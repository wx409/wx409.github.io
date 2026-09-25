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

KIND = [("晚会/典礼", ["春晚", "元宵", "中秋", "国庆", "典礼", "开幕", "闭幕", "盛典", "颁奖", "节"]),
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
    # 曲目 → 出现事件数（可重建"演出保留曲目"）
    song_events = defaultdict(list)
    for r in uniq:
        for s in r["songs"]:
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
