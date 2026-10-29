#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""高质量素材（录音笔 3 条 + 想游泳的星六轨）用同一方法测最长连续发声，并对同曲去重。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchcrepe

sys.path.insert(0, r'D:\wx409.github.io\project_b')
sys.stdout.reconfigure(encoding='utf-8')

CLIPS = [
    (Path(r'E:\wx\论文素材_王晰作传\现场录音-录音笔\录音笔直出\BV1eC4y1Y7JH_【3w块录音设备系列】【王晰】【纯享版】23.12.31肆意_四巡_上海站.wav'),
     '2023-12-31 上海（录音笔 3w 设备）', '多听有益等（纯享版）', 'recorder'),
    (Path(r'E:\wx\论文素材_王晰作传\现场录音-录音笔\录音笔直出\BV1Mi421C7gW_录音笔直出高音质，诚邀大家戴上耳机沉浸式体验王哥的现场魅力_【4K字幕】《海然海然_x_嘎达梅林》_王晰【肆益】个人巡回.wav'),
     '2024 肆益巡演（录音笔）', '海然海然×嘎达梅林', 'recorder'),
    (Path(r'E:\wx\论文素材_王晰作传\现场录音-录音笔\录音笔直出\BV1eprkYpEce_【王晰】《我很好》【4K字幕】_如果王哥年轻的时候选择搞摇滚的话我也会爱上_王晰『吾』个人巡回音乐会_20250101_.wav'),
     '2025-01-01 长沙（录音笔）', '我很好', 'recorder'),
    (Path(r'E:\wx\论文素材_王晰作传\现场录音-补充\xyy_vocals_6s.wav'),
     '2024-04-06 上海（六轨人声）', '想游泳的星', '6s'),
]


def longest(m, sr):
    idx = np.linspace(0, len(m) - 1, int(len(m) * 16000 / sr))
    m16 = np.interp(idx, np.arange(len(m)), m).astype('float32')
    f0, pd = torchcrepe.predict(torch.tensor(m16).unsqueeze(0), 16000, hop_length=160,
                                fmin=60, fmax=1000, model='full', batch_size=2048,
                                device='cuda' if torch.cuda.is_available() else 'cpu',
                                return_periodicity=True)
    f0 = f0.squeeze().cpu().numpy(); pd = pd.squeeze().cpu().numpy()
    ok = (pd > 0.55) & (f0 > 60)
    gap = 20; best = (0, 0, 0); start = None; last = None
    for i in range(len(ok)):
        if ok[i]:
            if start is None: start = i
            last = i
        elif last is not None and i - last > gap:
            if last - start > best[0]: best = (last - start + 1, start, last)
            start = None; last = None
    if start is not None and last - start > best[0]:
        best = (last - start + 1, start, last)
    n, s, e = best
    if not n:
        return None
    seg = f0[s:e + 1]; seg = seg[seg > 60]
    return {"dur": round(n / 100, 2), "t0": round(s / 100, 2),
            "median_hz": round(float(np.median(seg)), 1), "min_hz": round(float(seg.min()), 1)}


rows = []
for path, show, song, kind in CLIPS:
    if not path.exists():
        print('缺失', path.name[:40]); continue
    x, sr = sf.read(str(path), dtype='float32', always_2d=True)
    r = longest(x.mean(axis=1), sr)
    if r:
        rows.append({"show": show, "song": song, "source": kind, **r})
        print(f"{show[:26]:26s} {song[:16]:16s} {r['dur']}s 中位 {r['median_hz']}Hz")
Path(r'D:\wx409.github.io\temp\long_phrase_extra.json').write_text(
    json.dumps(rows, ensure_ascii=False, indent=1), encoding='utf-8')
print('已写 temp/long_phrase_extra.json')
