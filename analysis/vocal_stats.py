# -*- coding: utf-8 -*-
"""唱功证据：录音室 vs 现场的音域稳定性 + 测量不确定性。

数据：data/vocal_measurements.json（1006 行 = 曲目 × 版本；谱系分层）
方法：
  1) 录音室 72 首的最低音分布（不是单点 B1，而是分布 + 分位）
  2) 同曲配对：录音室 vs 现场，Δ最低音（半音）、Δ跨度（八度），bootstrap CI
  3) 复核状态分层：只用「已复核」子集重算，看结论是否依赖未复核样本
  4) 引擎分歧：把 B1 61.5Hz 报成区间（±50 音分），并注明来源文件的 publishable=False
输出 analysis/out/vocal_stats.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
RNG = np.random.default_rng(20261107)
NBOOT = 4000

VERIFIED = {"谐波列复核通过", "谐波列复核通过（全曲口径对账）", "谐波列复核通过（同刻三源）",
            "双引擎一致", "人耳确认（听辨）", "已核验", "已取证", "已测"}


def semitones(hz_from, hz_to):
    return 12 * np.log2(np.asarray(hz_to, dtype=float) / np.asarray(hz_from, dtype=float))


def boot_mean(v, nboot=NBOOT):
    v = np.asarray([x for x in v if np.isfinite(x)], dtype=float)
    if len(v) < 3:
        return None
    draws = np.array([RNG.choice(v, len(v), replace=True).mean() for _ in range(nboot)])
    return {"mean": float(v.mean()), "ci_lo": float(np.quantile(draws, 0.025)),
            "ci_hi": float(np.quantile(draws, 0.975)), "n": int(len(v))}


def share(v, cond):
    v = np.asarray([x for x in v if np.isfinite(x)], dtype=float)
    return float(np.mean(cond(v))) if len(v) else float("nan")


def main():
    v = pd.read_parquet(OUT / "vocal.parquet")
    v["verified"] = v["verify_state"].isin(VERIFIED)

    studio = v[v["layer"] == "studio_album"].dropna(subset=["low_hz"])
    live = v[v["layer"] == "tour_live"].dropna(subset=["low_hz"])

    # 1) 录音室最低音分布（B1 = 61.74Hz，±50 音分 ≈ 60.0–63.5Hz）
    b1_lo, b1_hi = 61.74 * 2 ** (-50 / 1200), 61.74 * 2 ** (50 / 1200)
    res = {
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "n_studio": int(len(studio)), "n_live_rows": int(len(live)),
        "studio_low_hz": {
            "min": float(studio["low_hz"].min()), "p10": float(studio["low_hz"].quantile(0.10)),
            "median": float(studio["low_hz"].median()), "p90": float(studio["low_hz"].quantile(0.90)),
            "n_reach_b1": int(((studio["low_hz"] >= b1_lo) & (studio["low_hz"] <= b1_hi)).sum()),
            "n_below_c2": int((studio["low_hz"] < 65.41).sum()),
            "b1_window_hz": [round(b1_lo, 2), round(b1_hi, 2)],
        },
        "studio_span_octaves": boot_mean(studio["span_octaves"]),
        "studio_span_share_ge2": share(studio["span_octaves"], lambda x: x >= 2),
    }

    # 2) 同曲配对（录音室 vs 现场），每曲取中位
    s = studio.groupby("song").agg(s_low=("low_hz", "median"), s_span=("span_octaves", "median"))
    l = live.groupby("song").agg(l_low=("low_hz", "median"), l_span=("span_octaves", "median"),
                                 l_n=("low_hz", "size"))
    pair = s.join(l, how="inner").dropna(subset=["l_low"])
    pair["d_semitone"] = semitones(pair["s_low"], pair["l_low"])   # >0 = 现场低音更高（掉了）
    pair["d_span"] = pair["l_span"] - pair["s_span"]
    res["paired"] = {
        "n_songs": int(len(pair)),
        "median_live_sessions": float(pair["l_n"].median()),
        "d_semitone": boot_mean(pair["d_semitone"]),
        "share_kept_or_lower": float((pair["d_semitone"] <= 0.5).mean()),   # 允许半个半音的测量误差
        "share_live_deeper": float((pair["d_semitone"] < -0.5).mean()),
        "d_span_octaves": boot_mean(pair["d_span"]),
        "pairs": [{"song": k, "studio_hz": round(r.s_low, 1), "live_hz": round(r.l_low, 1),
                   "d_semitone": round(r.d_semitone, 2), "live_n": int(r.l_n)}
                  for k, r in pair.iterrows()],
    }

    # 3) 只用已复核样本重算配对
    sv = studio[studio["verified"]]
    lv = live[live["verified"]]
    if len(sv) and len(lv):
        s2 = sv.groupby("song")["low_hz"].median()
        l2 = lv.groupby("song")["low_hz"].median()
        p2 = pd.concat([s2.rename("s"), l2.rename("l")], axis=1).dropna()
        res["paired_verified_only"] = {
            "n_songs": int(len(p2)),
            "d_semitone": boot_mean(semitones(p2["s"], p2["l"])),
        }

    # 4) 测量不确定性（引用站点自己的双引擎诊断）
    eng = json.loads((HERE.parent / "data" / "derived" / "engine_disagreement.json").read_text(encoding="utf-8"))
    res["measurement_uncertainty"] = {
        "engines": eng.get("engines"),
        "tolerance_cents": eng.get("protocol", {}).get("tol_cents"),
        "agreement_median_pct": {k: v.get("agree_pct_median") for k, v in (eng.get("summary") or {}).items()},
        "publishable": eng.get("publishable"),
        "note": "双引擎在 ±50 音分内一致的帧占比中位数；分歧来自八度/次谐波判定，不是音高真值误差。",
    }

    # 5) 分层计数，供图注写 n
    res["layer_counts"] = v["layer"].value_counts().to_dict()
    res["verify_counts"] = v["verify_state"].value_counts().head(8).to_dict()

    (OUT / "vocal_stats.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")

    sl = res["studio_low_hz"]
    print(f"录音室 {len(studio)} 首：最低 {sl['min']:.1f}Hz / p10 {sl['p10']:.1f} / 中位 {sl['median']:.1f} / p90 {sl['p90']:.1f}")
    print(f"  落在 B1±50¢（{sl['b1_window_hz'][0]}–{sl['b1_window_hz'][1]}Hz）的曲目：{sl['n_reach_b1']} 首；低于 C2：{sl['n_below_c2']} 首")
    sp = res["studio_span_octaves"]
    print(f"  跨度：{sp['mean']:.2f} 八度 [{sp['ci_lo']:.2f},{sp['ci_hi']:.2f}]，≥2 八度占 {res['studio_span_share_ge2']:.0%}")
    p = res["paired"]
    print(f"同曲配对 {p['n_songs']} 首（现场中位 {p['median_live_sessions']:.0f} 场）：")
    print(f"  Δ最低音 {p['d_semitone']['mean']:+.2f} 半音 [{p['d_semitone']['ci_lo']:+.2f},{p['d_semitone']['ci_hi']:+.2f}]"
          f"（>0=现场更高）｜保持或更低 {p['share_kept_or_lower']:.0%}｜现场更深 {p['share_live_deeper']:.0%}")
    print(f"  Δ跨度 {p['d_span_octaves']['mean']:+.2f} 八度 [{p['d_span_octaves']['ci_lo']:+.2f},{p['d_span_octaves']['ci_hi']:+.2f}]")
    if "paired_verified_only" in res:
        q = res["paired_verified_only"]
        print(f"  仅用已复核：{q['n_songs']} 首，Δ {q['d_semitone']['mean']:+.2f} 半音 "
              f"[{q['d_semitone']['ci_lo']:+.2f},{q['d_semitone']['ci_hi']:+.2f}]")
    print("引擎一致率:", res["measurement_uncertainty"]["agreement_median_pct"])


if __name__ == "__main__":
    main()
