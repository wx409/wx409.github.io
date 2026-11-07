#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给「状态 vs 特质」的方差成分加自助法区间（cluster bootstrap）。

为什么要做：上一轮 MixedLM 给出的场次解释率是 4.9%，曲目是 0.0%（边界值）。
点估计没有区间，就无法回答"4.9% 到底算不算数"。

做法
  · 方差成分用矩估计（one-way random effects，不平衡组也适用），无优化器、无收敛问题：
        σ²_within  = MSW
        σ²_between = max(0, (MSB − MSW) / n0),  n0 = (N − Σnᵢ²/N)/(k−1)
        ICC        = σ²_between / (σ²_between + σ²_within)
  · 区间用**按组整群重采样**（场次/曲目各自有放回抽样，保留组内结构），2000 次
  · 判定：若 95% 区间下界 ≤ 0（或很接近 0），就写"无法与噪声区分"，不给漂亮话

输出：data/variance_bootstrap.json
用法：python -X utf8 project_b\\variance_bootstrap.py [--boot 2000]
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "archive_stage_tour.json"
OUT = ROOT / "data" / "variance_bootstrap.json"

METRICS = {
    "vibrato_hz": "颤音速率 Hz",
    "vibrato_cents": "颤音幅度 音分",
    "stability_cents": "音符内稳定性 音分",
    "intonation_cents": "音准偏差 音分",
}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    rows = []
    for r in d.get("rows") or []:
        song = (r.get("song") or "").strip()
        show = "%s|%s" % (r.get("date") or "", r.get("city") or "")
        if not song or len(show) < 10:
            continue
        rows.append({"song": song, "show": show, **{k: r.get(k) for k in METRICS}})
    return rows


def icc_mom(groups):
    """groups: list[list[float]] → (icc, n, k)。矩估计，组内空/单点也容忍。"""
    groups = [g for g in groups if g]
    k = len(groups)
    N = sum(len(g) for g in groups)
    if k < 3 or N - k < 3:
        return None
    grand = sum(sum(g) for g in groups) / N
    ssb = sum(len(g) * (sum(g) / len(g) - grand) ** 2 for g in groups)
    ssw = sum(sum((x - sum(g) / len(g)) ** 2 for x in g) for g in groups)
    msb, msw = ssb / (k - 1), ssw / (N - k)
    n0 = (N - sum(len(g) ** 2 for g in groups) / N) / (k - 1)
    vb = max(0.0, (msb - msw) / n0) if n0 > 0 else 0.0
    vw = msw
    tot = vb + vw
    return (vb / tot if tot > 0 else 0.0), N, k


def boot_ci(rows, key, ngram, metric, nboot, seed):
    by = {}
    for r in rows:
        v = r.get(metric)
        if v is None or v <= 0:
            continue
        by.setdefault(r[key], []).append(float(v))
    keys = list(by)
    point = icc_mom(list(by.values()))
    if not point:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(nboot):
        pick = [by[rng.choice(keys)] for _ in range(len(keys))]
        # 整群重采样后组标签重复，直接按"每次抽到的组"当作独立组
        res = icc_mom(pick)
        if res:
            vals.append(res[0])
    vals.sort()
    lo = vals[int(0.025 * len(vals))] if vals else None
    hi = vals[int(0.975 * len(vals)) - 1] if vals else None
    return {"icc": round(point[0] * 100, 1), "n": point[1], "k": point[2],
            "ci95": [round(lo * 100, 1), round(hi * 100, 1)] if vals else None,
            "n_boot": len(vals)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261107)
    args = ap.parse_args()

    rows = load()
    print("素材 %d 条（有曲目归属）" % len(rows))
    out = {"schema": "variance-bootstrap/v1",
           "method": "矩估计 one-way random effects；整群自助法（场次/曲目分别有放回）",
           "n_boot": args.boot, "generated_at": date.today().isoformat(), "metrics": {}}

    for col, label in METRICS.items():
        show = boot_ci(rows, "show", None, col, args.boot, args.seed)
        song = boot_ci(rows, "song", None, col, args.boot, args.seed + 1)
        out["metrics"][col] = {"label": label, "show": show, "song": song}
        def fmt(x):
            if not x:
                return "样本不足"
            return "%5.1f%%  95%%CI [%s, %s]" % (x["icc"], x["ci95"][0], x["ci95"][1]) if x["ci95"] else "—"
        print("  %-16s 场次解释 %s" % (label, fmt(show)))
        print("  %-16s 曲目解释 %s" % ("", fmt(song)))

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    # 一句话判读
    v = out["metrics"]["vibrato_hz"]["show"]
    if v and v["ci95"]:
        verdict = ("颤音速率的场次解释率 %s%%，95%%CI [%s, %s]：%s"
                   % (v["icc"], v["ci95"][0], v["ci95"][1],
                      "与 0 无法区分，不能声称'场次状态有差别'" if v["ci95"][0] <= 0.5
                      else "区间不含 0，场次差异成立但幅度有限"))
        print("\n判读：" + verdict)
        out["verdict"] = verdict
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
