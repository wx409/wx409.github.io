#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同曲跨场矩阵生成器：data/archive_stage_tour.json → data/live_versions.json（+ 人读 md）。

为什么要它：
  站点此前只有「单曲 × 单场」的读数，以及「同曲录音室 ↔ 现场」的成对比较；
  缺的是**同一首歌在多个巡次/年份/城市之间的横向排列**——这正是评价"同一歌手如何随场景调整"
  最直接的一层，也是唱功分析里最容易被形容词替代的一层。

口径（沿用全站纪律，不新建）：
  - 只取已过复核门槛的行：verify 不是「人耳否决」、有最低音读数；
  - 明确区分「稳定音 / 待判读数」：待判的照样列出，但 state 标 pending，不进任何中位统计；
  - 录音室参照取 archive_vocal_albums.json 的该曲最低稳定音（没有则留空，不推测）；
  - 全部数字由数据派生，页面/报告里禁止手写。

用法：
  python -X utf8 project_b/build_live_versions.py              # 生成 json + md
  python -X utf8 project_b/build_live_versions.py --min 3      # 只保留 ≥3 个版本的曲目
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "archive_stage_tour.json"
ALB = ROOT / "data" / "archive_vocal_albums.json"
OUT = ROOT / "data" / "live_versions.json"
MD = Path(r"E:\wx\论文素材_王晰作传\传记素材\同曲跨场矩阵_v1.md")

# 优先曲目：有代表性、版本多、或被官方/文献点到；不足的会按「版本数」自动补齐
PRIORITY = ["多听有益", "静止了的夜晚", "让她降落", "Your Man", "一生守候", "哭砂",
            "后会无期", "再见我的爱人", "像雾像雨又像风", "雪地里寄不出的求救信"]

REJECT = ("人耳否决",)
PENDING = ("待判", "待复核", "不可复核", "未复核")
# 整场/混剪/串烧素材不是「一首歌的一个版本」，不进同曲矩阵
NOT_A_SONG = ("全场", "混剪", "串烧", "合集", "联唱")


def semi(a, b):
    if not a or not b:
        return None
    import math
    return round(12 * math.log2(a / b), 2)


def state_of(row):
    v = str(row.get("verify_channel") or row.get("a3_final_note") or "")
    if any(k in v for k in REJECT):
        return "rejected"
    if any(k in v for k in PENDING):
        return "pending"
    if row.get("claimable"):
        return "ok"
    return "recorded"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=3)
    args = ap.parse_args()

    tour = json.loads(SRC.read_text(encoding="utf-8"))
    alb = json.loads(ALB.read_text(encoding="utf-8"))
    studio = {}
    for s in alb.get("songs") or []:
        studio.setdefault(s["title"], {"note": s.get("low"), "hz": s.get("low_hz"), "album": s.get("album")})

    rows = tour.get("rows") or []
    if rows:
        rows[0].setdefault("_x", 0)  # nosemgrep: 空 dict 保护，防 None

    groups = defaultdict(list)
    for r in rows:
        name = (r.get("song") or "").strip()
        if not name or not r.get("low_hz"):
            continue
        if any(k in name for k in NOT_A_SONG):
            continue
        stt = state_of(r)
        if stt == "rejected":
            continue
        groups[name].append({
            "tour": r.get("tour") or "", "city": r.get("city") or "", "date": r.get("date") or "",
            "bv": r.get("bv") or "", "tag": r.get("tag") or "",
            "low_note": r.get("low_note"), "low_hz": r.get("low_hz"),
            "high_note": r.get("high_note"), "high_hz": r.get("high_hz"),
            "span_octaves": r.get("span_octaves"),
            "stability_cents": r.get("stability_cents"),
            "vibrato_hz": r.get("vibrato_hz"),
            "state": stt,
            "verify": str(r.get("verify_channel") or r.get("a3_final_note") or ""),
        })

    pick = [k for k in PRIORITY if len(groups.get(k, [])) >= 2]
    rest = sorted((k for k in groups if k not in pick and len(groups[k]) >= args.min),
                  key=lambda k: -len(groups[k]))
    chosen = pick + rest[:max(0, 12 - len(pick))]

    songs = []
    for name in chosen:
        vs = sorted(groups[name], key=lambda v: (str(v["date"]), v["tour"]))
        ok_low = [v["low_hz"] for v in vs if v["state"] == "ok"]
        stu = studio.get(name)
        tours = sorted({v["tour"] for v in vs if v["tour"]})
        item = {
            "song": name,
            "studio": stu,
            "n_versions": len(vs),
            "tours": tours,
            "n_tours": len(tours),
            "low_min": min(ok_low) if ok_low else None,
            "low_max": max(ok_low) if ok_low else None,
            "low_range_semitones": semi(max(ok_low), min(ok_low)) if len(ok_low) >= 2 else None,
            "low_median": round(st.median(ok_low), 2) if ok_low else None,
            "vs_studio_semitones": semi(st.median(ok_low), stu["hz"]) if ok_low and stu else None,
            "versions": vs,
        }
        songs.append(item)

    songs.sort(key=lambda x: (-x["n_tours"], -x["n_versions"]))

    doc = {
        "schema": "live-versions/v1",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "what": "同一首歌在不同巡次/年份/城市的现场读数横向矩阵（跨场对照的唯一数据出口）",
        "discipline": [
            "只列有最低音读数的现场行；人耳否决行直接排除",
            "state=ok 才可计入中位与对外结论；state=pending 照样展示但不进统计",
            "录音室参照取 archive_vocal_albums.json；无记录则留空，不推测",
            "全部数字派生，页面与报告禁止手写",
        ],
        "counts": {"songs": len(songs), "versions": sum(s["n_versions"] for s in songs)},
        "songs": songs,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    # 人读版
    lines = ["# 同曲跨场矩阵 v1", "",
             f"> 生成 {doc['generated_at']}｜曲目 **{doc['counts']['songs']}** 首 / 版本 **{doc['counts']['versions']}** 条",
             "> 口径：只计有最低音读数的现场行，人耳否决已排除；`待判` 展示但不进中位。", ""]
    for s in songs:
        stu = s["studio"]
        lines.append(f"## {s['song']}")
        if stu and stu.get("hz"):
            lines.append(f"录音室参照：**{stu['note']} {stu['hz']} Hz**（{stu['album']}）")
        if s["low_median"]:
            d = s.get("vs_studio_semitones")
            lines.append(f"现场 {len(s['tours'])} 个巡次 / {s['n_versions']} 个版本；稳定音中位 **{s['low_median']} Hz**"
                         + (f"，与录音室相差 **{d:+.1f} 半音**" if d is not None else "")
                         + (f"；版本间极差 **{s['low_range_semitones']:.1f} 半音**" if s.get("low_range_semitones") else ""))
        lines += ["", "| 巡次 | 日期 | 城市 | 最低音 | Hz | 最高音 | 跨度 | 稳定(音分) | 颤音(Hz) | 状态 |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for v in s["versions"]:
            lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                v["tour"] or "—", v["date"] or "—", v["city"] or "—",
                v["low_note"] or "—", v["low_hz"], v["high_note"] or "—",
                f'{v["span_octaves"]:.2f}' if v.get("span_octaves") else "—",
                f'{v["stability_cents"]:.1f}' if v.get("stability_cents") is not None else "—",
                f'{v["vibrato_hz"]:.2f}' if v.get("vibrato_hz") is not None else "—",
                {"ok": "✅ 过门槛", "pending": "⏳ 待判", "recorded": "· 已测"}.get(v["state"], v["state"])))
        lines.append("")
    MD.parent.mkdir(parents=True, exist_ok=True)
    MD.write_text("\n".join(lines), encoding="utf-8")

    print(f"[OK] {OUT.name}｜曲目 {len(songs)}｜版本 {doc['counts']['versions']}")
    print(f"[OK] {MD}")
    for s in songs[:6]:
        print(f"   {s['song']}: {s['n_versions']} 版 / {s['n_tours']} 巡 / 中位 {s['low_median']} Hz / Δ{s.get('vs_studio_semitones')}")


if __name__ == "__main__":
    main()
