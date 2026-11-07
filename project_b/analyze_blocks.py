#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双人场块级分析：用「同一场、同一套录音」的两位歌手做场内对照 + 块级方差。

为什么这个对照值钱
  之前所有跨场比较都缺对照组。双人场给了另一种可能：**同一晚、同一录音链、同一场馆**，
  两位歌手交替演唱——录音条件被固定住，剩下的差异更接近"人"的差异而不是"录音"的差异。

数据来源（站内已存在，不用再问用户）
  data/show_setlists/2026-10-09_北京.json          分段歌单 + 每段演唱者(by)
  data/show_blocks/沉响与长歌_20261009.json        18 个块（who_confirmed / 时间范围 / 指标）
  data/show_blocks/沉响与长歌_20261010.json        10 个块（同上）

产出：data/block_analysis.json
用法：python -X utf8 project_b\\analyze_blocks.py
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import date
from pathlib import Path

from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "block_analysis.json"
BLOCK_FILES = [
    ROOT / "data" / "show_blocks" / "沉响与长歌_20261009.json",
    ROOT / "data" / "show_blocks" / "沉响与长歌_20261010.json",
]
METRICS = {
    "f0_median_midi": "演唱音高中位（MIDI）",
    "low_ratio_db": "低频占比（dB）",
    "stability_cents_median": "音符内稳定性（音分）",
    "intonation_cents_median": "音准偏差（音分）",
    "vibrato_hz_median": "颤音速率（Hz）",
    "vibrato_cents_median": "颤音幅度（音分）",
    "density_per_s": "音符密度（/s）",
    "hnr_db_median": "HNR（dB）",
}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def norm_who(w):
    w = (w or "").strip()
    if w.startswith("王晰"):
        return "王晰"
    if w.startswith("傲日"):
        return "傲日其愣"
    return "未定"


def load_blocks():
    rows = []
    for f in BLOCK_FILES:
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        show = "%s|%s" % ((d.get("show") or {}).get("date") or f.stem,
                          (d.get("show") or {}).get("venue") or "")
        for b in d.get("blocks") or []:
            if not b.get("in_stats", True):
                continue
            rows.append({"show": show, "who": norm_who(b.get("who_confirmed")),
                         "dur": b.get("dur_s"),
                         **{k: b.get(k) for k in METRICS}})
    return rows


def compare(rows, key):
    a = [float(r[key]) for r in rows if r["who"] == "王晰" and r.get(key) is not None]
    b = [float(r[key]) for r in rows if r["who"] == "傲日其愣" and r.get(key) is not None]
    if len(a) < 3 or len(b) < 3:
        return None
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    # 秩二列相关效应量
    n1, n2 = len(a), len(b)
    r = 1 - (2 * u) / (n1 * n2)
    return {"n_wang": n1, "n_aori": n2,
            "median_wang": round(statistics.median(a), 2),
            "median_aori": round(statistics.median(b), 2),
            "diff": round(statistics.median(a) - statistics.median(b), 2),
            "U": float(u), "p": round(float(p), 4), "r": round(abs(r), 2)}


def icc(groups):
    groups = [g for g in groups if len(g) >= 1]
    k = len(groups)
    N = sum(len(g) for g in groups)
    if k < 3 or N - k < 3:
        return None
    grand = sum(sum(g) for g in groups) / N
    ssb = sum(len(g) * (sum(g) / len(g) - grand) ** 2 for g in groups)
    ssw = sum(sum((x - sum(g) / len(g)) ** 2 for x in g) for g in groups)
    msb, msw = ssb / (k - 1), ssw / (N - k)
    n0 = (N - sum(len(g) ** 2 for g in groups) / N) / (k - 1)
    vb = max(0.0, (msb - msw) / n0)
    tot = vb + msw
    return round(100 * vb / tot, 1) if tot > 0 else 0.0


def main() -> int:
    rows = load_blocks()
    if not rows:
        print("没有块级数据")
        return 1
    n_wang = sum(1 for r in rows if r["who"] == "王晰")
    n_aori = sum(1 for r in rows if r["who"] == "傲日其愣")
    print("块级素材 %d 条｜王晰 %d｜傲日其愣 %d｜未定 %d｜场次 %d"
          % (len(rows), n_wang, n_aori, len(rows) - n_wang - n_aori, len({r["show"] for r in rows})))

    out = {"schema": "block-analysis/v1", "generated_at": date.today().isoformat(),
           "design": ("同场同录音链的两位歌手交替演唱 → 场内对照；"
                      "块级指标为整块中位，不做逐音归属"),
           "n_blocks": len(rows), "n_wang": n_wang, "n_aori": n_aori,
           "metrics": {}, "icc": {}}

    print("\n场内对照（王晰 vs 傲日其愣，Mann–Whitney 双侧）：")
    for k, label in METRICS.items():
        c = compare(rows, k)
        if c:
            out["metrics"][k] = {"label": label, **c}
            flag = "★" if c["p"] < 0.05 else " "
            print("  %s %-18s 王 %6.2f vs 傲 %6.2f（差 %+6.2f）p=%.4f r=%.2f"
                  % (flag, label, c["median_wang"], c["median_aori"], c["diff"], c["p"], c["r"]))

    print("\n块级方差（ICC，%）：")
    for k in METRICS:
        vals = [r for r in rows if r.get(k) is not None]
        if len(vals) < 12:
            continue
        by_show = {}
        by_who = {}
        for r in vals:
            by_show.setdefault(r["show"], []).append(float(r[k]))
            by_who.setdefault(r["who"], []).append(float(r[k]))
        icc_show, icc_who = icc(list(by_show.values())), icc(list(by_who.values()))
        out["icc"][k] = {"by_show": icc_show, "by_singer": icc_who}
        print("  %-18s 按场次 %5.1f%%｜按歌手 %5.1f%%" % (METRICS[k], icc_show or 0, icc_who or 0))

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n→", OUT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
