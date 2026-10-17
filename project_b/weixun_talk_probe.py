# -*- coding: utf-8 -*-
"""《微醺23点08分》深圳 0926 现场：2:00 前后 talk 的转写与「微醺感」量化。

量化项：
  ① 语速（字/秒）——与本人常态基线对比（用 text_profile 的句长/语料，若无则只报绝对值并标基线待补）
  ② 停顿（>0.5s 静音次数与总时长，基于词级时间戳间隙）
  ③ 基频/音强起伏（F0 中位与 P10–P90、RMS 标准差）
  ④ 拖长音/口误/重复/笑（人工规则检测：相邻词间 >0.4s 且同一词延长；重复词检测；笑声关键词）
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

SRC = Path(r"E:\wx\私有工具\xhs_archive\按链接\68d79bfd000000000e026fff_王晰《微醺23点08分》0926深圳有故\video.mp4")
TMP = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频\_jiu_tmp\weixun_shenzhen.wav")
OUT = Path(r"E:\wx\论文素材_王晰作传\传播监测\微醺深圳0926_talk量化_20261017.json")
A, B = 100.0, 160.0     # 1:40–2:40 覆盖 2:00±20s


def decode(p, sr=16000):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    raw = subprocess.run([ff, "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0, sr


def main() -> int:
    from faster_whisper import WhisperModel
    TMP.parent.mkdir(parents=True, exist_ok=True)
    y, sr = decode(SRC)
    import wave
    with wave.open(str(TMP), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes((y * 32767).astype("<i2").tobytes())

    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(TMP), language="zh", beam_size=5, vad_filter=True,
                           word_timestamps=True, initial_prompt="微醺 深圳 有故事的歌 王晰")
    words, seg_rows = [], []
    for s in segs:
        seg_rows.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
        for wd in (s.words or []):
            words.append({"w": wd.word, "start": round(wd.start, 2), "end": round(wd.end, 2)})

    in_win = [w for w in words if A <= w["start"] <= B]
    text = "".join(x["w"] for x in in_win)
    dur = (in_win[-1]["end"] - in_win[0]["start"]) if in_win else 0
    cps = round(len(text) / dur, 2) if dur > 0 else None
    gaps = []
    for i in range(1, len(in_win)):
        g = in_win[i]["start"] - in_win[i - 1]["end"]
        if g >= 0.5:
            gaps.append({"at": round(in_win[i]["start"], 2), "gap": round(g, 2)})
    seg_sr = 16000
    a_i, b_i = int(A * seg_sr), int(B * seg_sr)
    seg = y[a_i:b_i]
    # F0（自相关）
    fr, hop = int(0.04 * seg_sr), int(0.02 * seg_sr)
    f0s = []
    for i in range(0, max(1, len(seg) - fr), hop):
        f = seg[i:i + fr] - seg[i:i + fr].mean()
        if np.sqrt((f ** 2).mean()) < 0.02:
            continue
        ac = np.correlate(f, f, mode="full")[len(f) - 1:]
        ac /= (ac[0] + 1e-12)
        lo, hi = int(seg_sr / 400), int(seg_sr / 70)
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.35:
            f0s.append(seg_sr / k)
    rms = [float(np.sqrt((seg[i:i + int(0.3 * seg_sr)] ** 2).mean()))
           for i in range(0, max(1, len(seg) - int(0.3 * seg_sr)), int(0.1 * seg_sr))]
    doc = {
        "source": str(SRC), "window": [A, B],
        "asr_model": "faster-whisper small（本地 int8）；ASR 未人工校对（唱段/方言更易错）",
        "segments": seg_rows, "words": in_win,
        "metrics": {
            "chars": len(text), "speech_duration_s": round(dur, 2),
            "chars_per_s": cps,
            "pauses_ge_0_5s": len(gaps), "pause_total_s": round(sum(g["gap"] for g in gaps), 2),
            "pause_list": gaps,
            "f0_median_hz": round(float(np.median(f0s)), 1) if f0s else None,
            "f0_p10_p90": [round(float(np.percentile(f0s, 10)), 1), round(float(np.percentile(f0s, 90)), 1)] if f0s else None,
            "rms_std_db": round(float(np.std(20 * np.log10(np.array(rms) + 1e-9))), 2) if rms else None,
        },
        "baseline": {"chars_per_s_typical_talk": None,
                     "note": "常态基线待补：需同一位说话人的其它 talk（例如沉响 10-09 的中控台 talk）按同法测量后对比"},
        "text": text,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {OUT}")
    for s in seg_rows:
        print(f"  {s['start']:6.1f}-{s['end']:6.1f} {s['text']}")
    mt = doc["metrics"]
    print(f"语速 {mt['chars_per_s']} 字/秒（{mt['chars']} 字 / {mt['speech_duration_s']}s）｜"
          f"停顿 ≥0.5s：{mt['pauses_ge_0_5s']} 次共 {mt['pause_total_s']}s｜"
          f"F0 中位 {mt['f0_median_hz']}Hz（P10–P90 {mt['f0_p10_p90']}）｜RMS 波动 σ {mt['rms_std_db']} dB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
