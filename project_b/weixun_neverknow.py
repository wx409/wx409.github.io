# -*- coding: utf-8 -*-
"""定位「never know」句并测其最高读数；同时输出全曲关键指标。"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ANA = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")
STATS = next((ANA / "wav_微醺深圳0926_分析").rglob("*_stats.json"))
F0CSV = next((ANA / "wav_微醺深圳0926_分析").rglob("*_f0.csv"))
WAV = ANA / "wav_微醺深圳0926" / "微醺23点08分" / "微醺深圳0926_68d79bfd.wav"
OUT = Path(r"E:\wx\论文素材_王晰作传\传播监测\微醺_neverknow_20261017.json")


def main() -> int:
    st = json.loads(STATS.read_text(encoding="utf-8"))
    df = pd.read_csv(F0CSV)
    print("stats keys:", [k for k in st.keys()][:14])
    print("low_stable", st.get("low_stable"), "| high_stable", st.get("high_stable"))
    print("span_octaves", st.get("span_octaves"), "| vibrato", st.get("vibrato_rate_hz_median"),
          st.get("vibrato_extent_cents_median"), "| stability", st.get("stability_cents_median"))

    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(WAV), language="en", beam_size=5, vad_filter=True,
                           word_timestamps=True)
    rows = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
    hits = [r for r in rows if "never" in r["text"].lower() or "know" in r["text"].lower()]
    print("英语命中:", hits[:6])

    # 该句最高音（从 f0.csv 取时间窗内最大稳定 midi）
    tcol = "time_s" if "time_s" in df.columns else df.columns[0]
    fcol = "f0_hz" if "f0_hz" in df.columns else df.columns[1]
    res = []
    for h in hits[:3]:
        seg = df[(df[tcol] >= h["start"]) & (df[tcol] <= h["end"])]
        seg = seg[(seg[fcol] > 60) & (seg[fcol] < 1200)]
        if len(seg):
            i = seg[fcol].idxmax()
            res.append({"text": h["text"], "start": h["start"], "end": h["end"],
                        "duration_s": round(h["end"] - h["start"], 2),
                        "max_hz": round(float(seg.loc[i, fcol]), 1),
                        "at_s": round(float(seg.loc[i, tcol]), 2),
                        "voiced_frames": int(len(seg))})
    doc = {"source": str(WAV), "stats": {k: st.get(k) for k in
           ("duration_s", "low_stable", "high_stable", "span_octaves", "note_count",
            "note_density_per_s", "stability_cents_median", "vibrato_rate_hz_median",
            "vibrato_extent_cents_median")},
           "asr_model": "faster-whisper small（本地 int8）；ASR 未人工校对",
           "segments": rows, "never_know": hits, "never_know_peak": res}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[OK]", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
