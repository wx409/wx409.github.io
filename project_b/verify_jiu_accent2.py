# -*- coding: utf-8 -*-
"""《美酒加咖啡》加重验证（只测 10-09 p22，约 2.6 分钟，避免整场 ASR）。

步骤：ASR 定位「并没有醉」→ 该句 vs 前后句 的短时能量（dB）、音高（自相关中位）、音符时长。
只报差异，不评优劣；双人重叠时标「归属不可判定」。
"""
from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ANA = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")
SRC = ANA / "美酒加咖啡" / "沉响与长歌20261009_双人_BV1mWpe6PESm.m4a"
TMP = ANA / "_jiu_tmp" / "meijiu.wav"
OUT = Path(r"E:\wx\论文素材_王晰作传\传播监测\美酒加咖啡_加重验证_20261017.json")


def decode(src: Path, sr: int = 16000, start=None, dur=None) -> np.ndarray:
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-v", "error"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", str(src)]
    if dur is not None:
        cmd += ["-t", str(dur)]
    cmd += ["-ac", "1", "-ar", str(sr), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def rms_db(y, sr):
    w, h = int(0.3 * sr), int(0.1 * sr)
    d = [20 * np.log10(np.sqrt((y[i:i + w] ** 2).mean()) + 1e-12)
         for i in range(0, max(1, len(y) - w), h)]
    return round(float(np.median(d)), 2) if d else float("nan")


def f0_med(y, sr):
    vals = []
    fr, hop = int(0.04 * sr), int(0.02 * sr)
    for i in range(0, max(1, len(y) - fr), hop):
        f = y[i:i + fr] - y[i:i + fr].mean()
        if np.sqrt((f ** 2).mean()) < 0.02:
            continue
        ac = np.correlate(f, f, mode="full")[len(f) - 1:]
        ac /= (ac[0] + 1e-12)
        lo, hi = int(sr / 420), int(sr / 70)
        if hi >= len(ac):
            continue
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.35:
            vals.append(sr / k)
    return round(float(np.median(vals)), 1) if vals else None


def main() -> int:
    if not SRC.exists():
        print("[X] 缺素材", SRC)
        return 1
    TMP.parent.mkdir(parents=True, exist_ok=True)
    y = decode(SRC)
    with wave.open(str(TMP), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes((y * 32767).astype("<i2").tobytes())

    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(TMP), language="zh", beam_size=1, vad_filter=True)
    rows = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
    hits = [r for r in rows if "没有醉" in r["text"] or "并没有醉" in r["text"]]
    sr = 16000
    phrases = []
    for h in hits:
        a, b = h["start"], h["end"]
        cur = rms_db(y[int(a * sr):int(b * sr)], sr)
        prev = rms_db(y[int(max(0, a - (b - a)) * sr):int(a * sr)], sr)
        nxt = rms_db(y[int(b * sr):int(min(len(y) / sr, b + (b - a)) * sr)], sr)
        phrases.append({"text": h["text"], "start": a, "end": b,
                        "cur_db": cur, "prev_db": prev, "next_db": nxt,
                        "delta_vs_prev": round(cur - prev, 2),
                        "delta_vs_next": round(cur - nxt, 2),
                        "f0_median_hz": f0_med(y[int(a * sr):int(b * sr)], sr)})
    doc = {"source": str(SRC), "duration_s": round(len(y) / sr, 1),
           "asr_model": "faster-whisper small（本地 int8）",
           "caveat": "双人合唱段落；若两人同时发声，能量/音高为混合信号，个人归属不可判定",
           "segments": rows, "hits": hits, "phrases": phrases}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {OUT}｜时长 {doc['duration_s']}s｜句 {len(rows)}｜命中 {len(hits)}")
    for p in phrases:
        print(f"   {p['start']:.1f}-{p['end']:.1f}s｜{p['text'][:20]}｜"
              f"{p['cur_db']} dB（前 {p['prev_db']}／后 {p['next_db']}）｜Δ {p['delta_vs_prev']}｜F0 {p['f0_median_hz']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
