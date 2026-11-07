# -*- coding: utf-8 -*-
"""规范事件研究（替代裸百分比）。

设计：
  样本    87 场演出 × 该场关联曲目 × 相对日 [-7,+14]，指数>0 才入样
  处理组  该场歌单上被演唱的曲目（on_setlist=True）
  对照组  同一场关联到但没被演唱的曲目（同场相减 → 场级共同冲击被吸收）
  模型    log(index) ~ Σ_t β_t · 1[rel=t]·treat + treat | 曲目FE + 日期FE
          聚类到事件（场次）
  检验    (1) 事件前系数联合 Wald（预趋势）(2) 全期 DiD 标量 + bootstrap CI

产出 analysis/out/did_stats.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
RNG = np.random.default_rng(20261107)


def build_long():
    panel = pd.read_parquet(OUT / "raw_panel.parquet")
    panel = panel.dropna(subset=["index"])
    panel = panel[panel["index"] > 0][["name", "date", "index"]].rename(columns={"name": "song"})
    panel["date"] = pd.to_datetime(panel["date"])

    es = pd.read_parquet(OUT / "event_song.parquet").dropna(subset=["song"])
    es["event_date"] = pd.to_datetime(es["event_date"])

    rows = []
    for (date,), g in es.groupby(["event_date"]):
        songs = g.drop_duplicates("song")[["song", "on_setlist"]]
        sub = panel[(panel["date"] >= date - pd.Timedelta(days=21)) &
                    (panel["date"] <= date + pd.Timedelta(days=14))]
        sub = sub[sub["song"].isin(songs["song"])]
        if sub.empty:
            continue
        sub = sub.merge(songs, on="song", how="left")
        sub["rel"] = (sub["date"] - date).dt.days
        sub["event"] = date
        rows.append(sub)
    df = pd.concat(rows, ignore_index=True)
    df["treat"] = df["on_setlist"].fillna(False).astype(int)
    df["log_index"] = np.log(df["index"].astype(float))
    return df


def wald(fit, terms):
    b = fit.coef()
    V = getattr(fit, "_vcov", None)
    if V is None:
        V = fit.vcov("HC1")
    if not isinstance(V, pd.DataFrame):
        V = pd.DataFrame(np.asarray(V), index=b.index, columns=b.index)
    idx = [i for i, t in enumerate(b.index) if t in terms]
    if not idx:
        return None
    beta = b.iloc[idx].values.astype(float)
    Vn = V.values[np.ix_(idx, idx)].astype(float)
    try:
        stat = float(beta.T @ np.linalg.pinv(Vn) @ beta)
    except np.linalg.LinAlgError:
        return None
    from scipy.stats import chi2
    return {"chi2": stat, "df": len(beta), "p": float(1 - chi2.cdf(stat, len(beta)))}


def main():
    df = build_long()
    df.to_parquet(OUT / "event_window.parquet", index=False)
    print(f"窗口样本 {len(df):,} 行 | 事件 {df['event'].nunique()} | 曲目 {df['song'].nunique()} | "
          f"处理行 {int(df['treat'].sum()):,} | 相对日 {df['rel'].min()}..{df['rel'].max()}")

    import pyfixest as pf

    df["rel_c"] = df["rel"].astype(str)          # 离散化，避免把时间当连续
    fml = "log_index ~ i(rel_c, treat, ref='-1') + treat | song + event"
    try:
        fit = pf.feols(fml, data=df, vcov={"CRV1": "event"})
    except Exception as e:                        # 聚类失败就退回稳健标准误
        print("聚类失败，退回 HC1：", type(e).__name__, str(e)[:120])
        fit = pf.feols(fml, data=df, vcov="HC1")

    coef = fit.coef()
    ci = fit.confint()
    curve = {}
    for term in coef.index:
        if "rel_c::" not in term or ":treat" not in term:
            continue
        rel = int(term.split("rel_c::")[1].split(":")[0].replace("T.", "").replace(".0", ""))
        curve[rel] = {"beta": float(coef[term]), "ci_lo": float(ci.loc[term].iloc[0]),
                      "ci_hi": float(ci.loc[term].iloc[1])}
    curve[-1] = {"beta": 0.0, "ci_lo": 0.0, "ci_hi": 0.0}   # 基准期

    pre_terms = [t for t in coef.index if "rel_c::-" in t and ":treat" in t]
    pre = wald(fit, pre_terms)

    # 全期 DiD 标量（对数点），bootstrap 到事件层
    def did_once(frame):
        g = frame.groupby(["event", "treat"]).apply(
            lambda x: x.loc[x["rel"] >= 0, "log_index"].mean() - x.loc[x["rel"] < 0, "log_index"].mean(),
            include_groups=False).unstack()
        if g.shape[1] < 2:
            return np.nan
        return float((g[1] - g[0]).mean())

    did = did_once(df)
    boots = []
    events = df["event"].unique()
    for _ in range(1500):
        pick = RNG.choice(events, size=len(events), replace=True)
        sub = pd.concat([df[df["event"] == e] for e in pick], ignore_index=True)
        v = did_once(sub)
        if np.isfinite(v):
            boots.append(v)
    lo, hi = np.quantile(boots, [0.025, 0.975]) if boots else (np.nan, np.nan)

    res = {
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "n_rows": int(len(df)), "n_events": int(df["event"].nunique()),
        "n_songs": int(df["song"].nunique()), "n_treat_rows": int(df["treat"].sum()),
        "curve": {str(k): v for k, v in sorted(curve.items())},
        "pre_trend": pre,
        "did_log_points": did,
        "did_pct": float((np.exp(did) - 1) * 100) if np.isfinite(did) else None,
        "did_ci_pct": [float((np.exp(lo) - 1) * 100), float((np.exp(hi) - 1) * 100)],
        "formula": fml,
    }
    (OUT / "did_stats.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    post = {k: v for k, v in curve.items() if 1 <= k <= 14}
    print("预趋势 Wald:", None if not pre else {k: round(v, 3) for k, v in pre.items()})
    print("事件后均值（对数点）:", round(np.mean([v["beta"] for v in post.values()]), 3),
          "| T+7:", round(curve[7]["beta"], 3) if 7 in curve else "-")
    print(f"DiD: {did:.3f} 对数点 = {(np.exp(did)-1)*100:.1f}%  95%CI "
          f"[{(np.exp(lo)-1)*100:.1f}%, {(np.exp(hi)-1)*100:.1f}%]")


if __name__ == "__main__":
    main()
