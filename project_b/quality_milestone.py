#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""quality_milestone.py —— 「音质达标」阶段性通知

达标口径（可调）：
  1 缺口 ≤ --max-gap 首（默认 60）
  2 已入库 B站 单曲音轨的**中位数** ≥ --min-median kbps（默认 200）
  3 无损（自录/小卡带）占比 ≥ --min-lossless（默认 0.6）
三个条件同时满足 → 推送一次「阶段性成功」通知，并写 data/milestone.json 记为已通知（不重复打扰）。

用法：
  python -X utf8 project_b/quality_milestone.py            # 检查并通知
  python -X utf8 project_b/quality_milestone.py --check    # 只看是否达标
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
FLAG = DATA / "milestone.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--max-gap", type=int, default=60)
    ap.add_argument("--min-median", type=int, default=200)
    ap.add_argument("--min-lossless", type=float, default=0.6)
    args = ap.parse_args()

    cov = json.loads((DATA / "song_coverage_status.json").read_text(encoding="utf-8"))
    gap = len(cov.get("missing") or [])

    from openpyxl import load_workbook
    wb = load_workbook(DATA / "最优音频清单.xlsx")
    ws = wb["最优音频"]
    cols = [c.value for c in ws[1]]
    idx = {c: i for i, c in enumerate(cols)}

    bili_kbps, lossless, total = [], 0, 0
    for r in ws.iter_rows(min_row=2, values_only=True):
        note = str(r[idx["备注"]] or "") if "备注" in idx else ""
        if "已归档" in note:
            continue
        total += 1
        src = str(r[idx["来源"]] or "")
        if any(k in src for k in ("小卡带", "自录", "中控台")):
            lossless += 1
            continue
        if not src.startswith("B站-"):
            continue
        m = re.search(r"(\d+)\s*kbps", str(r[idx["级别"]] or ""))
        if m:
            bili_kbps.append(int(m.group(1)))

    med = round(statistics.median(bili_kbps)) if bili_kbps else 0
    ratio = round(lossless / total, 3) if total else 0
    ok = gap <= args.max_gap and med >= args.min_median and ratio >= args.min_lossless

    print(f"缺口 {gap}（≤{args.max_gap}）| B站中位 {med}kbps（≥{args.min_median}）| 无损占比 {ratio:.0%}（≥{args.min_lossless:.0%}）→ {'达标' if ok else '未达标'}")
    if args.check or not ok:
        return 0

    prev = {}
    if FLAG.exists():
        try:
            prev = json.loads(FLAG.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    if prev.get("notified") and prev.get("gap", 999) <= gap:
        print("已通知过且未变好，不重复推送")
        return 0

    try:
        sys.path.insert(0, str(ROOT / "project_b"))
        import notify
        notify.record("音质达标（阶段性完成）",
                      f"一到六巡音频补全达到阶段目标：缺口 {gap} 首，B站音轨中位 {med} kbps，无损占比 {ratio:.0%}。"
                      f"之后转入个别替换（发现更高码率再换）。详见 data/缺口登记.md",
                      category="里程碑", source="quality_milestone")
        print("已推送阶段通知")
    except Exception as e:
        print("通知失败:", e)
    FLAG.write_text(json.dumps({"notified": True, "gap": gap, "median_kbps": med,
                                "lossless_ratio": ratio,
                                "time": datetime.now().strftime("%Y-%m-%d %H:%M")},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
