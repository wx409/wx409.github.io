# -*- coding: utf-8 -*-
"""并入用户手写的两份活动表 → 统一活动总表（带来源与状态）。

来源
----
① E:\\wx\\index_records\\王晰演出活动.xlsx        百科版：演出名称/时间/地点/备注/演唱曲目（含晚会·电视录制）
② E:\\wx\\index_records\\长表已核对_20260903.xlsx  微博核对版：事件日期/城市/标题/巡演/状态/提到歌曲/佐证原文

产出
----
data/activity_master.json ＋ E:\\wx\\论文素材_王晰作传\\活动总表_合并版.md

用途
----
· 晚会/综艺类事件（此前缺口）→ 可做事件窗口分析的**事件源**
· 带曲目的事件 → 可**重建演出场次/保留曲目**统计（比 songs_meta 更全）
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from song_names import canon  # noqa: E402

A = r"E:\wx\index_records\王晰演出活动.xlsx"
B = r"E:\wx\index_records\长表已核对_20260903.xlsx"
OUT_JSON = SITE / "data" / "activity_master.json"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\活动总表_合并版.md")

# 分类：按「标题 + 备注」首个命中的桶。⚠️ 关键字必须够窄——曾用单字「节」，
# 结果「点歌环节」把演唱会误判成「晚会/典礼」（2026-10-10 修）。节日类改成显式枚举。
KIND = [("晚会/典礼", ["春晚", "春节", "联欢", "元宵", "中秋", "国庆", "典礼", "开幕", "闭幕", "盛典", "颁奖",
                       "音乐节", "电影节", "戏剧节", "艺术节", "电视节", "狂欢节", "跨年"]),
        ("综艺/电视", ["综艺", "节目", "录制", "真人秀", "访谈", "直播", "歌手", "声入人心", "电视台"]),
        ("巡演/音乐会", ["巡演", "巡回", "音乐会", "演唱会", "签唱", "个人"]),
        ("音乐剧/话剧", ["音乐剧", "话剧", "舞台剧"]),
        ("公益/其他", [])]


def classify(text: str) -> str:
    for k, kws in KIND:
        if any(w in text for w in kws):
            return k
    return "其他"


def split_songs(s) -> list[str]:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return []
    parts = re.split(r"[、,，;；/\n]+", str(s))
    out = []
    for p in parts:
        p = p.strip()
        if 2 <= len(p) <= 24 and not re.search(r"^\d+$", p):
            out.append(canon(p))
    return sorted(set(out))


ATTR_FILE = SITE / "data" / "performance_attribution.json"


def load_attribution() -> list[dict]:
    """演唱者归属覆盖表（双人/拼盘场次的同台嘉宾独唱曲目）。缺文件则返回空表（不报错）。"""
    try:
        return json.loads(ATTR_FILE.read_text(encoding="utf-8")).get("shows", [])
    except Exception:
        return []


def apply_attribution(row: dict, shows: list[dict]) -> None:
    """给该事件挂归属：`song_performers`（逐曲归属）、`songs_subject`（只算主体歌手王晰的曲目）。

    **不删曲目**：`songs` 保持全场原样；`songs_subject` 供"王晰曲目"统计使用。
    """
    hit = next((s for s in shows
                if s.get("key") and row["date"].startswith(s["key"])
                and (not s.get("title_match") or s["title_match"] in row["title"])), None)
    if not hit:
        return
    excl = set(hit.get("exclude_for_subject") or [])
    pend = {p.get("song"): p.get("by") for p in (hit.get("pending") or [])}
    keep = hit.get("keep") or {}
    pmap = {}
    for s in row["songs"]:
        if s in excl:
            pmap[s] = "傲日其愣（独唱）"
        elif s in pend:
            pmap[s] = pend[s] or "待核（疑傲日独唱，用户未确认）"
        else:
            pmap[s] = "王晰/双人（未列入排除）"
    row["song_performers"] = pmap
    row["songs_subject"] = sorted([s for s in row["songs"] if s not in excl])
    row["attribution"] = {
        "cast": hit.get("cast", ""),
        "excluded_for_subject": sorted(excl),
        "pending": hit.get("pending", []),
        "keep_wangxi": keep.get("王晰独唱", []),
        "keep_duet": keep.get("双人合唱", []),
        "config": "data/performance_attribution.json",
        "note": ("本行为双人/拼盘场次全场曲目；`songs`=全场登记，`songs_subject`=只算主体歌手王晰"
                 "（已剔除同台嘉宾独唱，但不删数据）。" if excl else
                 "本行无归属覆盖（`songs`= `songs_subject`）。"),
    }

def main() -> int:
    rows = []
    # ① 百科版
    df1 = pd.read_excel(A, sheet_name=0)
    for _, r in df1.iterrows():
        d = pd.to_datetime(r.get("时间"), errors="coerce")
        if pd.isna(d):
            continue
        rows.append({"date": d.strftime("%Y-%m-%d"),
                     "title": str(r.get("演出名称") or "").strip(),
                     "city": str(r.get("地点") or "").strip(),
                     "note": str(r.get("备注") or "").strip(),
                     "songs": split_songs(r.get("演唱曲目")),
                     "source": "百科版", "status": "已核对（百科）"})
    # ② 微博核对版
    df2 = pd.read_excel(B, sheet_name=0)
    for _, r in df2.iterrows():
        d = pd.to_datetime(r.get("事件日期"), errors="coerce")
        if pd.isna(d):
            continue
        rows.append({"date": d.strftime("%Y-%m-%d"),
                     "title": str(r.get("标题") or "").strip(),
                     "city": str(r.get("城市") or "").strip(),
                     "note": f"巡演={r.get('巡演')}｜长表命中={r.get('长表命中')}｜差异={r.get('差异说明')}",
                     "songs": split_songs(r.get("提到歌曲")),
                     "evidence": str(r.get("佐证原文") or "")[:200],
                     "source": "微博核对版", "status": str(r.get("状态") or "")})
    # 应用人工更正（日期-城市错配）
    try:
        corr = json.loads((Path(__file__).resolve().parent.parent / "data" / "activity_corrections.json")
                          .read_text(encoding="utf-8"))
        for item in corr.get("items", []):
            for r in rows:
                if r["date"] == item["date"] and r.get("city") == item["from_city"]:
                    r["city"] = item["to_city"]
                    if item.get("to_title"):
                        r["title"] = item["to_title"]
                    r["note"] = (r.get("note") or "") + f"｜更正：{item['reason']}"
    except Exception as e:
        print("更正表读取失败:", e)

    for r in rows:
        r["kind"] = classify(f"{r['title']} {r['note']}")
    # 去重（同日期+同标题前 12 字）
    seen, uniq = set(), []
    for r in rows:
        k = (r["date"], re.sub(r"\W", "", r["title"])[:12])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    uniq.sort(key=lambda x: x["date"])

    with_songs = [r for r in uniq if r["songs"]]
    # 演唱者归属覆盖（双人/拼盘场次：同台嘉宾独唱不计入"王晰曲目"，但不删数据）
    shows = load_attribution()
    for r in uniq:
        apply_attribution(r, shows)
    # 曲目 → 出现事件数（可重建"演出保留曲目"）——**按主体歌手口径**（songs_subject）
    song_events = defaultdict(list)
    for r in uniq:
        for s in (r.get("songs_subject") or r["songs"]):
            song_events[s].append(r["date"])

    payload = {"generated_at": datetime.now().isoformat(timespec="seconds"),
               "n_events": len(uniq), "n_with_songs": len(with_songs),
               "by_source": dict(Counter(r["source"] for r in uniq)),
               "by_kind": dict(Counter(r["kind"] for r in uniq)),
               "by_year": dict(sorted(Counter(r["date"][:4] for r in uniq).items())),
               "song_event_counts": {k: len(v) for k, v in
                                     sorted(song_events.items(), key=lambda kv: -len(kv[1]))},
               "rows": uniq}
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    L = ["# 活动总表（合并版：百科 + 微博核对）", "",
         f"生成 {datetime.now():%Y-%m-%d %H:%M}", "",
         f"- 事件 **{len(uniq)}** 条（百科版 {payload['by_source'].get('百科版',0)} ＋ "
         f"微博核对版 {payload['by_source'].get('微博核对版',0)}）",
         f"- **带演唱曲目 {len(with_songs)} 条** → 可重建保留曲目统计",
         f"- 日期范围 **{uniq[0]['date']} → {uniq[-1]['date']}**", "",
         "## 按类型", "", "| 类型 | 条数 |", "|---|---|"]
    for k, v in sorted(payload["by_kind"].items(), key=lambda kv: -kv[1]):
        L.append(f"| {k} | {v} |")
    L += ["", "## 按年份", "", "| 年 | 条数 |", "|---|---|"]
    for y, v in payload["by_year"].items():
        L.append(f"| {y} | {v} |")
    L += ["", "## 带曲目事件明细（前 60，按日期）", "",
          "| 日期 | 类型 | 标题 | 城市 | 曲目 | 来源 |", "|---|---|---|---|---|---|"]
    for r in with_songs[:60]:
        L.append(f"| {r['date']} | {r['kind']} | {r['title'][:30]} | {r['city'][:8]} | "
                 f"{'、'.join(r['songs'][:6])} | {r['source']} |")
    L += ["", "## 曲目出现事件数 Top 30（= 演出保留曲目，比 songs_meta 更全）", "",
          "| 曲目 | 事件数 | 涉及日期（前 6） |", "|---|---|---|"]
    for s, ds in sorted(song_events.items(), key=lambda kv: -len(kv[1]))[:30]:
        L.append(f"| {s} | {len(ds)} | {'、'.join(sorted(ds)[:6])} |")
    L += ["", "## 说明与边界", "",
          "- ① 百科版来自百度百科手工整理（含晚会/电视录制/典礼，此前是缺口）",
          "- ② 微博核对版含「佐证原文」与状态（疑似长表缺失/歌单差异/基本一致）",
          "- ② 作者自述**粗糙且有错误、不含最新活动（《沉响与长歌》）** → 本表保留 status 字段以便复核",
          "- 曲目经 canon() 归一；同名不同歌的情况仍可能合并（待核）", ""]
    OUT_MD.write_text("\n".join(L), encoding="utf-8")

    print(f"合并事件 {len(uniq)}｜带曲目 {len(with_songs)}｜日期 {uniq[0]['date']} → {uniq[-1]['date']}")
    print("按类型:", payload["by_kind"])
    print("按来源:", payload["by_source"])
    print("带曲目事件数按年:", dict(sorted(Counter(r['date'][:4] for r in with_songs).items())))
    print("曲目覆盖数:", len(song_events))
    print("\n保留曲目 Top12:", [(s, len(d)) for s, d in sorted(song_events.items(), key=lambda kv: -len(kv[1]))[:12]])
    print(f"\n→ {OUT_JSON}\n→ {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
