#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""音高校准（第一层：合成谐波复音试运行）。

定位（别叫"校准完成"）：
  这是**首轮合成基准测试**，回答"在最理想信号上，我们的音高管线偏多少、会不会锁错"。
  它不回答"真实演唱素材上的误差是多少"——那需要第二层：真实录音参考标注集。

设计（按评审意见补齐）：
  - 每个「音高×条件」跑 3 个随机种子 × 2 种时长（1.5s / 3.0s），避免单例偶然；
  - 判对容差显式定义为 |误差| ≤ 50 音分；倍频/次谐波单独计类，不并入"判对"；
  - 负对照：纯 60Hz 贝斯正弦、静音、纯噪声——用于说明"管线无法区分人声与乐器，
    归属必须另证"，而不是把它们算成错误率；
  - 结果文件带参数、代码 SHA256、运行日期，便于复核。

用法：python -X utf8 project_b/calibrate_pitch.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

SR = 22050
FRAME = 2048
HOP = 512
FMIN, FMAX = 55.0, 1100.0
THRESH = 0.15
TOL_CENTS = 50.0          # 判对容差：|误差| ≤ 50 音分
SEEDS = (0, 1, 2)
DURS = (1.5, 3.0)


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
    den = (a - 2 * b + c)
    shift = 0.5 * (a - c) / den if abs(den) > 1e-12 else 0.0
    period = tau + shift
    return sr / period if period > 0 else 0.0


def synth(f0, secs, sr, seed=0, drop_fundamental=False, noise_db=None, bass_hz=None):
    rng = np.random.default_rng(seed)
    t = np.arange(int(secs * sr)) / sr
    sig = np.zeros_like(t)
    for k in range(1, 12):
        if drop_fundamental and k == 1:
            continue
        sig += (1.0 / k) * np.sin(2 * np.pi * f0 * k * t + 0.3 * k + rng.uniform(0, 0.2))
    sig /= np.max(np.abs(sig)) + 1e-9
    if bass_hz:
        sig += 0.5 * np.sin(2 * np.pi * bass_hz * t)
    if noise_db is not None:
        p = np.mean(sig ** 2)
        sig = sig + rng.normal(0, np.sqrt(p / (10 ** (noise_db / 10))), len(sig))
    return sig / (np.max(np.abs(sig)) + 1e-9) * 0.5


def estimate(sig, sr):
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
        return 'no-frames', np.nan, 0.0
    med = float(np.median(est))
    cents = 1200 * np.log2(med / truth)
    ratio = med / truth
    if abs(cents) <= TOL_CENTS:
        label = 'ok'
    elif any(abs(ratio - r) < 0.06 for r in (2, 4, 0.5, 0.25)):
        label = 'octave'
    elif any(abs(ratio - r) < 0.05 for r in (1/3, 1/2, 3/2)):
        label = 'subharmonic'
    else:
        label = 'other'
    within = float(np.mean(np.abs(1200 * np.log2(est / truth)) <= TOL_CENTS))
    return label, float(abs(cents)), within


F0S = [58.27, 61.74, 65.41, 73.42]
COND = [
    ('clean', {}),
    ('noise10dB', {'noise_db': 10}),
    ('+bass60Hz', {'bass_hz': 60.0}),
    ('missing-fund', {'drop_fundamental': True}),
    ('missing+bass', {'drop_fundamental': True, 'bass_hz': 60.0}),
]

rows = []
for f0 in F0S:
    for cname, kw in COND:
        for seed in SEEDS:
            for dur in DURS:
                sig = synth(f0, dur, SR, seed=seed, **kw)
                est = estimate(sig, SR)
                label, err, within = classify(f0, est)
                rows.append({'f0': f0, 'cond': cname, 'seed': seed, 'dur': dur,
                             'median': None if np.isnan(err) else round(est.mean(), 2),
                             'err_cents': None if np.isnan(err) else round(err, 1),
                             'within_tol': round(within, 2), 'label': label,
                             'frames': int(len(est))})

# 负对照：纯贝斯 / 静音 / 纯噪声
neg = []
for name, sig in (
        ('pure-60Hz-bass', 0.5 * np.sin(2 * np.pi * 60.0 * np.arange(int(2 * SR)) / SR)),
        ('silence', np.zeros(int(2 * SR))),
        ('white-noise', np.random.default_rng(0).normal(0, 0.05, int(2 * SR))),
):
    est = estimate(sig, SR)
    neg.append({'case': name, 'frames': int(len(est)),
                'median': None if not len(est) else round(float(np.median(est)), 2)})

ok = [r for r in rows if r['label'] == 'ok']
errs = [r['err_cents'] for r in ok]
summary = {
    'runs': len(rows),
    'ok': len(ok),
    'octave': sum(1 for r in rows if r['label'] == 'octave'),
    'subharmonic': sum(1 for r in rows if r['label'] == 'subharmonic'),
    'other': sum(1 for r in rows if r['label'] == 'other'),
    'no_frames': sum(1 for r in rows if r['label'] == 'no-frames'),
    'err_median': round(float(np.median(errs)), 1),
    'err_max': round(float(np.max(errs)), 1),
    'err_p90': round(float(np.percentile(errs, 90)), 1),
    'tol_cents': TOL_CENTS,
}

code = Path(__file__).read_bytes()
doc = {
    'schema': 'calibration/pitch-v2',
    'status': '第一层·合成基准试运行（不是"校准完成"）',
    'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
    'code': {'file': 'project_b/calibrate_pitch.py',
             'sha256': hashlib.sha256(code).hexdigest()[:16],
             'numpy': np.__version__},
    'params': {'sr': SR, 'frame': FRAME, 'hop': HOP, 'fmin': FMIN, 'fmax': FMAX,
               'thresh': THRESH, 'tol_cents': TOL_CENTS, 'seeds': list(SEEDS), 'durations': list(DURS)},
    'not_covered': ['颤音', '元音变化', '起音/尾音', '气声', '多人重叠', 'demucs 分离伪影',
                    '真实录音的编码与扩声'],
    'summary': summary,
    'negative_controls': neg,
    'rows': rows,
}
Path(r'D:\wx409.github.io\data\calibration_pitch.json').write_text(
    json.dumps(doc, ensure_ascii=False, indent=1), encoding='utf-8')

print(f"运行 {summary['runs']} 次｜判对 {summary['ok']}｜倍频 {summary['octave']}｜"
      f"次谐波 {summary['subharmonic']}｜其他 {summary['other']}｜无帧 {summary['no_frames']}")
print(f"判对样本绝对误差：中位 {summary['err_median']} 音分｜P90 {summary['err_p90']}｜最大 {summary['err_max']}"
      f"（容差 ±{TOL_CENTS} 音分）")
for n in neg:
    print(f"负对照 {n['case']}: 帧 {n['frames']}｜中位 {n['median']}")
print('-> data/calibration_pitch.json')
