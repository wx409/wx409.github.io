#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""音高校准集：用"已知答案"的合成信号，量出我们的 F0 管线在哪类素材上错、错多少。

为什么必须做：
  站内所有低音结论都建立在 YIN/CREPE 读数上，但从未系统回答"错了会错多少"。
  没有校准，"65.2–65.4Hz 差 5 音分"就只是读数差，不能写成"实际波动 5 音分"。

方法：
  1. 合成谐波复音（f0 已知），逐条件注入干扰：
     clean｜白噪 SNR 10dB｜叠加 60Hz 低音伴奏｜缺失基频（去掉 H1）
  2. 用与站内同参数的 YIN（frame 2048 / hop 512 / fmin 55 / fmax 1100 / sr 22050）逐帧估计
  3. 报三类错误：中位绝对误差、±50 音分内比例、倍频/次谐波锁错比例

局限（必须随结果写）：
  - 合成信号不等于真实演唱（无颤音、无辅音、无元音变化）；
  - 只校准"音高提取"这一环，不覆盖人声归属与分离影响。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SR = 22050
FRAME = 2048
HOP = 512
FMIN, FMAX = 55.0, 1100.0
THRESH = 0.15


def yin_frame(x: np.ndarray, sr: int, fmin: float, fmax: float, thresh: float) -> float:
    """单帧 YIN：差函数 → 累积均值归一化 → 阈值 → 抛物插值。返回 Hz 或 0。"""
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
    denom = (a - 2 * b + c)
    shift = 0.5 * (a - c) / denom if abs(denom) > 1e-12 else 0.0
    period = tau + shift
    return sr / period if period > 0 else 0.0


def synth(f0: float, secs: float, sr: int, drop_fundamental=False, noise_db=None, bass_hz=None):
    t = np.arange(int(secs * sr)) / sr
    sig = np.zeros_like(t)
    for k in range(1, 12):
        if drop_fundamental and k == 1:
            continue
        sig += (1.0 / k) * np.sin(2 * np.pi * f0 * k * t + 0.3 * k)
    sig /= np.max(np.abs(sig)) + 1e-9
    if bass_hz:
        sig += 0.5 * np.sin(2 * np.pi * bass_hz * t)
    if noise_db is not None:
        p = np.mean(sig ** 2)
        n = np.random.default_rng(0).normal(0, np.sqrt(p / (10 ** (noise_db / 10))), len(sig))
        sig = sig + n
    return sig / (np.max(np.abs(sig)) + 1e-9) * 0.5


def estimate(sig: np.ndarray, sr: int):
    vals = []
    for i in range(0, len(sig) - FRAME, HOP):
        fr = sig[i:i+FRAME] * np.hanning(FRAME)
        if np.sqrt(np.mean(fr ** 2)) < 0.005:
            continue
        f = yin_frame(fr, sr, FMIN, FMAX, THRESH)
        if f > 0:
            vals.append(f)
    return np.array(vals)


def classify(truth, est):
    if not len(est):
        return 'no-frames', np.nan, 0.0, 0.0
    med = float(np.median(est))
    cents = 1200 * np.log2(med / truth)
    ratio = med / truth
    near = abs(cents) <= 50
    octave = any(abs(ratio - r) < 0.06 for r in (2, 4, 0.5, 0.25))
    sub = any(abs(ratio - r) < 0.04 for r in (1/3, 1/2, 3/2))
    label = 'ok' if near else ('octave' if octave else ('subharmonic' if sub else 'other'))
    within = float(np.mean(np.abs(1200 * np.log2(est / truth)) <= 50))
    return label, abs(cents), within, med


F0S = [58.27, 61.74, 65.41, 73.42]
COND = [
    ('clean', {}),
    ('noise10dB', {'noise_db': 10}),
    ('+bass60Hz', {'bass_hz': 60.0}),
    ('missing-fund', {'drop_fundamental': True}),
    ('missing+bass', {'drop_fundamental': True, 'bass_hz': 60.0}),
]

rows = []
truth_all, est_all = [], []
for f0 in F0S:
    for name, kw in COND:
        sig = synth(f0, 2.0, SR, **kw)
        est = estimate(sig, SR)
        label, err, within, med = classify(f0, est)
        rows.append({'f0': f0, 'cond': name, 'label': label, 'median': round(med, 2),
                     'err_cents': None if np.isnan(err) else round(err, 1),
                     'within50': round(within, 2), 'frames': int(len(est))})
        if label == 'ok':
            truth_all.append(f0); est_all.append(med)

print(f"{'f0':>7} {'条件':>14} {'中位':>8} {'误差(c)':>8} {'±50c内':>7} {'判定':>12}")
for r in rows:
    print(f"{r['f0']:>7.2f} {r['cond']:>14} {r['median']:>8.2f} {str(r['err_cents']):>8} "
          f"{r['within50']:>7.2f} {r['label']:>12}")

ok = [r for r in rows if r['label'] == 'ok']
print(f"\n总计 {len(rows)} 条件×音高：判对 {len(ok)}｜"
      f"倍频/次谐波错 {sum(1 for r in rows if r['label'] in ('octave','subharmonic'))}｜"
      f"其他错 {sum(1 for r in rows if r['label'] == 'other')}｜无帧 {sum(1 for r in rows if r['label']=='no-frames')}")
if ok:
    errs = [r['err_cents'] for r in ok]
    print(f"判对条件下：中位绝对误差 {np.median(errs):.1f} 音分｜最大 {max(errs):.1f} 音分")

Path(r'D:\wx409.github.io\data\calibration_pitch.json').write_text(
    json.dumps({'schema': 'calibration/pitch-v1', 'sr': SR, 'frame': FRAME, 'hop': HOP,
                'fmin': FMIN, 'fmax': FMAX, 'thresh': THRESH, 'rows': rows,
                'note': '合成谐波复音校准；不含颤音/辅音/元音变化，只覆盖音高提取这一环'},
               ensure_ascii=False, indent=1), encoding='utf-8')
print('-> data/calibration_pitch.json')
