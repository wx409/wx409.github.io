# -*- coding: utf-8 -*-
"""把统计结果变成页面能吃的 JSON + 一张独立预览页。

不改动 index.html：新页面 dashboard/analysis-v2.html，数据 dashboard/data/stats-v2.json。
确认无误后再决定是否接进主大屏。
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SITE = HERE.parent
DATA_OUT = OUT
DATA_OUT.mkdir(parents=True, exist_ok=True)


def hist(values, bins=18):
    v = np.asarray([x for x in values if np.isfinite(x)], dtype=float)
    cnt, edges = np.histogram(v, bins=bins)
    return {"edges": [round(float(e), 1) for e in edges], "counts": [int(c) for c in cnt]}


def main():
    curve = json.loads((OUT / "curve.json").read_text(encoding="utf-8"))
    sens = json.loads((OUT / "sensitivity.json").read_text(encoding="utf-8"))
    voc = json.loads((OUT / "vocal_stats.json").read_text(encoding="utf-8"))
    live_stats = json.loads((OUT / "vocal_live.json").read_text(encoding="utf-8"))
    raw_manifest = json.loads((OUT / "raw_panel.manifest.json").read_text(encoding="utf-8"))
    v = pd.read_parquet(OUT / "vocal.parquet")
    live = v[v["layer"] == "tour_live"].copy()
    live["song"] = live["song"].astype("string").fillna("").str.strip()
    quality = {
        "per_song_session": int(((live["song"] != "") & (~live["song"].str.contains("全场|整场|合集"))).sum()),
        "aggregate": int(live["song"].str.contains("全场|整场|合集").sum()),
        "unnamed": int((live["song"] == "").sum()),
        "total": int(len(live)),
    }
    studio = v[(v["layer"] == "studio_album")].dropna(subset=["low_hz"])

    bundle = {
        "generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "source": {"raw": raw_manifest["src_file"], "sha256": raw_manifest["sha256"],
                   "rows": raw_manifest["rows"], "dates": raw_manifest["dates"],
                   "from": raw_manifest["date_min"], "to": raw_manifest["date_max"]},
        "tour": {
            "n_events": curve["n_events"], "curve": curve["curve"], "week1_pct": curve["week1_pct"],
            "heterogeneity": curve.get("heterogeneity"),
            "sensitivity": sens["cells"],
        },
        "vocal": {
            "studio": voc["studio_low_hz"], "span": voc["studio_span_octaves"],
            "span_share_ge2": voc["studio_span_share_ge2"],
            "hist_low": hist(studio["low_hz"]),
            "n_studio": voc["n_studio"], "live_quality": quality,
            "live_stability": {
                "icc": live_stats["icc"], "icc_ci": live_stats["icc_ci"],
                "sd": live_stats["sd_semitone"], "range": live_stats["range_semitone"],
                "n_songs": live_stats["n_songs_used"], "n_sessions": live_stats["n_sessions"],
                "qc": live_stats["qc"],
                "detail": live_stats["detail"],
            },
            "uncertainty": voc["measurement_uncertainty"],
        },
    }
    (DATA_OUT / "stats-v2.json").write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")),
                                            encoding="utf-8")
    print("写出:", DATA_OUT / "stats-v2.json", f"{len(json.dumps(bundle))//1024} KB")


if __name__ == "__main__":
    main()

