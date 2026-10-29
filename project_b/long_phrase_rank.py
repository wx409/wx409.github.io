#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""37 场最长连续发声排行（初筛用两轨人声轨，逐曲 CREPE；取 top 后另行六轨复核）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
import torchcrepe

sys.stdout.reconfigure(encoding='utf-8')
SEP = Path(r'E:\wx\论文素材_王晰作传\_staging_现场_分离')
OUT = Path(r'D:\wx409.github.io\data\research\live_long_phrase_rank.json')
LOG = Path(r'D:\wx409.github.io\temp\long_phrase_rank.log')
MAX_SEC = 8 * 60


def longest_phrase(m, sr):
    idx = np.linspace(0, len(m) - 1, int(len(m) * 16000 / sr))
    m16 = np.interp(idx, np.arange(len(m)), m).astype('float32')
    f0, pd = torchcrepe.predict(torch.tensor(m16).unsqueeze(0), 16000, hop_length=160,
                                fmin=60, fmax=1000, model='full', batch_size=2048,
                                device='cuda' if torch.cuda.is_available() else 'cpu',
                                return_periodicity=True)
    f0 = f0.squeeze().cpu().numpy(); pd = pd.squeeze().cpu().numpy()
    ok = (pd > 0.55) & (f0 > 60)
    gap = 20
    best = (0, 0, 0)
    start = None; last = None
    for i in range(len(ok)):
        if ok[i]:
            if start is None:
                start = i
            last = i
        elif last is not None and i - last > gap:
            if last - start > best[0]:
                best = (last - start + 1, start, last)
            start = None; last = None
    if start is not None and last - start > best[0]:
        best = (last - start + 1, start, last)
    n, s, e = best
    if n == 0:
        return None
    seg = f0[s:e + 1]; seg = seg[seg > 60]
    return {"dur": round(n / 100, 2), "t0": round(s / 100, 2),
            "median_hz": round(float(np.median(seg)), 1) if len(seg) else None,
            "min_hz": round(float(seg.min()), 1) if len(seg) else None}


def main() -> None:
    rows = []
    files = sorted(SEP.rglob('vocals.wav'))
    with open(LOG, 'w', encoding='utf-8') as lg:
        lg.write(f'共 {len(files)} 个文件\n')
        for i, f in enumerate(files, 1):
            album = f.parts[-5] if len(f.parts) >= 5 else ''
            title = f.parts[-4]
            try:
                x, sr = sf.read(str(f), dtype='float32', always_2d=True)
                m = x.mean(axis=1)
                if len(m) / sr > MAX_SEC:
                    m = m[:MAX_SEC * sr]
                r = longest_phrase(m, sr)
                if r:
                    rows.append({"show": album, "song": title, **r})
                    if r['dur'] > 12:
                        lg.write(f"{i}/{len(files)} {album} {title} {r['dur']}s\n")
            except Exception as e:
                lg.write(f'失败 {f}: {e}\n')
            if i % 50 == 0:
                lg.write(f'进度 {i}/{len(files)}\n'); lg.flush()
    rows.sort(key=lambda r: -r['dur'])
    OUT.write_text(json.dumps({"schema": "live_long_phrase_rank/v1", "count": len(rows),
                               "method": "两轨人声轨 + CREPE；top 待六轨复核",
                               "rows": rows[:100]}, ensure_ascii=False, indent=1), encoding='utf-8')
    print('完成', len(rows), '首｜top1', rows[0] if rows else None)


if __name__ == '__main__':
    main()
