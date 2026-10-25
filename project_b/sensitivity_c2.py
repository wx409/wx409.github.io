#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C2 读数稳健性：冻结素材与时间窗，在参数网格上统一跑，不允许挑参数。

规则（跑之前冻结）：
  - 素材与目标窗：乐华 65–72s、北京 143–148.5s、录音室参考段（同一首歌）
  - 网格：frame ∈ {1024,2048,4096}｜fmin ∈ {50,55}｜thresh ∈ {0.10,0.15,0.20}
          hop 固定 512、fmax 固定 1100、sr 22050
  - 汇总：取窗内逐帧中位读数；与 C2=65.41Hz 比较
  - 判定：|偏差| ≤ 50 音分 → 仍归 C2；出现 2×/0.5× 锁错 → 标 octave/sub
  - 不允许事后删参数：全部组合都要出现在结果里
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 22050
FRAMES = [1024, 2048, 4096]
FMINS = [50.0, 55.0]
THRESHS = [0.10, 0.15, 0.20]
HOP = 512
FMAX = 1100.0
C2 = 65.41

MATS = [
    ('乐华 2024-08-24', r'E:\wx\论文素材_王晰作传\专辑\工作室现场\多听有益\乐华20240824_多听有益.wav', 65.0, 72.0),
    ('北京 2023-11-13', r'E:\wx\论文素材_王晰作传\专辑\工作室现场\多听有益\北京20231113_多听有益.wav', 143.0, 148.5),
    ('录音室 320k（参考）', r'E:\wx\论文素材_王晰作传\音域分析\专辑音频\X自选集\多听有益.mp3', 79.0, 84.0),
]


def yin_frame(x, sr, fmin, fmax, thresh):
    tau_min = int(sr / fmax)
    tau_max = min(int(sr / fmin), len(x) // 2)
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


def run(path, t0, t1, frame, fmin, thresh):
    x, sr = sf.read(path, dtype='float32', always_2d=True)
    mono = x.mean(axis=1)
    if sr != SR:
        idx = np.linspace(0, len(mono) - 1, int(len(mono) * SR / sr))
        mono = np.interp(idx, np.arange(len(mono)), mono).astype('float32')
        sr = SR
    seg = mono[int(t0*sr):int(t1*sr)]
    win = np.hanning(frame)
    vals = []
    for i in range(0, len(seg) - frame, HOP):
        fr = seg[i:i+frame] * win
        if np.sqrt(np.mean(fr ** 2)) < 0.005:
            continue
        f = yin_frame(fr, sr, fmin, FMAX, thresh)
        if f > 0:
            vals.append(f)
    if not vals:
        return None, 0
    return float(np.median(vals)), len(vals)


out = []
for name, path, t0, t1 in MATS:
    if not Path(path).exists():
        print('MISS', name); continue
    meds = []
    for frame in FRAMES:
        for fmin in FMINS:
            for th in THRESHS:
                med, n = run(path, t0, t1, frame, fmin, th)
                if med is None:
                    out.append({'mat': name, 'frame': frame, 'fmin': fmin, 'thresh': th,
                                'median': None, 'cents': None, 'cls': 'no-frames'})
                    continue
                cents = 1200 * np.log2(med / C2)
                ratio = med / C2
                if abs(cents) <= 50:
                    cls = 'in-C2'
                elif any(abs(ratio - r) < 0.06 for r in (2, 4, 0.5, 0.25)):
                    cls = 'octave'
                elif any(abs(ratio - r) < 0.05 for r in (1/3, 1/2, 3/2)):
                    cls = 'subharmonic'
                else:
                    cls = 'shifted'
                meds.append(med)
                out.append({'mat': name, 'frame': frame, 'fmin': fmin, 'thresh': th,
                            'median': round(med, 2), 'cents': round(float(cents), 1), 'cls': cls})
    if meds:
        print(f'{name}: {len(meds)} 组｜范围 {min(meds):.1f}–{max(meds):.1f}Hz｜'
              f'中位 {np.median(meds):.2f}Hz｜全部归 C2: '
              f'{all(o["cls"]=="in-C2" for o in out if o["mat"]==name)}')

Path(r'D:\wx409.github.io\data\sensitivity_c2.json').write_text(
    json.dumps({'schema': 'sensitivity/c2-v1', 'target_hz': C2,
                'frozen': {'hop': HOP, 'fmax': FMAX, 'sr': SR,
                           'frames': FRAMES, 'fmins': FMINS, 'threshs': THRESHS},
                'materials': [m[0] for m in MATS], 'rows': out}, ensure_ascii=False, indent=1),
    encoding='utf-8')
print('-> data/sensitivity_c2.json｜共', len(out), '行')
