#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对能量口径排名前 N 条做六轨复核：6s 分离后，用「能量 + 周期性」双条件判连续发声。"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault('HF_HUB_OFFLINE', '1')
import numpy as np
import soundfile as sf
import torch
import torchcrepe
from demucs.api import Separator

sys.stdout.reconfigure(encoding='utf-8')
STAGE = Path(r'E:\wx\论文素材_王晰作传\_staging_现场')
OUT = Path(r'D:\wx409.github.io\data\research\live_long_phrase_verified.json')
SR = 44100


def phrase(m, sr):
    hop = int(0.01 * sr); win = int(0.03 * sr)
    n = max(0, (len(m) - win) // hop)
    frames = np.lib.stride_tricks.sliding_window_view(m, win)[np.arange(n) * hop]
    rms = np.sqrt((frames ** 2).mean(axis=1))
    db = 20 * np.log10(rms + 1e-12)
    thr = np.median(db) - 12
    on = db > thr
    # 周期性
    m16 = np.interp(np.linspace(0, len(m) - 1, int(len(m) * 16000 / sr)), np.arange(len(m)), m).astype('float32')
    f0, pd = torchcrepe.predict(torch.tensor(m16).unsqueeze(0), 16000, hop_length=160,
                                fmin=60, fmax=1000, model='full', batch_size=2048,
                                device='cuda' if torch.cuda.is_available() else 'cpu',
                                return_periodicity=True)
    pd = pd.squeeze().cpu().numpy()
    voiced = pd > 0.55
    # 对齐帧（100Hz vs 100Hz）
    L = min(len(on), len(voiced))
    good = on[:L] & voiced[:L]
    gapmax = 25
    best = (0, 0); start = None; last = None
    for i in range(L):
        if good[i]:
            if start is None: start = i
            last = i
        elif last is not None and i - last > gapmax:
            if last - start + 1 > best[0]: best = (last - start + 1, start)
            start = None; last = None
    if start is not None and last - start + 1 > best[0]:
        best = (last - start + 1, start)
    return round(best[0] / 100, 2), round(best[1] / 100, 2)


def main() -> None:
    d = json.loads((Path(r'D:\wx409.github.io\data\research\live_long_phrase_energy.json')).read_text(encoding='utf-8'))['rows']
    seen = set(); cands = []
    for r in d:
        k = (r['show'], r['song'])
        if k in seen:
            continue
        seen.add(k)
        cands.append(r)
        if len(cands) >= 6:
            break
    sep = Separator(model='htdemucs_6s', device='cuda' if torch.cuda.is_available() else 'cpu', progress=False)
    out = []
    for c in cands:
        src = STAGE / c['show'] / (c['song'] + '.wav')
        if not src.exists():
            print('缺文件', c['show'], c['song']); continue
        x, sr = sf.read(str(src), dtype='float32', always_2d=True)
        if x.shape[1] == 1:
            x = np.repeat(x, 2, axis=1)
        if sr != SR:
            from math import gcd
            from scipy.signal import resample_poly
            g = gcd(sr, SR); x = resample_poly(x, SR // g, sr // g, axis=0).astype('float32'); sr = SR
        _, parts = sep.separate_tensor(torch.from_numpy(x.T.copy()), sr)
        v = parts['vocals'].cpu().numpy().T.mean(axis=1)
        dur, t0 = phrase(v, sr)
        out.append({"show": c['show'], "song": c['song'], "dur": dur, "t0": t0})
        print(f"{c['show']:14s} {c['song'][:18]:18s} → {dur}s", flush=True)
    out.sort(key=lambda r: -r['dur'])
    OUT.write_text(json.dumps({"schema": "live_long_phrase_verified/v1", "rows": out},
                              ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
