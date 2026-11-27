#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_collect.py —— 多源采集 B站 王晰 视频，按「代表性标准」打分，筛选后再下载。

为什么要有它：
  原流程只抓官方空间（mid 3493257487059302）。该号本人最后一条是 2024-05-13，
  采集范围内最新一条是 2025-01-29（别人的专访），所以 today.html 会长期写
  “今天没有新的 B站视频”——不是 bug，是源太窄。本脚本扩源并给出可解释的打分。

来源（三路合并去重）：
  1. space：官方空间 x/space/arc/search
  2. search：关键词 x/web-interface/search/type（order=pubdate）
  3. whitelist：指定 UP 主 MID（各走一次 space）

代表性标准（写死在 SCORE_RULES，输出里带 reasons，可核对）：
  相关性  标题含「王晰」+2；来自官方/白名单 +1
  类型    含 直拍/现场/点歌/歌曲/唱 等 +3；含 专访/花絮/预告/reaction/盘点 等 -3
  热度    play>=10000 +2；>=2000 +1
  时效    <=3 天 +3；<=14 天 +2；<=60 天 +1
  时长    45~1800 秒 +1；<45 秒 -2
  入选    总分 >= 6 且 类型分 > 0（避免把访谈/花絮收进来）

输出：
  data/bili_candidates.json    候选清单（含 score / reasons / representative）
  data/bili_fetch_status.json  抓取状态（每个来源的 ok/code/count/error），供页面如实提示
  --download 时：把入选且本地没有的 BV 写进临时 txt，调用 download_bilibili.py 下载到「精选」目录

用法：
  python -X utf8 project_b/bili_collect.py                # 只采集打分
  python -X utf8 project_b/bili_collect.py --download     # 采集 + 下载入选
  python -X utf8 project_b/bili_collect.py --window 30    # 只看最近 30 天
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
DL_PY = ROOT / "project_b" / "download_bilibili.py"
OFFICIAL_MID = "3493257487059302"
OFFICIAL_DIR = Path(r"E:\wx\论文素材_王晰作传\B站\官方空间")
CURATED_DIR = Path(r"E:\wx\论文素材_王晰作传\B站\精选")

KEYWORDS = ["王晰 直拍", "王晰 现场", "王晰 巡演", "王晰 歌曲"]
# 白名单：已知较活跃的饭拍/合作方；找不到就自动跳过（接口会返回 0 条）
WHITELIST_MIDS = {
    "王晰Elvis": "3493257487059302",
}

SONG = ("直拍", "现场", "live", "Live", "点歌", "歌曲", "唱", "多听有益", "哭砂", "微醺", "小河", "甩啦", "巡演")
BAD = ("专访", "访谈", "纪录片", "幕后", "花絮", "特辑", "hi，", "Vlog", "预告", "reaction", "盘点", "采访", "reaction")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bili_rules import exclude_reason  # noqa: E402

REQUEST_GAP = 3.0     # 每次请求间隔（秒），避免 -799
RETRY_ON_LIMIT = 3
STATUS = DATA / "bili_fetch_status.json"
CAND = DATA / "bili_candidates.json"


def load_downloader():
    spec = importlib.util.spec_from_file_location("dl", str(DL_PY))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_headers(dl):
    cookie = dl.get_session_cookie() or ""
    extra = dl.load_bili_cookie() or ""
    if extra:
        cookie = cookie + "; " + extra
    return {"User-Agent": dl.UA, "Cookie": cookie,
            "Referer": "https://space.bilibili.com/"}


def get_json(dl, url, headers, tag):
    """带 -799 退避的 GET；失败返回 (None, err)。"""
    last = ""
    for attempt in range(RETRY_ON_LIMIT + 1):
        try:
            j = dl.http_get_json(url, headers=headers)
        except Exception as e:
            last = str(e)[:120]
            time.sleep(REQUEST_GAP * 2)
            continue
        code = j.get("code")
        if code == 0:
            return j, None
        last = f"code={code} {str(j.get('message') or '')[:40]}"
        if code == -799:                     # 限流
            time.sleep(20 + attempt * 15)
            continue
        if code in (-352, -403):             # 风控
            time.sleep(10)
            continue
        return None, last
    return None, last


# ---------------- 采集 ----------------

def to_secs(x):
    """'31:09' / '1:02:03' / 1893 / None → 秒。"""
    if isinstance(x, (int, float)):
        return int(x)
    s = str(x or "").strip()
    if not s:
        return 0
    try:
        total = 0
        for p in s.split(":"):
            total = total * 60 + int(p)
        return total
    except Exception:
        return 0


def norm_space_item(v):
    return {
        "bvid": v.get("bvid"),
        "title": (v.get("title") or "").strip(),
        "owner": v.get("author") or "",
        "mid": "",
        "pub_ts": int(v.get("created") or 0),
        "duration": to_secs(v.get("length")),
        "play": int(v.get("play") or 0),
        "src": "space",
    }


def norm_search_item(v):
    title = re.sub(r"<[^>]+>", "", v.get("title") or "")   # 去掉 <em> 高亮
    return {
        "bvid": v.get("bvid"),
        "title": title.strip(),
        "owner": v.get("author") or "",
        "mid": str(v.get("mid") or ""),
        "pub_ts": int(v.get("pubdate") or 0),
        "duration": to_secs(v.get("duration")),
        "play": int(v.get("play") or 0),
        "src": "search",
    }


def collect_space(dl, headers, mid, pages=2):
    out, err = [], None
    for pn in range(1, pages + 1):
        url = f"https://api.bilibili.com/x/space/arc/search?mid={mid}&ps=50&pn={pn}&order=pubdate"
        j, e = get_json(dl, url, headers, f"space:{mid}")
        if e:
            err = e
            break
        vl = ((j.get("data") or {}).get("list") or {}).get("vlist") or []
        out += [norm_space_item(v) for v in vl]
        if not ((j.get("data") or {}).get("page") or {}).get("count"):
            break
        time.sleep(REQUEST_GAP)
    return out, err


def collect_search(dl, headers, keyword):
    out, err = [], None
    kw = urllib.parse.quote(keyword)
    url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword={kw}&order=pubdate&page=1"
    j, e = get_json(dl, url, headers, f"search:{keyword}")
    if e:
        return [], e
    res = (j.get("data") or {}).get("result") or []
    out = [norm_search_item(v) for v in res if v.get("bvid")]
    return out, None


# ---------------- 打分 ----------------

def score_item(it, window_days, today):
    score, reasons = 0, []
    title = it["title"]

    # 硬规则：群星/合唱/串烧/访谈 一律不进候选（见 bili_rules.py）
    why = exclude_reason(title, it.get("bvid", ""))
    if why:
        it["age_days"] = 9999
        it["score"] = -99
        it["reasons"] = ["规则排除：" + why]
        it["representative"] = False
        return it

    if "王晰" in title:
        score += 2; reasons.append("标题含王晰 +2")
    if str(it.get("mid")) == OFFICIAL_MID or it.get("owner") == "王晰Elvis":
        score += 1; reasons.append("官方号 +1")

    type_score = 0
    if any(k in title for k in SONG):
        type_score += 3
    if any(k in title for k in BAD):
        type_score -= 3
    score += type_score
    if type_score >= 3:
        reasons.append("演唱/现场类 +3")
    elif type_score <= -3:
        reasons.append("访谈/花絮类 -3")

    if it["play"] >= 10000:
        score += 2; reasons.append("播放≥1万 +2")
    elif it["play"] >= 2000:
        score += 1; reasons.append("播放≥2千 +1")

    age_days = (today - datetime.fromtimestamp(it["pub_ts"]).date()).days if it["pub_ts"] else 9999
    if age_days <= 3:
        score += 3; reasons.append(f"{age_days}天内 +3")
    elif age_days <= 14:
        score += 2; reasons.append(f"{age_days}天内 +2")
    elif age_days <= 60:
        score += 1; reasons.append(f"{age_days}天内 +1")

    if 45 <= it["duration"] <= 1800:
        score += 1; reasons.append("时长合适 +1")
    elif it["duration"] < 45:
        score -= 2; reasons.append("时长过短 -2")

    it["age_days"] = age_days
    it["score"] = score
    it["reasons"] = reasons
    it["representative"] = bool(score >= 6 and type_score > 0 and age_days <= window_days)
    return it


def local_bvids():
    s = set()
    for d in (OFFICIAL_DIR, CURATED_DIR):
        if d.exists():
            for f in d.glob("*.mp4"):
                s.add(f.name.split("_", 1)[0])
    return s


# ---------------- 定向补全（--fill） ----------------

FILL_REPORT = DATA / "bili_fill_report.json"


def weak_shows(levels):
    try:
        cov = json.loads((DATA / "coverage_index.json").read_text(encoding="utf-8"))
    except Exception:
        return []
    out = []
    for s in cov.get("shows") or []:
        try:
            lv = int(s.get("level") or 0)
        except Exception:
            lv = 0
        if lv in levels:
            out.append(s)
    return out


def match_score(text, show):
    """标题/文件名与场次的匹配分：城市 3、完整日期 5、年份 2。"""
    city = show.get("city") or ""
    date8 = (show.get("date") or "").replace("-", "")
    year = date8[:4]
    s = 0
    if city and city in text:
        s += 3
    if date8 and date8 in text:
        s += 5
    if year and year in text:
        s += 2
    return s


def fill_quality(title):
    """补全用的质量分：优先全场/直拍，压掉嘉宾寒暄、花絮、采访。"""
    q = 0
    if any(k in title for k in ("全场", "完整", "整场")):
        q += 2
    if any(k in title for k in ("直拍", "超清", "4K", "4k")):
        q += 1
    if any(k in title for k in ("嘉宾", "非演唱", "花絮", "采访", "专访", "预告", "reaction")):
        q -= 3
    return q


def run_fill(args, dl, headers):
    levels = [int(x) for x in str(args.levels).split(",") if x.strip().isdigit()]
    shows = weak_shows(levels)
    print(f"待补全场次 {len(shows)} 个（覆盖等级 {levels}）")
    report = {"at": datetime.now().strftime("%Y-%m-%d %H:%M"), "levels": levels,
              "shows": [], "picked": []}
    have = local_bvids()
    picked = []

    for sh in shows:
        city = sh.get("city") or ""
        date8 = (sh.get("date") or "").replace("-", "")
        year = date8[:4]
        queries = [f"王晰 {city}", f"王晰 {city} 现场", f"王晰 {city} {year}", f"王晰 {date8}"]
        found, seen_local = [], set()
        for q in queries:
            items, err = collect_search(dl, headers, q)
            for it in items:
                if it["bvid"] in seen_local:
                    continue
                sc = match_score(it["title"] + " " + it.get("owner", ""), sh)
                if sc >= 3:
                    seen_local.add(it["bvid"])
                    it["match"] = sc
                    it["query"] = q
                    found.append(it)
            print(f"  [{sh.get('tour')} {city} {date8}] 「{q}」→ {len(items)} 条，命中 {len(found)}")
            time.sleep(REQUEST_GAP)

        found.sort(key=lambda x: (x["match"] + fill_quality(x["title"]), x["play"]), reverse=True)
        take = found[: max(1, args.per_show)]
        report["shows"].append({
            "tour": sh.get("tour"), "city": city, "date": date8, "level": sh.get("level"),
            "queries": queries, "hits": len(found),
            "best": [{"bvid": x["bvid"], "title": x["title"], "match": x["match"],
                      "play": x["play"], "local": x["bvid"] in have} for x in take],
        })
        for x in take:
            if x["bvid"] not in have:
                picked.append(x)
        time.sleep(REQUEST_GAP)

    # 按 BV 去重
    uniq, seen_bv = [], set()
    for x in picked:
        if x["bvid"] in seen_bv:
            continue
        seen_bv.add(x["bvid"])
        uniq.append(x)
    report["picked"] = [{"bvid": x["bvid"], "title": x["title"], "match": x["match"]} for x in uniq]

    print(f"\n定向命中 {sum(1 for s in report['shows'] if s['hits'])}/{len(shows)} 个场次；待下载 {len(uniq)} 条")
    for s in report["shows"]:
        best = s["best"][0] if s["best"] else None
        print(f"  {s['tour']} {s['city']} {s['date']}: 命中 {s['hits']} 条"
              + (f" | 最佳 {best['bvid']} {best['title'][:34]}" if best else " | 无"))

    if args.dry_run:
        print("--dry-run：不写文件、不下载")
        return 0

    FILL_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print("写出:", FILL_REPORT.name)

    if args.download and uniq:
        CURATED_DIR.mkdir(parents=True, exist_ok=True)
        txt = Path(tempfile.gettempdir()) / "bili_fill.txt"
        txt.write_text("\n".join(x["bvid"] for x in uniq), encoding="utf-8")
        cmd = [sys.executable, "-X", "utf8", str(DL_PY), str(txt), "--out", str(CURATED_DIR)]
        print("下载:", " ".join(cmd))
        rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
        print("下载退出码:", rc)
        return rc
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=120, help="只看最近 N 天的投稿（默认 120）")
    ap.add_argument("--top", type=int, default=8, help="每天最多入选 N 条（默认 8）")
    ap.add_argument("--download", action="store_true", help="下载入选且本地没有的视频")
    ap.add_argument("--dry-run", action="store_true", help="不写任何文件，只打印")
    ap.add_argument("--fill", action="store_true", help="定向补全：对覆盖最弱的场次做定向搜索")
    ap.add_argument("--levels", default="4", help="--fill 时针对的覆盖等级（逗号分隔，默认 4）")
    ap.add_argument("--per-show", type=int, default=1, help="--fill 时每个场次最多取几条（默认 1）")
    args = ap.parse_args()

    today = date.today()
    dl = load_downloader()
    headers = make_headers(dl)
    ttl = (headers.get("Cookie") or "")
    print(f"cookie 长度 {len(ttl)}")

    if args.fill:
        return run_fill(args, dl, headers)

    status = {"at": datetime.now().strftime("%Y-%m-%d %H:%M"), "ok": False, "sources": [], "window_days": args.window}

    raw, seen = [], set()

    def add(items, src):
        for it in items:
            if not it.get("bvid") or it["bvid"] in seen:
                # 同一 BV 多来源：保留首次（并记录来源）
                continue
            seen.add(it["bvid"])
            it.setdefault("src", src)
            raw.append(it)

    # 1) 官方空间
    items, err = collect_space(dl, headers, OFFICIAL_MID)
    status["sources"].append({"name": "space:official", "ok": err is None, "count": len(items), "error": err})
    add(items, "space")
    print(f"[空间] {len(items)} 条 err={err}")

    # 2) 白名单空间
    for name, mid in WHITELIST_MIDS.items():
        if mid == OFFICIAL_MID:
            continue
        time.sleep(REQUEST_GAP)
        items, err = collect_space(dl, headers, mid, pages=1)
        status["sources"].append({"name": f"space:{name}", "ok": err is None, "count": len(items), "error": err})
        add(items, "whitelist")
        print(f"[白名单 {name}] {len(items)} 条 err={err}")

    # 3) 关键词搜索
    for kw in KEYWORDS:
        time.sleep(REQUEST_GAP)
        items, err = collect_search(dl, headers, kw)
        status["sources"].append({"name": f"search:{kw}", "ok": err is None, "count": len(items), "error": err})
        add(items, "search")
        print(f"[搜索 {kw}] {len(items)} 条 err={err}")

    status["ok"] = any(s["ok"] for s in status["sources"]) and len(raw) > 0
    status["total_scanned"] = len(raw)
    if not status["ok"]:
        status["note"] = "全部来源失败或为空；保留上次结果，不覆盖"

    scored = [score_item(it, args.window, today) for it in raw]
    scored.sort(key=lambda x: (x["score"], x["pub_ts"]), reverse=True)
    picked = [x for x in scored if x["representative"]][: args.top]
    have = local_bvids()
    for x in picked:
        x["already_local"] = x["bvid"] in have
    need = [x for x in picked if not x["already_local"]]

    doc = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "window_days": args.window,
        "total_scanned": len(raw),
        "scored": len(scored),
        "representative_count": sum(1 for x in scored if x["representative"]),
        "picked_count": len(picked),
        "need_download": len(need),
        "items": picked,
    }

    print(f"\n扫到 {len(raw)} 条 → 入选 {len(picked)} 条，其中待下载 {len(need)} 条")
    for x in picked:
        print(f"  {x['score']:>3}  {x['bvid']}  {datetime.fromtimestamp(x['pub_ts']).strftime('%Y-%m-%d') if x['pub_ts'] else '?'}  "
              f"{x['title'][:36]}  [{'已有' if x['already_local'] else '待下'}]")

    if args.dry_run:
        print("\n--dry-run：不写文件")
        return 0

    if status["ok"]:
        STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
        CAND.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        print("写出:", CAND.name, "|", STATUS.name)
    else:
        STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
        print("!! 全部来源失败，仅写状态；候选文件保持上次内容")

    if args.download and need:
        CURATED_DIR.mkdir(parents=True, exist_ok=True)
        txt = Path(tempfile.gettempdir()) / "bili_picked.txt"
        txt.write_text("\n".join(x["bvid"] for x in need), encoding="utf-8")
        cmd = [sys.executable, "-X", "utf8", str(DL_PY), str(txt), "--out", str(CURATED_DIR)]
        print("下载:", " ".join(cmd))
        rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
        print("下载退出码:", rc)
        return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
