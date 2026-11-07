# -*- coding: utf-8 -*-
"""口径敏感性：同一批演出，换基线窗/事后窗，结论会不会翻。

这是整份分析里最该给外行看的一张表——它回答「你信哪个数字，取决于我选了哪段基线」。
输出 analysis/out/sensitivity.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20261107)

BASELINES = [(-7, -1), (-14, -8), (-21, -8), (-21, -15)]
POSTS = [(0, 6), (0, 13)]


def did_frame(df, base, post):
    b0, b1 = base
    p0, p1 = post
    rows = []
    for ev, g in df.groupby("event"):
        pre = g[(g["rel"] >= b0) & (g["rel"] <= b1)]
        aft = g[(g["rel"] >= p0) & (g["rel"] <= p1)]
        if pre.empty or aft.empty:
            continue
        t_pre = pre.loc[pre["treat"] == 1, "log_index"].mean()
        t_aft = aft.loc[aft["treat"] == 1, "log_index"].mean()
        c_pre = pre.loc[pre["treat"] == 0, "log_index"].mean()
        c_aft = aft.loc[aft["treat"] == 0, "log_index"].mean()
        if not np.isfinite([t_pre, t_aft, c_pre, c_aft]).all():
            continue
        rows.append({"event": ev, "did": (t_aft - t_pre) - (c_aft - c_pre)})
    return pd.DataFrame(rows)


def summarize(fr, label):
    if fr.empty:
        return None
    v = fr["did"].values
    boots = np.array([RNG.choice(v, len(v), replace=True).mean() for _ in range(2000)])
    lo, hi = np.quantile(boots, [0.025, 0.975])
    return {
        "label": label, "n_events": int(len(v)),
        "did_pct": float((np.exp(v.mean()) - 1) * 100),
        "ci_lo_pct": float((np.exp(lo) - 1) * 100), "ci_hi_pct": float((np.exp(hi) - 1) * 100),
        "median_pct": float((np.exp(np.median(v)) - 1) * 100),
        "share_positive": float((v > 0).mean()),
        "p_sign": float(min((v > 0).mean(), (v < 0).mean()) * 2),
    }


def main():
    df = pd.read_parquet(OUT / "event_window.parquet")
    res = {"generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "cells": []}
    for base in BASELINES:
        for post in POSTS:
            fr = did_frame(df, base, post)
            s = summarize(fr, f"基线[{base[0]},{base[1]}] × 事后[{post[0]},{post[1]}]")
            if s:
                s.update({"base": base, "post": post})
                res["cells"].append(s)
    (OUT / "sensitivity.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    for c in res["cells"]:
        print(f"{c['label']:<34} DiD={c['did_pct']:>6.1f}%  [{c['ci_lo_pct']:>6.1f}, {c['ci_hi_pct']:>6.1f}]"
              f"  中位={c['median_pct']:>6.1f}%  正= {c['share_positive']:.0%}  n={c['n_events']}")


if __name__ == "__main__":
    main()
