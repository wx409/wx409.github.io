#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「分析向视频」剪辑素材清单：B站链接 + 精确时间点 + 声学理由。

数据：data/archive_stage_tour.json（每行含 bv / low_t_s / low_hz / low_dur_s / review_status）
输出：
  E:\\wx\\论文素材_王晰作传\\视频剪辑素材清单_<日期>.md    人读（带可点链接与理由）
  E:\\wx\\论文素材_王晰作传\\视频剪辑素材清单_<日期>.csv   剪辑用（Premiere/达芬奇/Excel）

分区
  A 低音证据（B1–C2 级、过复核门槛）——讲「低音怎么站住」用
  B 长音证据（持续时间最长的低音）——讲气息与支撑
  C 高音/颤音（可选）——讲音区与稳定
每行只收录「能对上一个具体时间点」的素材。
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data" / "archive_stage_tour.json"
OUTDIR = Path(r"E:\wx\论文素材_王晰作传")
TAG = date.today().strftime("%Y%m%d")
OK_STATES = ("谐波列通过", "人耳确认")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def mmss(t: float) -> str:
    return "%d:%02d" % (int(t // 60), int(t % 60))


def link(bv: str, t: float) -> str:
    return "https://www.bilibili.com/video/%s?t=%d" % (bv, int(t))


def row_reason(r: dict) -> str:
    bits = ["最低稳定音 %s（%.1fHz）" % (r.get("low_note"), r["low_hz"])]
    if r.get("low_dur_s"):
        bits.append("持续 %.2fs" % r["low_dur_s"])
    if r.get("vibrato_hz"):
        bits.append("颤音 %.2fHz" % r["vibrato_hz"])
    if r.get("stability_cents"):
        bits.append("音符内抖动 %d 音分" % round(r["stability_cents"]))
    bits.append("复核：%s" % r.get("review_status"))
    return "｜".join(bits)


def main() -> int:
    rows = json.loads(DATA.read_text(encoding="utf-8"))["rows"]
    usable = [r for r in rows
              if (r.get("bv") or "").strip()
              and r.get("low_t_s") is not None
              and r.get("low_hz")]

    # A：低音证据（≤ C2 82.4Hz，过复核）
    low = [r for r in usable
           if r["low_hz"] <= 82.4 and (r.get("review_status") in OK_STATES)]
    low.sort(key=lambda r: r["low_hz"])

    # B：长音（持续时间最长的低音，≥0.3s）
    long = [r for r in usable
            if (r.get("low_dur_s") or 0) >= 0.30 and (r.get("review_status") in OK_STATES)]
    long.sort(key=lambda r: -(r.get("low_dur_s") or 0))

    # C：高音/颤音（最高音读数，过复核）
    high = [r for r in usable
            if r.get("high_hz") and (r.get("review_status") in OK_STATES)]
    high.sort(key=lambda r: -r["high_hz"])

    md = ["# 分析向视频 · 剪辑素材清单（%s）" % TAG, "",
          "> 每条都能对上「哪个视频 + 第几秒 + 为什么值得讲」。",
          "> 只用过了复核门槛（谐波列通过/人耳确认）的读数；A1 一类低音带读数不在表里。", ""]

    def section(title, items, limit, why):
        md.append("## %s（%d 条，取前 %d）" % (title, len(items), limit))
        md.append("")
        md.append(why)
        md.append("")
        md.append("| # | 曲目 | 场次 | 时间点 | 声学理由 | 链接 |")
        md.append("|---|---|---|---|---|---|")
        for i, r in enumerate(items[:limit], 1):
            md.append("| %d | %s | %s %s %s | %s | %s | [打开](%s) |" % (
                i, r.get("song") or r.get("tag", "")[:16], r.get("tour", ""), r.get("city", ""),
                r.get("date", ""), mmss(r["low_t_s"]), row_reason(r), link(r["bv"], r["low_t_s"])))
        md.append("")

    section("A. 低音证据（讲「低音怎么站住」）", low, 20,
            "按最低音从低到高排。适合做「他到底能低到哪」的递进剪辑：每个音一条，听 2 秒即可。")
    section("B. 长音证据（讲气息与支撑）", long, 15,
            "按该低音的持续时间从长到短排。适合放慢、加波形，讲「站得住」而不是「碰得到」。")
    section("C. 高音与音区（讲两端）", high, 10,
            "按最高音排。前面的低音段与这里的高音段可以剪成同一首歌的两端对比。")

    md += ["## 使用建议", "",
           "- 每条链接带 `?t=` 秒数，点开直接跳到那一秒，省去拖进度条；",
           "- 同一首歌若有多个场次，优先用 B 区的（持续更长，画面更稳）；",
           "- 字幕建议只打三个信息：音名、赫兹、持续秒数——观众对「Hz」没有直觉，对「比某某低」有；",
           "- A 区前三条（B1/C2 附近）已经足够做一个 30 秒的开场钩子。", "",
           "生成脚本：`D:\\wx409.github.io\\project_b\\build_edit_list.py`"]

    md_path = OUTDIR / ("视频剪辑素材清单_%s.md" % TAG)
    md_path.write_text("\n".join(md), encoding="utf-8")

    csv_path = OUTDIR / ("视频剪辑素材清单_%s.csv" % TAG)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["分区", "曲目", "巡次", "城市", "日期", "时间点", "秒", "最低音", "Hz", "持续s", "颤音Hz", "复核", "BV", "链接"])
        for tag, items, limit in (("A低音", low, 20), ("B长音", long, 15), ("C高音", high, 10)):
            for r in items[:limit]:
                w.writerow([tag, r.get("song"), r.get("tour"), r.get("city"), r.get("date"),
                            mmss(r["low_t_s"]), int(r["low_t_s"]), r.get("low_note"), r.get("low_hz"),
                            round(r.get("low_dur_s") or 0, 2), r.get("vibrato_hz"),
                            r.get("review_status"), r.get("bv"), link(r["bv"], r["low_t_s"])])

    print("素材池：有 BV 且有时戳 %d 条" % len(usable))
    print("  A 低音 %d｜B 长音 %d｜C 高音 %d" % (len(low), len(long), len(high)))
    print("→", md_path)
    print("→", csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
