# -*- coding: utf-8 -*-
"""微醺：高音可疑点复核（A#5 951.7Hz）+ 定位 never know（中文 ASR 回退）。"""
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ANA = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")
ST = next((ANA / "wav_微醺深圳0926_分析").rglob("*_stats.json"))
F0 = next((ANA / "wav_微醺深圳0926_分析").rglob("*_f0.csv"))
WAV = ANA / "wav_微醺深圳0926" / "微醺23点08分" / "微醺深圳0926_68d79bfd.wav"
OUT = Path(r"E:\wx\论文素材_王晰作传\传播监测\微醺_neverknow_20261017.json")


def decode(p, sr=22050):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    raw = subprocess.run([ff, "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0, sr


def harm(mix, sr, t, f0):
    a = max(0, int((t - 0.05) * sr))
    seg = mix[a:a + int(0.4 * sr)]
    if len(seg) < 1024:
        return {}
    sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    fr = np.fft.rfftfreq(len(seg), 1 / sr)
    base = float(np.median(sp) + 1e-12)

    def band(f):
        i = int(np.argmin(np.abs(fr - f)))
        w = max(1, int(0.03 * f / (fr[1] - fr[0])))
        return float(sp[max(0, i - w):i + w + 1].max()) / base
    return {"f0": round(band(f0), 1), "2f0": round(band(2 * f0), 1), "3f0": round(band(3 * f0), 1)}


def main() -> int:
    st = json.loads(ST.read_text(encoding="utf-8"))
    df = pd.read_csv(F0)
    tcol, fcol = ("time_s", "f0_hz") if "time_s" in df.columns else (df.columns[0], df.columns[1])
    # 所有 ≥C5 的帧
    hi = df[(df[fcol] >= 523) & (df[fcol] < 1200)]
    print(f"≥C5 帧数 {len(hi)}｜时长合计 {len(hi)*0.0232:.2f}s（近似）")
    top = df.loc[df[fcol].idxmax()]
    print("最高帧", round(float(top[fcol]), 1), "Hz @", round(float(top[tcol]), 2), "s")
    mix, sr = decode(WAV)
    h = harm(mix, sr, float(top[tcol]), float(top[fcol]))
    print("该点原始混音谐波比（相对底噪）:", h, "→", "2f0 有峰=真音" if h.get("2f0", 0) > 3 else "2f0 弱=可能非本人/次谐波错误")

    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(WAV), language="zh", beam_size=5, vad_filter=True, word_timestamps=True)
    rows = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segs]
    keys = [r for r in rows if any(k in r["text"].lower() for k in ("never", "know", "微醺", "vever", "nover"))]
    print("关键词命中:", keys[:5])
    print("末 5 段:", rows[-5:])

    doc = json.loads(OUT.read_text(encoding="utf-8"))
    doc["high_note_check"] = {"frames_ge_C5": int(len(hi)),
                              "max_hz": round(float(top[fcol]), 1),
                              "max_at_s": round(float(top[tcol]), 2),
                              "harmonic_ratio": h,
                              "verdict": ("2f0 有峰 → 可能是真音（但仍需人耳/分离复核）"
                                          if h.get("2f0", 0) > 3 else
                                          "2f0 弱 → 疑非本人或次谐波错误，应按三级制度剔除")}
    doc["segments_zh"] = rows
    doc["keyword_hits"] = keys
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[OK]", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
