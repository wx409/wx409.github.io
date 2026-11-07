# -*- coding: utf-8 -*-
"""事件后逐日曲线（DiD 口径，事件级 bootstrap）。

为什么不用 FE 系数画曲线：FE 与 DiD 标量在长窗口下会给出一正一负，两者混在
一页里读者只会更困惑。这里统一用「同场相减、再对场次取等权平均」的口径，
与 sensitivity.json 的标量完全同源，图上每个点都能对上表里那一行。

基线：每场每曲 rel∈[-7,-1] 的均值（要求 ≥3 天）；事件日 rel=0 为演出当天。
输出 analysis/out/curve.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "out"
RNG = np.random.default_rng(20261107)
NBOOT = 4000
RELS = list(range(0, 15))


def build():
    df = pd.read_parquet(OUT / "event_window.parquet")
    df = df[(df["rel"] >= -7) & (df["rel"] <= 14)].copy()
    base = (df[df["rel"] < 0].groupby(["event", "song", "treat"])["log_index"]
            .agg(["mean", "count"]).reset_index())
    base = base[base["count"] >= 3].rename(columns={"mean": "base"})
    df = df.merge(base[["event", "song", "treat", "base"]], on=["event", "song", "treat"], how="inner")
    df["delta"] = df["log_index"] - df["base"]
    return df


def curve(df):
    out = []
    for t in RELS:
        g = df[df["rel"] == t]
        per_event = []
        for ev, eg in g.groupby("event"):
            a = eg.loc[eg["treat"] == 1, "delta"]
            c = eg.loc[eg["treat"] == 0, "delta"]
            if len(a) >= 1 and len(c) >= 3:
                per_event.append(a.mean() - c.mean())
        v = np.array(per_event, dtype=float)
        if len(v) < 5:
            continue
        draws = np.array([RNG.choice(v, len(v), replace=True).mean() for _ in range(NBOOT)])
        out.append({
            "rel": t, "effect_pct": float((np.exp(v.mean()) - 1) * 100),
            "ci_lo_pct": float((np.exp(np.quantile(draws, 0.025)) - 1) * 100),
            "ci_hi_pct": float((np.exp(np.quantile(draws, 0.975)) - 1) * 100),
            "median_pct": float((np.exp(np.median(v)) - 1) * 100),
            "share_positive": float((v > 0).mean()), "n_events": int(len(v)),
        })
    return out


def heterogeneity(df, rel_max=6):
    g = df[(df["rel"] >= 0) & (df["rel"] <= rel_max)]
    per_event = []
    for ev, eg in g.groupby("event"):
        a = eg.loc[eg["treat"] == 1, "delta"]
        c = eg.loc[eg["treat"] == 0, "delta"]
        if len(a) and len(c) >= 3:
            per_event.append({"event": ev, "diff": a.mean() - c.mean()})
    pe = pd.DataFrame(per_event)
    meta = pd.read_parquet(OUT / "events.parquet")[["event_date", "content_type", "city_tier", "venue_type"]]
    meta["event_date"] = pd.to_datetime(meta["event_date"])
    pe = pe.merge(meta, left_on="event", right_on="event_date", how="left")
    res = {}
    for col in ("content_type", "city_tier"):
        rows = []
        for name, gg in pe.groupby(col):
            v = gg["diff"].dropna().values
            if len(v) < 6:
                continue
            draws = np.array([RNG.choice(v, len(v), replace=True).mean() for _ in range(NBOOT)])
            rows.append({"group": str(name), "n": int(len(v)),
                         "effect_pct": float((np.exp(v.mean()) - 1) * 100),
                         "ci_lo_pct": float((np.exp(np.quantile(draws, 0.025)) - 1) * 100),
                         "ci_hi_pct": float((np.exp(np.quantile(draws, 0.975)) - 1) * 100)})
        res[col] = sorted(rows, key=lambda r: -r["effect_pct"])
    return res


def main():
    df = build()
    c = curve(df)
    summary = {
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "method": "同场 DiD：被演唱曲目 − 同场未演唱曲目；基线 rel[-7,-1]（≥3 天）；事件等权；bootstrap 4000 次",
        "n_rows": int(len(df)), "n_events": int(df["event"].nunique()),
        "curve": c,
        "week1_pct": float(np.mean([x["effect_pct"] for x in c if x["rel"] <= 6])),
        "heterogeneity": heterogeneity(df),
    }
    (OUT / "curve.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("曲线（rel: 效应% [CI] 事件数）:")
    for x in c:
        print(f"  T+{x['rel']:<2} {x['effect_pct']:>6.1f}%  [{x['ci_lo_pct']:>6.1f},{x['ci_hi_pct']:>6.1f}]  n={x['n_events']}")
    print("首周均值: %.1f%%" % summary["week1_pct"])
    for col, rows in summary["heterogeneity"].items():
        print(col, [(r["group"], round(r["effect_pct"], 1), r["n"]) for r in rows])


if __name__ == "__main__":
    main()
