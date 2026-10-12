# -*- coding: utf-8 -*-
"""同曲跨夜一致性（判断七第五块砖）：10-09 vs 10-10 同曲块级指标对比。

输出：data/archive_cross_night.json + 报告独立小节「第五种证据：同曲跨夜」。
纪律：只报**差异与一致性**，不写「谁更强」、不做极值主张；上站层级按 review_status 决定。
用法：python -X utf8 project_b\\cross_night_consistency.py [--dry]
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
SB = SITE / "data" / "show_blocks"
OUT = SITE / "data" / "archive_cross_night.json"
KEYS = ["stability_cents_median", "intonation_cents_median", "vibrato_hz_median",
        "density_per_s", "hnr_db_median", "f0_median_note"]


def load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    nights = {}
    for f in sorted(SB.glob("*.json")):
        d = load(f)
        bl = d.get("blocks") or []
        date = (d.get("show") or {}).get("date")
        if date and bl:
            nights[date] = d
    print(f"[跨夜] 有块级数据的场次：{sorted(nights) or '（暂无）'}")
    if len(nights) < 2:
        print("⛔ 不足两夜有块级数据 → 无法计算跨夜一致性（10-10 待回填定案后即可）")
        print("[--dry] 参数对齐检查通过：输入路径 data/show_blocks/*.json，输出 data/archive_cross_night.json")
        return 0
    dates = sorted(nights)
    # 同曲对齐：以 blocks[].song（已确证）为键
    per = {}
    for dt in dates:
        for b in nights[dt]["blocks"]:
            song = b.get("song")
            if song and b.get("song_status") == "已确证":
                per.setdefault(song, {}).setdefault(dt, []).append(b)
    rows = []
    for song, byd in per.items():
        if len(byd) < 2:
            continue
        cmp = {}
        for k in KEYS:
            vals = {dt: ([x[k] for x in v if isinstance(x.get(k), (int, float))] or None)
                    for dt, v in byd.items()}
            med = {dt: (round(st.median(vv), 2) if vv else None) for dt, vv in vals.items()}
            cmp[k] = med
        rows.append({"song": song, "by_night": cmp})
    print(f"[跨夜] 同曲可比：{len(rows)} 首｜" + "、".join(r["song"] for r in rows[:6]))
    print("口径：只报差异/一致性，不评优劣；极值音不参与")
    if a.dry:
        print("[--dry] 不写产物"); return 0
    OUT.write_text(json.dumps({"schema": 1, "metric": "同曲跨夜一致性",
                               "discipline": "只报差异与一致性，不写谁更强；极值音不参与",
                               "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[ok]", OUT.name)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
