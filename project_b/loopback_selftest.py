#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""环回链路自检：放一段 60Hz+1200Hz 测试音，边放边从立体声混音录，测两频段是否都在。

用途：判断「立体声混音」是否被音效处理（Nahimic 等）高通滤掉低频，或实际串进了麦克风。
用法：python -X utf8 project_b/loopback_selftest.py [--seconds 10]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

TMP = Path(r'E:\wx\论文素材_王晰作传\专辑\环回录制')
TONE = TMP / "_selftest_tone.wav"
REC = TMP / "_selftest_rec.wav"
DEV = "立体声混音 (Realtek(R) Audio)"


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def make_tone(sr=48000, secs=8.0):
    t = np.arange(int(sr * secs)) / sr
    sig = 0.20 * np.sin(2 * np.pi * 60 * t) + 0.20 * np.sin(2 * np.pi * 1200 * t)
    # 淡入淡出
    n = int(0.05 * sr)
    env = np.ones_like(sig)
    env[:n] = np.linspace(0, 1, n)
    env[-n:] = np.linspace(1, 0, n)
    sig *= env
    st = np.stack([sig, sig], axis=1)
    pcm = (np.clip(st, -1, 1) * 32767).astype('<i2')
    TMP.mkdir(parents=True, exist_ok=True)
    with wave.open(str(TONE), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=10)
    ap.add_argument("--device", default=DEV)
    args = ap.parse_args()

    make_tone()
    rec_cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
               "-f", "dshow", "-i", f"audio={args.device}",
               "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le",
               "-t", str(args.seconds), str(REC)]
    p = subprocess.Popen(rec_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    time.sleep(1.5)
    import winsound
    winsound.PlaySound(str(TONE), winsound.SND_FILENAME | winsound.SND_ASYNC)
    time.sleep(max(3, args.seconds - 2))
    p.terminate()
    p.wait(timeout=10)

    import soundfile as sf
    x, sr = sf.read(str(REC), dtype='float32', always_2d=True)
    m = x.mean(axis=1)
    n = 8192
    win = np.hanning(n)
    best = 0.0
    sig_spec = None
    for i in range(0, len(m) - n, n // 2):
        seg = m[i:i+n] * win
        r = float(np.sqrt(np.mean(seg ** 2)))
        if r > best:
            best, sig_spec = r, np.abs(np.fft.rfft(seg)) ** 2
    if sig_spec is None:
        print("[ERR] 没录到声音")
        return
    f = np.fft.rfftfreq(n, 1 / sr)
    def peak_near(freq, tol=15):
        band = (f > freq - tol) & (f < freq + tol)
        return float(sig_spec[band].max()), float(f[band][np.argmax(sig_spec[band])])
    a60, f60 = peak_near(60)
    a1200, f1200 = peak_near(1200)
    print(f"[SELFTEST] 录制 {len(m)/sr:.1f}s｜峰值 RMS {20*np.log10(best+1e-12):.1f} dBFS")
    print(f"  60Hz   峰值 {a60:.3e} @ {f60:.1f}Hz")
    print(f"  1200Hz 峰值 {a1200:.3e} @ {f1200:.1f}Hz")
    if a60 <= 0 or a1200 <= 0:
        print("  → 判定：某一路缺失")
    else:
        ratio_db = 10 * np.log10(a60 / a1200)
        print(f"  低频/高频 幅度比（相对，应为 0 dB 左右）：{ratio_db:+.1f} dB")
        if ratio_db < -12:
            print("  → 判定：低频被高通滤掉（音效处理或设备设置）")
        elif ratio_db > 12:
            print("  → 判定：高频衰减（少见）")
        else:
            print("  → 判定：链路正常，可做低频测量")


if __name__ == "__main__":
    main()
