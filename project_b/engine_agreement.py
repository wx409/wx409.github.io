#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双引擎误差分层：自研 YIN vs Praat(Parselmouth) 在真实素材上的分歧率。

为什么做：合成基准只说明"理想信号上错多少"，真实素材的误差没有估计。
两引擎看同一段音频，分歧率就是真实误差的直接代理（不是真值，是"两个独立实现
在同一输入上不一致的频率"）。

分层：录音室人声轨（分离后）/ 现场混音（未分离）。两者不可合并报告。
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import parselmouth
import soundfile as sf

sys.stdout.reconfigure(encoding='utf-8')
D = Path(r'E:\wx\论文素材_王晰作传\音域分析')
OUT = Path(r'D:\wx409.github.io\data\derived\engine_agreement.json')

SR = 22050
FRAME, HOP = 2048, 512
FMIN, FMAX, THRESH = 55.0, 1100.0, 0.15
WIN_S = 6.0
N_PER_STRATUM = 10
TOL = 50.0  # 音分


def yin_frame(x, sr, fmin, fmax, thresh):
    tau_min, tau_max = int(sr / fmax), min(int(sr / fmin), len(x) // 2)
    if tau_max <= tau_min + 2:
        return 0.0
    d = np.zeros(tau_max + 1)
    for tau in range(1, tau_max + 1):
        diff = x[:len(x) - tau] - x[tau:]
        d[tau] = np.dot(diff, diff)
    cmnd = np.ones(tau_max + 1)
    run = 0.0
    for tau in range(1, tau_max + 1):
        run += d[tau]
        cmnd[tau] = d[tau] * tau / run if run > 0 else 1.0
    tau = None
    for t in range(tau_min, tau_max):
        if cmnd[t] < thresh:
            while t + 1 < tau_max and cmnd[t + 1] < cmnd[t]:
                t += 1
            tau = t
            break
    if tau is None:
        tau = int(np.argmin(cmnd[tau_min:tau_max])) + tau_min
    if tau <= 0 or tau >= tau_max:
        return 0.0
    a, b, c = cmnd[tau - 1], cmnd[tau], cmnd[tau + 1]
    den = a - 2 * b + c
    shift = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
    return sr / (tau + shift) if (tau + shift) > 0 else 0.0


def analyse(path: Path, start: float):
    x, sr = sf.read(str(path), dtype='float32', always_2d=True)
    mono = x.mean(axis=1)
    if sr != SR:
        idx = np.linspace(0, len(mono) - 1, int(len(mono) * SR / sr))
        mono = np.interp(idx, np.arange(len(mono)), mono).astype('float32')
        sr = SR
    a = int(start * sr)
    seg = mono[a:a + int(WIN_S * sr)]
    if len(seg) < int(WIN_S * sr * 0.8):
        return None

    # 引擎 A：自研 YIN
    win = np.hanning(FRAME)
    ours = {}
    for i in range(0, len(seg) - FRAME, HOP):
        fr = seg[i:i+FRAME] * win
        if np.sqrt(np.mean(fr ** 2)) < 0.005:
            continue
        f = yin_frame(fr, sr, FMIN, FMAX, THRESH)
        if f > 0:
            ours[round(i / sr, 3)] = f

    # 引擎 B：Praat（自相关法）
    snd = parselmouth.Sound(seg.astype('float64'), sampling_frequency=sr)
    pitch = snd.to_pitch(time_step=HOP / sr, pitch_floor=FMIN, pitch_ceiling=FMAX)
    praat = {}
    n = pitch.get_number_of_frames()
    for i in range(1, n + 1):
        t = pitch.get_time_from_frame_number(i)
        v = pitch.get_value_at_time(i * HOP / sr)
        if v and v == v and v > 0:
            praat[round(i * HOP / sr, 3)] = v

    # 对齐比较
    pairs = []
    for t, f in ours.items():
        g = praat.get(t)
        if g:
            pairs.append((f, g))
    if len(pairs) < 40:
        return None
    o = np.array([p[0] for p in pairs])
    p = np.array([p[1] for p in pairs])
    cents = 1200 * np.log2(o / p)
    ratio = o / p
    near = np.abs(cents) <= TOL
    octave = (np.abs(ratio - 2) < .06) | (np.abs(ratio - 0.5) < .06) | \
             (np.abs(ratio - 4) < .1) | (np.abs(ratio - .25) < .05)
    return {
        "frames": int(len(pairs)),
        "agree_pct": round(float(near.mean()) * 100, 1),
        "octave_pct": round(float(octave.mean()) * 100, 1),
        "median_cents": round(float(np.median(cents)), 1),
        "p90_abs_cents": round(float(np.percentile(np.abs(cents), 90)), 1),
    }


def main() -> None:
    random.seed(20261025)
    studio = [p for p in D.glob('分离_专辑/**/vocals.wav')
              if p.parent.parent.name and p.parent.parent.name != '分离_专辑']
    stage = [p for p in D.glob('场次音频/**/*.wav')
             if '分离' not in str(p) and 'input_ascii' not in p.name and p.stat().st_size > 200_000]
    random.shuffle(studio)
    random.shuffle(stage)
    rows = []
    for stratum, files in (('录音室人声轨', studio[:N_PER_STRATUM]),
                           ('现场混音', stage[:N_PER_STRATUM])):
        for f in files:
            try:
                r = analyse(f, start=4.0)
            except Exception as e:
                print('skip', f.name, type(e).__name__)
                continue
            if r:
                r.update({"stratum": stratum, "file": (f.parent.parent.name + "/" if stratum == "录音室人声轨" else "") + f.name})
                rows.append(r)
                print(f'{stratum}｜{f.name[:34]:34s} 帧 {r["frames"]:4d}｜一致 {r["agree_pct"]:5.1f}%'
                      f'｜倍频 {r["octave_pct"]:4.1f}%｜中位偏 {r["median_cents"]:+.1f}c')
    summary = {}
    for stratum in ('录音室人声轨', '现场混音'):
        sub = [r for r in rows if r['stratum'] == stratum]
        if sub:
            summary[stratum] = {
                "files": len(sub),
                "agree_pct_median": round(float(np.median([r['agree_pct'] for r in sub])), 1),
                "octave_pct_median": round(float(np.median([r['octave_pct'] for r in sub])), 1),
                "median_cents_median": round(float(np.median([r['median_cents'] for r in sub])), 1),
            }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": "engine_agreement/v1", "engine_a": "自研 YIN",
                               "engine_b": "Praat autocorrelation (Parselmouth)",
                               "window_s": WIN_S, "tol_cents": TOL,
                               "summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
                   encoding='utf-8')
    print('\n汇总:', json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
