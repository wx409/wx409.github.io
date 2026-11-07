# -*- coding: utf-8 -*-
"""唱功证据的唯一数据根源 → 可渲染的事实包（不写死任何数字）。

数据根源：data/vocal_measurements.json（站内自称「声学测量统一长表，一行=一首歌×一个版本」）
本脚本只做三件事：
  1. 读这一份长表，按层（录音室/现场/严格精测/他人舞台）分组
  2. 算每个声学维度的中位数、bootstrap 95% CI、n
  3. 写 dashboard/vocal_claims.json —— 页面、大屏一行结论、自动报告都只读这个文件

禁止在任何 HTML/MD 里手写「4 首」「61.5Hz」「0.33」这类数字；改数据后重跑即可。
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

SITE = Path(r"D:\wx409.github.io")
SRC = SITE / "data" / "vocal_measurements.json"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
RNG = np.random.default_rng(20261108)
NBOOT = 3000

METRICS = ["low_hz", "high_hz", "span_octaves", "intonation_cents",
           "stability_cents", "vibrato_hz", "vibrato_cents", "hnr_db",
           "duration_s", "density_per_s"]

LAYER_LABEL = {
    "studio_album": "录音室专辑",
    "single": "网易云独有单曲/OST",
    "precision": "十曲严格精测",
    "tour_live": "王晰主导巡演现场",
    "stage_other": "他人主导舞台",
}

# 现场层里这些名字是「整场」或占位，不是一首歌
AGG_MARKERS = ("全场", "整场", "合集")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    rows = []
    for r in d["rows"]:
        m = r.get("metrics") or {}
        v = r.get("verify") or {}
        rows.append({
            "song": (r.get("song") or "").strip(),
            "version": r.get("version"), "layer": r.get("layer"),
            "tour": r.get("tour"), "city": r.get("city"), "date": r.get("date"),
            "verify": v.get("state"),
            **{k: m.get(k) for k in METRICS},
        })
    df = pd.DataFrame(rows)
    for c in METRICS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df, d


def ci_median(values, alpha=0.05):
    v = np.asarray([x for x in values if np.isfinite(x)], dtype=float)
    n = len(v)
    if n < 3:
        return None
    draws = np.array([np.median(RNG.choice(v, n, replace=True)) for _ in range(NBOOT)])
    return {"n": int(n), "median": float(np.median(v)),
            "ci_lo": float(np.quantile(draws, alpha / 2)),
            "ci_hi": float(np.quantile(draws, 1 - alpha / 2)),
            "p25": float(np.quantile(v, 0.25)), "p75": float(np.quantile(v, 0.75))}


def cohort_stats(df):
    out = {}
    for m in METRICS:
        s = ci_median(df[m])
        if s:
            out[m] = s
    return out


def live_clean(df):
    """只保留「一首歌 × 一场」的现场记录。"""
    l = df[df["layer"] == "tour_live"].copy()
    l["song"] = l["song"].fillna("")
    qc = {"total": int(len(l)),
          "unnamed": int((l["song"] == "").sum()),
          "aggregate": int(l["song"].str.contains("|".join(AGG_MARKERS)).sum())}
    l = l[(l["song"] != "") & (~l["song"].str.contains("|".join(AGG_MARKERS)))]
    l = l.dropna(subset=["low_hz"])
    l["session"] = (l["date"].astype("string").fillna("") + "|" +
                    l["city"].astype("string").fillna(""))
    l["session"] = l["session"].where(l["session"].str.strip("|") != "",
                                      l["version"].astype("string").fillna(""))
    l = (l.groupby(["song", "session"], as_index=False)
         .agg({**{m: "median" for m in METRICS if m in l.columns}}))
    qc["per_song_session"] = int(len(l))
    qc["sessions"] = int(l["session"].nunique())
    return l, qc


def icc1(groups):
    groups = [g for g in groups if len(g) >= 2]
    k = len(groups)
    if k < 3:
        return None
    n = sum(len(g) for g in groups)
    grand = float(np.mean(np.concatenate(groups)))
    ssb = sum(len(g) * (float(g.mean()) - grand) ** 2 for g in groups)
    ssw = sum(float(((g - g.mean()) ** 2).sum()) for g in groups)
    msb, msw = ssb / (k - 1), ssw / (n - k)
    k0 = (n - sum(len(g) ** 2 for g in groups) / n) / (k - 1)
    den = msb + (k0 - 1) * msw
    if den <= 0:
        return None
    return {"icc": float((msb - msw) / den), "n_songs": int(k), "n_obs": int(n)}


def stability(live, min_sessions=3):
    sizes = live.groupby("song")["low_hz"].size()
    keep = sizes[sizes >= min_sessions].index
    sub = live[live["song"].isin(keep)]
    per = sub.groupby("song")["low_hz"].agg(["size", "mean", "median", "std", "min", "max"])
    per["sd_semitone"] = 12 * np.log2((per["mean"] + per["std"].fillna(0)) / per["mean"])
    per["range_semitone"] = 12 * np.log2(per["max"] / per["min"])
    groups = [g["low_hz"].values.astype(float) for _, g in sub.groupby("song")]
    base = icc1(groups)
    boots = []
    for _ in range(1500):
        pick = RNG.choice(len(groups), size=len(groups), replace=True)
        r = icc1([groups[i] for i in pick])
        if r:
            boots.append(r["icc"])
    icc = dict(base) if base else None
    if icc:
        icc["ci_lo"], icc["ci_hi"] = (float(np.quantile(boots, 0.025)),
                                      float(np.quantile(boots, 0.975))) if boots else (None, None)
    detail = [{"song": k, "sessions": int(r["size"]), "median_hz": round(float(r["median"]), 1),
               "sd_semitone": round(float(r["sd_semitone"]), 2),
               "range_semitone": round(float(r["range_semitone"]), 2)}
              for k, r in per.sort_values("size", ascending=False).iterrows()]
    return {"icc": icc,
            "sd_semitone": {"median": float(per["sd_semitone"].median()),
                            "p75": float(per["sd_semitone"].quantile(0.75)),
                            "p90": float(per["sd_semitone"].quantile(0.90))},
            "range_semitone_median": float(per["range_semitone"].median()),
            "n_songs": int(len(per)), "n_obs": int(len(sub)), "min_sessions": min_sessions,
            "detail": detail}


def profile(studio, live_clean_df):
    """逐曲画像：录音室指标 + 现场场次/波动（有就带）。"""
    st = studio.dropna(subset=["low_hz"]).copy()
    live_by_song = (live_clean_df.groupby("song")
                    .agg(live_sessions=("low_hz", "size"),
                         live_sd=("low_hz", lambda s: float(np.std(s, ddof=1)) if len(s) > 1 else np.nan),
                         live_median=("low_hz", "median")))
    rows = []
    for song, g in st.groupby("song"):
        rec = {"song": song, "versions": int(len(g)),
               "low_hz": round(float(g["low_hz"].median()), 1),
               "span_octaves": (round(float(g["span_octaves"].median()), 2)
                                if g["span_octaves"].notna().any() else None),
               "intonation_cents": (round(float(g["intonation_cents"].median()), 1)
                                    if g["intonation_cents"].notna().any() else None),
               "stability_cents": (round(float(g["stability_cents"].median()), 1)
                                   if g["stability_cents"].notna().any() else None),
               "vibrato_hz": (round(float(g["vibrato_hz"].median()), 2)
                              if g["vibrato_hz"].notna().any() else None),
               "hnr_db": (round(float(g["hnr_db"].median()), 1)
                          if g["hnr_db"].notna().any() else None)}
        if song in live_by_song.index:
            l = live_by_song.loc[song]
            rec["live_sessions"] = int(l["live_sessions"])
            rec["live_median_hz"] = round(float(l["live_median"]), 1)
            rec["live_sd_hz"] = (round(float(l["live_sd"]), 1) if np.isfinite(l["live_sd"]) else None)
        rows.append(rec)
    return rows


def main():
    df, raw = load()
    studio = df[df["layer"] == "studio_album"]
    precision = df[df["layer"] == "precision"]
    live, qc = live_clean(df)

    # B1 窗口：A4=440，B1 = 61.735Hz；±50 音分
    b1 = 61.735
    b1_lo, b1_hi = b1 * 2 ** (-50 / 1200), b1 * 2 ** (50 / 1200)
    lows = studio["low_hz"].dropna()

    claims = {
        "meta": {
            "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "source": {"file": str(SRC.relative_to(SITE)), "sha256": sha256(SRC),
                       "rows": int(len(df)), "songs": int(df["song"].replace("", np.nan).nunique())},
            "by_layer": {LAYER_LABEL.get(k, k): int(v) for k, v in df["layer"].value_counts().items()},
            "by_verify": {str(k): int(v) for k, v in df["verify"].value_counts().head(6).items()},
            "metric_note": "低音/高音单位 Hz；intonation_cents 与 stability_cents 越小越准越稳；vibrato 为颤音频率(Hz)与幅度(音分)；hnr_db 越高气息越干净",
        },
        "studio": {
            "n": int(len(studio)), "metrics": cohort_stats(studio),
            "b1": {"hz": b1, "window_hz": [round(b1_lo, 2), round(b1_hi, 2)],
                   "count": int(((lows >= b1_lo) & (lows <= b1_hi)).sum()),
                   "share": float(((lows >= b1_lo) & (lows <= b1_hi)).mean())},
            "below_c2": {"threshold_hz": 65.406, "count": int((lows < 65.406).sum())},
            "span_share_ge2": float((studio["span_octaves"] >= 2).mean()),
        },
        "precision": {"n": int(len(precision)), "metrics": cohort_stats(precision)},
        "live": {"n_clean": int(len(live)), "qc": qc, "metrics": cohort_stats(live),
                 "stability": stability(live)},
        "per_song": profile(studio, live),
    }
    out = OUT / "vocal_claims.json"
    out.write_text(json.dumps(claims, ensure_ascii=False, indent=2), encoding="utf-8")
    # dashboard/ 由 PowerShell 复制（venv 的 python 对那个目录没有写权限）
    (OUT / "vocal_claims.min.json").write_text(
        json.dumps(claims, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    s = claims["studio"]
    print(f"根源 {claims['meta']['source']['file']} | 行 {len(df)} | 曲 {claims['meta']['source']['songs']}")
    print(f"录音室 {s['n']} 首：B1±50¢ {s['b1']['count']} 首（{s['b1']['share']:.0%}）| "
          f"低于 C2 {s['below_c2']['count']} 首 | ≥2 八度 {s['span_share_ge2']:.0%}")
    for m in ("low_hz", "span_octaves", "intonation_cents", "stability_cents", "vibrato_hz", "hnr_db"):
        v = s["metrics"].get(m)
        if v:
            print(f"  {m:18} 中位 {v['median']:.2f} [{v['ci_lo']:.2f},{v['ci_hi']:.2f}] n={v['n']}")
    st = claims["live"]["stability"]
    if st["icc"]:
        print(f"现场清洗 {claims['live']['qc']['per_song_session']} 行 | 可比 {st['n_songs']} 首 | "
              f"ICC {st['icc']['icc']:.2f} [{st['icc']['ci_lo']:.2f},{st['icc']['ci_hi']:.2f}] | "
              f"跨场 SD 中位 {st['sd_semitone']['median']:.2f} 半音")


if __name__ == "__main__":
    main()
