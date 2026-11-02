#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把整轨 FLAC 按静音/掌声切成单曲片段（供逐曲声学分析）。

规则：RMS 低于「全场中位 −25dB」持续 ≥1.5 秒 → 切点；保留 ≥45 秒的片段。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding='utf-8')
H = Path(r'H:\王晰巡演素材存档\现场录制视频')
OUT = Path(r'E:\wx\论文素材_王晰作传\_staging_现场')
LOGS = Path(r'D:\wx409.github.io\temp')

SHOWS = [
    ('h5_sh_20231231', H / '四巡' / '2023.12.31上海第3场'),
    ('h5_bj2_20240816', H / '四巡' / '2024.8.16北京第 场'),
    ('h5_bj_20260410', H / '五巡' / '20260410五巡北京站收官场'),
]


def split_file(p: Path, tag: str, idx_start: int):
    x, sr = sf.read(str(p), dtype='float32', always_2d=True)
    m = x.mean(axis=1)
    hop = int(0.1 * sr)
    n = len(m) // hop
    env = np.array([np.sqrt(np.mean(m[i*hop:(i+1)*hop]**2)) for i in range(n)])
    db = 20 * np.log10(env + 1e-12)
    thr = np.median(db) - 25
    quiet = db < thr
    # 找静音段
    gaps = []
    i = 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]:
                j += 1
            if (j - i) * 0.1 >= 1.5:
                gaps.append((i * 0.1, j * 0.1))
            i = j
        else:
            i += 1
    # 切分
    bounds = [0.0] + [ (a + b) / 2 for a, b in gaps ] + [len(m) / sr]
    chunks = []
    idx = idx_start
    for k in range(len(bounds) - 1):
        a, b = bounds[k], bounds[k + 1]
        if b - a < 45:
            continue
        seg = m[int(a*sr):int(b*sr)]
        name = f'{tag}_{idx:02d}_{int(a)}s.wav'
        sf.write(str(OUT / tag / name), seg, sr)
        chunks.append({"file": name, "start": round(a, 1), "dur": round(b - a, 1)})
        idx += 1
    return chunks, len(gaps)


def main() -> None:
    report = {}
    for tag, d in SHOWS:
        dst = OUT / tag
        dst.mkdir(parents=True, exist_ok=True)
        if any(dst.glob('*.wav')):
            print(tag, '已切分，跳过')
            continue
        flacs = sorted([f for f in d.rglob('*.flac') if f.name.count(' ') < 3])
        allc = []
        idx = 1
        for f in flacs:
            try:
                c, ngaps = split_file(f, tag, idx)
                idx += len(c)
                allc += c
                print(f'{tag} | {f.name[:40]} → {len(c)} 段（静音 {ngaps}）', flush=True)
            except Exception as e:
                print(tag, '失败', f.name, repr(e)[:60], flush=True)
        report[tag] = allc
        print(f'{tag} 合计 {len(allc)} 段', flush=True)
    (LOGS / 'h5_split_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
