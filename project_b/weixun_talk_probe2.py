# -*- coding: utf-8 -*-
"""微醺深圳 0926 talk 量化 v2：**先切片再转写**（避免整段 VAD 吞掉），并给对照组基线。

① 目标：视频 100–160s（覆盖 2:00±20s）的 talk；
② 基线：沉响 10-09 p21「talking2：点歌环节」前 60s（同一位说话人、近期、现场 talk）。
指标：语速（字/秒，仅计说话段）、>0.5s 停顿次数/总时长、F0 中位与 P10–P90、RMS 波动。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ANA = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")
WEIXUN = Path(r"E:\wx\私有工具\xhs_archive\按链接\68d79bfd000000000e026fff_王晰《微醺23点08分》0926深圳有故\video.mp4")
BASE = ANA / "全场_第二场_全量" / "p21.m4a"
TMP = ANA / "_jiu_tmp"
OUT = Path(r"E:\wx\论文素材_王晰作传\传播监测\微醺深圳0926_talk量化_20261017.json")


def clip_wav(src: Path, a: float, b: float, dst: Path, sr=16000):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-v", "error", "-ss", str(a), "-t", str(b - a), "-i", str(src),
                    "-ac", "1", "-ar", str(sr), str(dst)], check=False)
    import wave
    with wave.open(str(dst), "rb") as w:
        y = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
        return y, w.getframerate()


def metrics(y, sr, words, text):
    dur = (words[-1]["end"] - words[0]["start"]) if words else 0
    cps = round(len(text) / dur, 2) if dur > 0 else None
    gaps = [{"at": round(words[i]["start"], 2), "gap": round(words[i]["start"] - words[i - 1]["end"], 2)}
            for i in range(1, len(words)) if words[i]["start"] - words[i - 1]["end"] >= 0.5]
    fr, hop = int(0.04 * sr), int(0.02 * sr)
    f0s = []
    for i in range(0, max(1, len(y) - fr), hop):
        f = y[i:i + fr] - y[i:i + fr].mean()
        if np.sqrt((f ** 2).mean()) < 0.02:
            continue
        ac = np.correlate(f, f, mode="full")[len(f) - 1:]
        ac /= (ac[0] + 1e-12)
        lo, hi = int(sr / 400), int(sr / 70)
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.35:
            f0s.append(sr / k)
    rms = [float(np.sqrt((y[i:i + int(0.3 * sr)] ** 2).mean()))
           for i in range(0, max(1, len(y) - int(0.3 * sr)), int(0.1 * sr))]
    return {"chars": len(text), "speech_duration_s": round(dur, 2), "chars_per_s": cps,
            "pauses_ge_0_5s": len(gaps), "pause_total_s": round(sum(g["gap"] for g in gaps), 2),
            "pause_list": gaps,
            "f0_median_hz": round(float(np.median(f0s)), 1) if f0s else None,
            "f0_p10_p90": [round(float(np.percentile(f0s, 10)), 1),
                           round(float(np.percentile(f0s, 90)), 1)] if f0s else None,
            "rms_std_db": round(float(np.std(20 * np.log10(np.array(rms) + 1e-9))), 2) if rms else None}


def transcribe(wav: Path):
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(wav), language="zh", beam_size=5, vad_filter=True,
                           word_timestamps=True)
    rows, words = [], []
    for s in segs:
        rows.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
        for wd in (s.words or []):
            words.append({"w": wd.word, "start": round(wd.start, 2), "end": round(wd.end, 2)})
    return rows, words


def main() -> int:
    TMP.mkdir(parents=True, exist_ok=True)
    doc = {"asr_model": "faster-whisper small（本地 int8）；ASR 未人工校对"}

    # 目标：100–160s
    a, b = 100.0, 160.0
    y, sr = clip_wav(WEIXUN, a, b, TMP / "weixun_100_160.wav")
    rows, words = transcribe(TMP / "weixun_100_160.wav")
    text = "".join(r["text"] for r in rows)
    doc["target"] = {"source": str(WEIXUN), "window": [a, b], "segments": rows,
                     "words": words, "text": text, "metrics": metrics(y, sr, words, text)}

    # 基线：沉响 10-09 p21 前 60s
    if BASE.exists():
        y2, sr2 = clip_wav(BASE, 20, 80, TMP / "base_20_80.wav")
        rows2, words2 = transcribe(TMP / "base_20_80.wav")
        text2 = "".join(r["text"] for r in rows2)
        doc["baseline"] = {"source": str(BASE), "window": [20, 80], "segments": rows2,
                           "text": text2, "metrics": metrics(y2, sr2, words2, text2)}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    for k in ("target", "baseline"):
        if k not in doc:
            continue
        t = doc[k]
        print(f"== {k}｜{t['window']}｜{t['metrics']}")
        for s in t["segments"]:
            print(f"   {s['start']:5.1f}-{s['end']:5.1f} {s['text']}")
    print("[OK]", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
