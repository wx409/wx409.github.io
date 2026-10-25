#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比播放：先放原声，再放候选 A 音，再放候选 B 音，最后回到原声。

用法：python -X utf8 project_b/play_compare.py adj-01

原理：把候选 F0 合成一个"有泛音的音"（不是纯正弦），人耳更容易和真人的低音对上。
判据：
  · 哪个音和原声里的低音重合 → 那个候选更可能对
  · 两个都像 → both_reasonable_small_difference
  · 都不像 → unresolved / both_unreliable
"""
from __future__ import annotations

import json
import sys
import tempfile
import winsound
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding='utf-8')
ADJ = Path(r'D:\wx409.github.io\data\research\experiments\exp-20261025-01\adjudication')


def tone(f0: float, sr=44100, secs=2.0, nh=6):
    t = np.arange(int(secs * sr)) / sr
    y = np.zeros_like(t)
    for k in range(1, nh + 1):
        if f0 * k > sr / 2:
            break
        y += (1.0 / k) * np.sin(2 * np.pi * f0 * k * t)
    env = np.minimum(1, np.minimum(t / 0.05, (secs - t) / 0.15))
    y = y * env
    return (0.25 * y / (np.max(np.abs(y)) + 1e-9)).astype('float32')


def play(path: Path):
    winsound.PlaySound(str(path), winsound.SND_FILENAME)


def main() -> None:
    if len(sys.argv) < 2:
        print('用法: python -X utf8 project_b/play_compare.py adj-01'); sys.exit(1)
    aid = sys.argv[1]
    d = ADJ / 'materials' / aid
    if not d.exists():
        print('没有这个窗口:', aid); sys.exit(1)
    h = json.loads((d / 'harmonics.json').read_text(encoding='utf-8'))
    fa, fb = h.get('candidate_A_f0'), h.get('candidate_B_f0')
    print(f"{aid}｜{h['layer']}｜t={h['t_global']}s")
    print(f"  候选 A = {fa} Hz｜候选 B = {fb} Hz")
    for name, sup in (('A', h.get('support_A')), ('B', h.get('support_B'))):
        if sup:
            have = [s['harmonic'] for s in sup if s['peak_hz']]
            print(f"  候选{name} 谐波命中: {have}（1/2/3 都在 = 更像真音）")
    tmp = Path(tempfile.gettempdir())
    ta, tb = tmp / 'cand_A.wav', tmp / 'cand_B.wav'
    sf.write(str(ta), tone(fa), 44100)
    sf.write(str(tb), tone(fb), 44100)
    ratio = (max(fa, fb) / min(fa, fb)) if fa and fb else None
    if ratio and 1.8 < ratio < 2.2:
        print('\n  ⚠ 两候选正好差一倍 → 这是八度问题，别靠耳朵，直接看谐波列。')
    print('\n播放顺序：原声 → A → 原声 → B → 原声（各段 3 秒，便于来回对照）')
    clip = d / 'clip_context.wav'
    for _ in range(1):
        play(clip)
        play(ta)
        play(clip)
        play(tb)
        play(clip)
    print('听完后：先填归属；F0 拿不准就填 unresolved，不用硬选。')


if __name__ == '__main__':
    main()
