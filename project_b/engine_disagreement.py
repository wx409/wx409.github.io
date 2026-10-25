#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实素材的双引擎分歧诊断（探索性，不是"误差分层"，也不是真值估计）。

定位：
  自研 YIN 与 Praat(自相关) 看同一窗口，统计"两套独立实现给出不同答案的频率"。
  一致性衡量的是算法间稳定性，不是相对真值的准确率——两法都锁到同一个伴奏音时
  会"一致但共同错误"。

口径（冻结）：
  · 窗口：录音室取人声轨能量最高的 6s；现场取已登记低音时刻 ±3s（仅用于定位，不作真值）
  · 采样：固定时间点；fmin 55 / fmax 1100；hop 512；容差 ±50 音分
  · 分类：双方有声 / 仅 A / 仅 B / 八度类分歧 / 非八度分歧
  · 汇总：先算每段，再取各段中位数（不让长段支配）
  · 偏差：只报绝对偏差中位数与 P90，不报带符号值
  · 状态：exploratory / publishable=false
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
SITE = Path(r'D:\wx409.github.io')
OUT = SITE / 'data' / 'derived' / 'engine_disagreement.json'

SR, FRAME, HOP = 22050, 2048, 512
FMIN, FMAX, THRESH = 55.0, 1100.0, 0.15
WIN, TOL = 6.0, 50.0
N_PER = 20


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


def load_mono(path, start, dur):
    x, sr = sf.read(str(path), dtype='float32', always_2d=True)
    m = x.mean(axis=1)
    if sr != SR:
        idx = np.linspace(0, len(m) - 1, int(len(m) * SR / sr))
        m = np.interp(idx, np.arange(len(m)), m).astype('float32')
        sr = SR
    a = max(0, int(start * sr))
    seg = m[a:a + int(dur * sr)]
    return seg, sr


def best_energy_start(path, dur):
    x, sr = sf.read(str(path), dtype='float32', always_2d=True)
    m = x.mean(axis=1)
    if sr != SR:
        idx = np.linspace(0, len(m) - 1, int(len(m) * SR / sr))
        m = np.interp(idx, np.arange(len(m)), m).astype('float32')
        sr = SR
    step = int(0.5 * sr)
    win = int(dur * sr)
    best, bs = -1, 0.0
    for s in range(0, max(1, len(m) - win), step):
        e = float(np.mean(m[s:s+win] ** 2))
        if e > best:
            best, bs = e, s / sr
    return bs


def analyse(path, start):
    seg, sr = load_mono(path, start, WIN)
    if len(seg) < WIN * sr * 0.8:
        return None
    win = np.hanning(FRAME)
    ours = {}
    for i in range(0, len(seg) - FRAME, HOP):
        fr = seg[i:i+FRAME] * win
        if np.sqrt(np.mean(fr ** 2)) < 0.005:
            continue
        f = yin_frame(fr, sr, FMIN, FMAX, THRESH)
        if f > 0:
            ours[round(i / sr, 3)] = f
    snd = parselmouth.Sound(seg.astype('float64'), sampling_frequency=sr)
    pitch = snd.to_pitch(time_step=HOP / sr, pitch_floor=FMIN, pitch_ceiling=FMAX)
    n = pitch.get_number_of_frames()
    praat = {}
    for i in range(1, n + 1):
        t = round((i - 1) * HOP / sr, 3)
        v = pitch.get_value_at_time(t)
        if v and v == v and v > 0:
            praat[t] = v
    if not ours or not praat:
        return None
    common = sorted(set(ours) & set(praat))
    both = len(common)
    if both < 40:
        return None
    o = np.array([ours[t] for t in common])
    p = np.array([praat[t] for t in common])
    cents = 1200 * np.log2(o / p)
    ratio = o / p
    near = np.abs(cents) <= TOL
    octave = (np.abs(ratio - 2) < .06) | (np.abs(ratio - .5) < .06) | \
             (np.abs(ratio - 4) < .1) | (np.abs(ratio - .25) < .05)
    return {
        "frames_both": both,
        "frames_ours_only": len(set(ours) - set(praat)),
        "frames_praat_only": len(set(praat) - set(ours)),
        "agree_pct": round(float(near.mean()) * 100, 1),
        "octave_pct": round(float((octave & ~near).mean()) * 100, 1),
        "nonoctave_disagree_pct": round(float((~near & ~octave).mean()) * 100, 1),
        "abs_cents_median": round(float(np.median(np.abs(cents))), 1),
        "abs_cents_p90": round(float(np.percentile(np.abs(cents), 90)), 1),
    }


def main() -> None:
    random.seed(20261025)
    tour = json.loads((SITE / 'data' / 'archive_stage_tour.json').read_text(encoding='utf-8'))
    stage_rows = [r for r in tour['rows'] if r.get('low_t_s') and r.get('low_hz')]
    random.shuffle(stage_rows)
    studio = [p for p in D.glob('分离_专辑/**/vocals.wav')
              if p.parent.parent.name not in ('分离_专辑', 'input_ascii')]
    random.shuffle(studio)

    rows, excluded = [], []
    # 录音室：能量最高 6s 窗口（与两引擎无关）
    for f in studio:
        if sum(1 for r in rows if r['stratum'] == '录音室人声轨') >= N_PER:
            break
        try:
            st = best_energy_start(f, WIN)
            r = analyse(f, st)
        except Exception as e:
            excluded.append({"file": f.name, "why": type(e).__name__})
            continue
        if r:
            r.update({"stratum": "录音室人声轨", "file": str(f.parent.parent.name), "start_s": round(st, 1)})
            rows.append(r)
    # 现场：已登记低音时刻 ±3s（仅定位）
    for row in stage_rows:
        if sum(1 for r in rows if r['stratum'] == '现场混音') >= N_PER:
            break
        wav = row.get('tag') or ''
        cand = list(D.glob(f'场次音频/**/{wav}*')) or list(D.glob(f'场次音频/**/*{wav[:18]}*'))
        if not cand:
            excluded.append({"file": wav[:40], "why": "audio-not-found"})
            continue
        p = cand[0]
        try:
            r = analyse(p, max(0.0, float(row['low_t_s']) - 3.0))
        except Exception as e:
            excluded.append({"file": p.name, "why": type(e).__name__})
            continue
        if r:
            r.update({"stratum": "现场混音", "file": p.name[:48],
                      "start_s": round(max(0.0, float(row['low_t_s']) - 3.0), 1)})
            rows.append(r)

    def agg(sub):
        if not sub:
            return {}
        return {
            "segments": len(sub),
            "agree_pct_median": round(float(np.median([r['agree_pct'] for r in sub])), 1),
            "octave_pct_median": round(float(np.median([r['octave_pct'] for r in sub])), 1),
            "nonoctave_pct_median": round(float(np.median([r['nonoctave_disagree_pct'] for r in sub])), 1),
            "abs_cents_median": round(float(np.median([r['abs_cents_median'] for r in sub])), 1),
            "abs_cents_p90_median": round(float(np.median([r['abs_cents_p90'] for r in sub])), 1),
        }

    out = {
        "schema": "engine_disagreement/v1",
        "status": "exploratory",
        "publishable": False,
        "purpose": "真实素材的双引擎分歧诊断（非真值估计）",
        "engines": {"a": "自研 YIN", "b": "Praat autocorrelation (Parselmouth)"},
        "protocol": {"window_s": WIN, "fmin": FMIN, "fmax": FMAX, "hop": HOP,
                     "tol_cents": TOL, "aggregate": "先段内后跨段中位数"},
        "summary": {s: agg([r for r in rows if r['stratum'] == s])
                    for s in ('录音室人声轨', '现场混音')},
        "rows": rows, "excluded": excluded[:20],
        "limitations": ["一致性≠准确率：两法可能共同锁错",
                        "现场窗口用已登记低音时刻定位，存在定位偏差",
                        "样本为探索性，不可外推为总体比例"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(out['summary'], ensure_ascii=False, indent=1))
    print('段数', len(rows), '| 排除', len(excluded))


if __name__ == '__main__':
    main()
