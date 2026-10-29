#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最长连续发声（能量口径）：RMS 低于中位 12dB 视为断点，缺口 ≤0.25s 允许合并。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding='utf-8')
SEP = Path(r'E:\wx\论文素材_王晰作传\_staging_现场_分离')
OUT = Path(r'D:\wx409.github.io\data\research\live_long_phrase_energy.json')
LOG = Path(r'D:\wx409.github.io\temp\long_phrase_energy.log')


def longest(m, sr):
    hop = int(0.01 * sr); win = int(0.03 * sr)
    n = max(0, (len(m) - win) // hop)
    if n < 100:
        return None
    rms = np.sqrt(np.add.reduceat(m[:n * hop + win - hop] ** 2, np.arange(0, n * hop, hop)) / win) if False else None
    # 直接逐帧（numpy 向量化）
    idx = np.arange(n) * hop
    frames = np.lib.stride_tricks.sliding_window_view(m, win)[idx]
    rms = np.sqrt((frames ** 2).mean(axis=1))
    db = 20 * np.log10(rms + 1e-12)
    thr = np.median(db) - 12
    on = db > thr
    gapmax = 25
    best = (0, 0, 0); start = None; last = None
    for i in range(len(on)):
        if on[i]:
            if start is None:
                start = i
            last = i
        elif last is not None and i - last > gapmax:
            if last - start + 1 > best[0]:
                best = (last - start + 1, start, last)
            start = None; last = None
    if start is not None and last - start + 1 > best[0]:
        best = (last - start + 1, start, last)
    n2, s, e = best
    if n2 < 100:
        return None
    return {"dur": round(n2 / 100, 2), "t0": round(s / 100, 2)}


rows = []
files = sorted(SEP.rglob('vocals.wav'))
with open(LOG, 'w', encoding='utf-8') as lg:
    for i, f in enumerate(files, 1):
        album = f.parts[-5] if len(f.parts) >= 5 else ''
        title = f.parts[-4]
        try:
            x, sr = sf.read(str(f), dtype='float32', always_2d=True)
            r = longest(x.mean(axis=1), sr)
            if r:
                rows.append({"show": album, "song": title, **r})
        except Exception as e:
            lg.write(f'失败 {f}: {e}\n')
        if i % 100 == 0:
            lg.write(f'进度 {i}/{len(files)}\n'); lg.flush()
rows.sort(key=lambda r: -r['dur'])
OUT.write_text(json.dumps({"schema": "live_long_phrase_energy/v1", "count": len(rows),
                           "method": "RMS 中位-12dB 断点、缺口≤0.25s 合并", "rows": rows[:80]},
                          ensure_ascii=False, indent=1), encoding='utf-8')
print('完成', len(rows), '｜top5')
for r in rows[:5]:
    print(f"  {r['dur']:6.2f}s {r['show'][:20]:20s} {r['song'][:18]}")
