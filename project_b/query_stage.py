#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""现场层检索器：按声学条件筛「哪一站、哪首歌」。

数据源：data/archive_stage_tour.json（879 行，每行一场次-曲目）

用法示例
  python -X utf8 project_b\\query_stage.py --low 70 --limit 10        # 最低音 ≤70Hz
  python -X utf8 project_b\\query_stage.py --long 0.7 --sort low_dur_s # 低音站得久
  python -X utf8 project_b\\query_stage.py --soft --limit 15           # 弱唱（claimable_soft）
  python -X utf8 project_b\\query_stage.py --dense 1.6                 # 一字一音的高密度段
  python -X utf8 project_b\\query_stage.py --song 绒花 --city 上海
  python -X utf8 project_b\\query_stage.py --low 70 --year 2024 --md out.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "archive_stage_tour.json"


def load():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    return d.get("rows", [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--low", type=float, help="最低稳定音 ≤ 该 Hz")
    ap.add_argument("--high", type=float, help="最高稳定音 ≥ 该 Hz")
    ap.add_argument("--long", type=float, help="低音持续 ≥ 该秒数")
    ap.add_argument("--dense", type=float, help="音符密度 ≥ 该值（音/秒）")
    ap.add_argument("--stable", type=float, help="音分稳定性 ≤ 该值（越小越稳）")
    ap.add_argument("--soft", action="store_true", help="只看 claimable_soft=真（弱唱）")
    ap.add_argument("--claimable", action="store_true", help="只看 claimable=真")
    ap.add_argument("--song", help="曲名包含")
    ap.add_argument("--city", help="城市包含")
    ap.add_argument("--tour", help="巡演轮次包含（一巡/二巡…）")
    ap.add_argument("--year", help="年份，如 2024")
    ap.add_argument("--sort", default="low_hz", help="排序字段（默认 low_hz 升序）")
    ap.add_argument("--desc", action="store_true", help="降序")
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--md", help="同时写出 markdown 表格")
    ap.add_argument("--video", action="store_true", help="素材模式：输出时间点+B站链接")
    a = ap.parse_args()

    rows = [r for r in load() if r.get("song")]
    n0 = len(rows)

    def num(r, k):
        v = r.get(k)
        return float(v) if isinstance(v, (int, float)) else None

    if a.low is not None:
        rows = [r for r in rows if (num(r, "low_hz") or 9e9) <= a.low]
    if a.high is not None:
        rows = [r for r in rows if (num(r, "high_hz") or 0) >= a.high]
    if a.long is not None:
        rows = [r for r in rows if (num(r, "low_dur_s") or 0) >= a.long]
    if a.dense is not None:
        rows = [r for r in rows if (num(r, "density_per_s") or 0) >= a.dense]
    if a.stable is not None:
        rows = [r for r in rows if (num(r, "stability_cents") or 9e9) <= a.stable]
    if a.soft:
        rows = [r for r in rows if r.get("claimable_soft") is True]
    if a.claimable:
        rows = [r for r in rows if r.get("claimable") is True]
    if a.song:
        rows = [r for r in rows if a.song in str(r.get("song", ""))]
    if a.city:
        rows = [r for r in rows if a.city in str(r.get("city", ""))]
    if a.tour:
        rows = [r for r in rows if a.tour in str(r.get("tour", ""))]
    if a.year:
        rows = [r for r in rows if str(r.get("date", "")).startswith(a.year)]

    rows.sort(key=lambda r: (num(r, a.sort) if num(r, a.sort) is not None else 9e9),
              reverse=a.desc)
    hit = rows[: a.limit]

    print(f"命中 {len(rows)} / {n0} 条｜条件: " + ", ".join(
        f"{k}={v}" for k, v in vars(a).items() if v not in (None, False, "", 15, "low_hz")) or "（无）")
    def mmss(v):
        if not isinstance(v, (int, float)):
            return "—"
        return "%d:%02d" % (int(v) // 60, int(v) % 60)

    print("-" * 100)
    if a.video:
        print("%-16s %-9s %-10s %-6s %7s %7s %6s  %s" %
              ("曲目", "城市", "日期", "最低音", "Hz", "时间点", "时长s", "链接"))
        for r in hit:
            link = ("https://www.bilibili.com/video/" + str(r.get("bv"))) if r.get("bv") else "（本地素材）"
            print("%-16s %-9s %-10s %-6s %7.1f %7s %6.2f  %s" % (
                str(r.get("song"))[:16], str(r.get("city") or "—")[:9], str(r.get("date") or "")[:10],
                str(r.get("low_note") or "—"), num(r, "low_hz") or 0,
                mmss(r.get("low_t_s")), num(r, "low_dur_s") or 0, link))
    else:
        print("%-16s %-10s %-10s %-6s %-7s %6s %6s %5s %6s %6s" %
              ("曲目", "城市", "日期", "最低音", "Hz", "时长s", "密度", "稳定", "颤音", "可引用"))
        for r in hit:
            print("%-16s %-10s %-10s %-6s %7.1f %6.2f %6.2f %5.1f %6.2f %6s" % (
                str(r.get("song"))[:16], str(r.get("city"))[:10], str(r.get("date"))[:10],
                str(r.get("low_note") or "—"), num(r, "low_hz") or 0,
                num(r, "low_dur_s") or 0, num(r, "density_per_s") or 0,
                num(r, "stability_cents") or 0, num(r, "vibrato_hz") or 0,
                "✓" if r.get("claimable") else ""))

    if a.md:
        lines = ["| 曲目 | 城市 | 日期 | 最低音 | Hz | 时长s | 密度 | 稳定(音分) | 颤音Hz | 可引用 |",
                 "|---|---|---|---|---|---|---|---|---|---|"]
        for r in hit:
            lines.append("| %s | %s | %s | %s | %.1f | %.2f | %.2f | %.1f | %.2f | %s |" % (
                r.get("song"), r.get("city"), r.get("date"), r.get("low_note") or "—",
                num(r, "low_hz") or 0, num(r, "low_dur_s") or 0, num(r, "density_per_s") or 0,
                num(r, "stability_cents") or 0, num(r, "vibrato_hz") or 0,
                "✓" if r.get("claimable") else ""))
        Path(a.md).write_text("\n".join(lines), encoding="utf-8")
        print("\n已写出:", a.md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
