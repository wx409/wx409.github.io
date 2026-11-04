#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重算巡演现场层的派生跨度（唯一口径：逐条明细里显示的那一对音）。

背景：data/archive_stage_tour.json 里 18 行的 span_octaves 与
low_hz/high_hz 不自洽（多数恰好 +1.00 八度，属上游在极值被降级/替换后
没有重算派生值）。页面把两者并排展示，读者会直接看出矛盾。

本脚本只改派生字段，不动任何原始读数：
  · rows[].span_octaves   ← log2(high_hz / low_hz)
  · by_tour[].span_median_octaves ← 该巡内 rows 跨度的 statistics.median
  · summary.span_median_octaves   ← 全部 rows 跨度的 statistics.median
并在 derived_fix 里留审计痕迹（改了几行、口径、时间）。

用法（工作目录 D:\\wx409.github.io）：
    python -X utf8 project_b\\fix_stage_derived.py --dry-run
    python -X utf8 project_b\\fix_stage_derived.py
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOUR = ROOT / "data" / "archive_stage_tour.json"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def span_of(r):
    lo, hi = r.get("low_hz"), r.get("high_hz")
    if not lo or not hi or hi <= lo:
        return None
    return round(math.log2(hi / lo), 2)


def main() -> int:
    ap = argparse.ArgumentParser(description="重算 archive_stage_tour 的派生跨度")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    t = json.loads(TOUR.read_text(encoding="utf-8"))
    rows = t.get("rows") or []
    changed = []
    spans_all = []
    for r in rows:
        calc = span_of(r)
        if calc is None:
            continue
        spans_all.append(calc)
        old = r.get("span_octaves")
        if old is None or abs(float(old) - calc) > 0.005:
            changed.append((r.get("tour"), r.get("city"), r.get("date"),
                            r.get("low_note"), r.get("low_hz"),
                            r.get("high_note"), r.get("high_hz"), old, calc))
            r["span_octaves"] = calc
        else:
            r["span_octaves"] = calc

    # 巡次中位
    by_tour = t.get("by_tour") or []
    for x in by_tour:
        vals = [r["span_octaves"] for r in rows
                if r.get("tour") == x.get("tour") and r.get("span_octaves") is not None]
        if vals:
            x["span_median_octaves"] = round(statistics.median(vals), 2)

    s = t.setdefault("summary", {})
    old_med = s.get("span_median_octaves")
    new_med = round(statistics.median(spans_all), 2) if spans_all else old_med
    s["span_median_octaves"] = new_med
    s["span_basis"] = "逐条明细同一对音（low_hz→high_hz，已过复核门槛），跨度=log2(高/低)"

    t["derived_fix"] = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "field": "span_octaves",
        "rule": "由 low_hz/high_hz 重算，不再沿用上游极值被替换前的旧值",
        "rows_changed": len(changed),
        "span_median_before": old_med,
        "span_median_after": new_med,
    }

    print("跨度重算：%d 行变更｜中位 %s → %s" % (len(changed), old_med, new_med))
    for c in changed:
        print("  %s｜%s %s：%s %.1f → %s %.1f  %s → %s" % (
            c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8]))
    if args.dry_run:
        print("dry-run，未写盘")
        return 0
    TOUR.write_text(json.dumps(t, ensure_ascii=False, indent=2), encoding="utf-8")
    print("已写回", TOUR.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
