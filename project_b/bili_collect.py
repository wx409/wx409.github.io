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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=120, help="只看最近 N 天的投稿（默认 120）")
    ap.add_argument("--top", type=int, default=8, help="每天最多入选 N 条（默认 8）")
    ap.add_argument("--download", action="store_true", help="下载入选且本地没有的视频")
    ap.add_argument("--dry-run", action="store_true", help="不写任何文件，只打印")
    args = ap.parse_args()

    today = date.today()
    dl = load_downloader()
    headers = make_headers(dl)
    ttl = (headers.get("Cookie") or "")
    print(f"cookie 长度 {len(ttl)}")

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
