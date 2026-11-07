# -*- coding: utf-8 -*-
"""现场层清洗 + 同曲跨场稳定性（唯一能站住的「现场」结论）。

清洗规则（每条都要能在页面图注里复述）：
  1. 只保留 layer=tour_live 且有 low_hz 的行
  2. 曲名非空，且不含「全场/整场/合集」（那是整场极值，不是一首歌）
  3. 同一 (曲, 日期) 多行 → 取中位（同场重复测量）
  4. 每曲至少 3 个不同场次才纳入（少于 3 场无法区分「他唱得稳」和「只唱过一次」）

统计：
  - 每曲跨场最低音的标准差（半音）与极差
  - ICC(1)：单因素随机效应，衡量「曲目间差异」占总方差的比例
    ICC 高 = 每首歌有自己稳定的音区，场次之间抖动小 → 这才是「唱功稳定」的证据
输出 analysis/out/vocal_live.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
RNG = np.random.default_rng(20261107)
NBOOT = 3000
MIN_SESSIONS = 3


def clean(v: pd.DataFrame):
    l = v[v["layer"] == "tour_live"].copy()
    l["song"] = l["song"].astype("string").fillna("").str.strip()
    total = len(l)
    empty = int((l["song"] == "").sum())
    agg = int(l["song"].str.contains("全场|整场|合集").sum())
    l = l[(l["song"] != "") & (~l["song"].str.contains("全场|整场|合集"))].dropna(subset=["low_hz"])
    # 同场重复测量合并
    l["session"] = l["date"].astype("string").fillna("") + "|" + l["city"].astype("string").fillna("")
    l["session"] = l["session"].where(l["session"].str.strip("|") != "", l["version"].astype("string"))
    merged = (l.groupby(["song", "session"])
              .agg(low_hz=("low_hz", "median"), span=("span_octaves", "median"))
              .reset_index())
    return merged, {"total": total, "empty_name": empty, "aggregate": agg,
                    "per_song_session": int(len(l)), "sessions": int(merged["session"].nunique())}


def icc1(groups):
    """单因素随机效应 ICC(1)，groups 为每曲的观测数组。"""
    groups = [g for g in groups if len(g) >= 2]
    k = len(groups)
    if k < 3:
        return None
    n = sum(len(g) for g in groups)
    grand = np.mean(np.concatenate(groups))
    ssb = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
    ssw = sum(((g - g.mean()) ** 2).sum() for g in groups)
    dfb, dfw = k - 1, n - k
    msb, msw = ssb / dfb, ssw / dfw
    k0 = (n - (sum(len(g) ** 2 for g in groups)) / n) / (k - 1)
    denom = msb + (k0 - 1) * msw
    if denom <= 0:
        return None
    return {"icc": float((msb - msw) / denom), "n_songs": k, "n_obs": int(n), "k0": float(k0)}


def main():
    v = pd.read_parquet(OUT / "vocal.parquet")
    clean_df, qc = clean(v)

    sizes = clean_df.groupby("song")["low_hz"].size()
    keep = sizes[sizes >= MIN_SESSIONS].index
    sub = clean_df[clean_df["song"].isin(keep)]

    per = sub.groupby("song")["low_hz"].agg(["size", "mean", "median", "std", "min", "max"])
    per["sd_semitone"] = 12 * np.log2((per["mean"] + per["std"].fillna(0)) / per["mean"])
    per["range_semitone"] = 12 * np.log2(per["max"] / per["min"])

    groups = [g["low_hz"].values.astype(float) for _, g in sub.groupby("song")]
    icc = icc1(groups)

    # ICC 的 bootstrap：重采样曲目
    boots = []
    for _ in range(NBOOT):
        pick = RNG.choice(len(groups), size=len(groups), replace=True)
        r = icc1([groups[i] for i in pick])
        if r:
            boots.append(r["icc"])
    icc_ci = [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))] if boots else [None, None]

    out = {
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "qc": qc,
        "method": f"清洗后仅保留「一首歌 × 一场」；每曲 ≥{MIN_SESSIONS} 场；同场重复取中位；ICC(1) 单因素随机效应",
        "n_songs_used": int(len(per)),
        "n_sessions": int(len(sub)),
        "sd_semitone": {
            "median": float(per["sd_semitone"].median()),
            "p75": float(per["sd_semitone"].quantile(0.75)),
            "p90": float(per["sd_semitone"].quantile(0.90)),
            "median_cents": float(per["sd_semitone"].median() * 100),
        },
        "range_semitone": {
            "median": float(per["range_semitone"].median()),
            "p90": float(per["range_semitone"].quantile(0.90)),
        },
        "icc": icc, "icc_ci": icc_ci,
        "detail": [{"song": k, "sessions": int(r["size"]), "median_hz": round(float(r["median"]), 1),
                    "sd_semitone": round(float(r["sd_semitone"]), 2),
                    "range_semitone": round(float(r["range_semitone"]), 2)}
                   for k, r in per.sort_values("size", ascending=False).iterrows()],
    }
    (OUT / "vocal_live.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"清洗：{qc['total']} 行 → 单曲单场 {qc['per_song_session']} 行 / {qc['sessions']} 场（剔除空名 {qc['empty_name']}、整场 {qc['aggregate']}）")
    print(f"纳入 {out['n_songs_used']} 首（≥{MIN_SESSIONS} 场，共 {out['n_sessions']} 个观测）")
    print(f"同曲跨场最低音 SD 中位 {out['sd_semitone']['median']:.2f} 半音（≈{out['sd_semitone']['median_cents']:.0f} 音分）"
          f"｜p75 {out['sd_semitone']['p75']:.2f}｜极差中位 {out['range_semitone']['median']:.2f} 半音")
    if icc:
        print(f"ICC(1) = {icc['icc']:.2f} [{icc_ci[0]:.2f}, {icc_ci[1]:.2f}]（曲目间差异占总方差；越接近 1 越说明每首歌有稳定音区）")


if __name__ == "__main__":
    main()
