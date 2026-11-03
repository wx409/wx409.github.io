#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""句内结构统计：句尾走向 + 低音落点（用逐帧 F0，避开歌词对齐）。

对每首歌：
  · 连续有声段切音符（抖动 <0.6 半音），间隔 >0.3s 切句
  · 句尾方向：末音相对前一个音（半音）
  · 低音落点：全曲最低 10% 的音，在一句里的相对位置（0=句首，1=句尾）
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
ANA = Path(r'E:\wx\论文素材_王晰作传\音域分析')

songs = json.loads((ROOT / 'data' / 'studio_full.json').read_text(encoding='utf-8'))['songs']
solo_titles = {s['title'] for s in songs if s['source'] == 'single' or s['source'] == 'album'}
solo_titles = {t for t in solo_titles if len(t) >= 2}

files = []
for p in ANA.rglob('*_f0.csv'):
    stem = p.stem.replace('_f0', '')
    hit = [t for t in solo_titles if t in stem]
    if hit and ('专辑' in str(p) or '分析结果' in str(p) or 'v2tmp' in str(p)):
        files.append((p, max(hit, key=len)))


def load(p):
    df = pd.read_csv(p, encoding='utf-8-sig')
    df = df[['time_s', 'midi']].dropna()
    return df[df['midi'] > 20]


rows = []
for p, title in files[:400]:
    try:
        df = load(p)
    except Exception:
        continue
    if len(df) < 200:
        continue
    t = df['time_s'].to_numpy()
    m = df['midi'].to_numpy()
    # 切句：间隔 > 0.3s
    gaps = np.where(np.diff(t) > 0.3)[0]
    starts = np.r_[0, gaps + 1]
    ends = np.r_[gaps, len(t) - 1]
    phrases = []
    for a, b in zip(starts, ends):
        if b - a >= 8:                      # 至少 8 帧
            phrases.append((a, b))
    if len(phrases) < 5:
        continue
    thr = np.percentile(m, 10)
    lows = []
    end_dirs = []
    for a, b in phrases:
        seg = m[a:b + 1]
        # 句尾方向：末 3 帧中位 vs 前 3 帧中位
        if len(seg) >= 30:
            end_dirs.append(float(np.median(seg[-8:]) - np.median(seg[-30:-16])))
        low_idx = np.where(seg <= thr)[0]
        if len(low_idx):
            pos = low_idx.mean() / max(1, len(seg) - 1)
            lows.append(float(pos))
    if not end_dirs:
        continue
    rows.append({
        "title": title,
        "file": p.name,
        "phrases": len(phrases),
        "end_dir_median": round(float(np.median(end_dirs)), 2),
        "end_down_share": round(float(np.mean([d < -0.3 for d in end_dirs])), 3),
        "low_pos_median": round(float(np.median(lows)), 3) if lows else None,
        "n_low": len(lows),
    })

# 每首取最匹配的一条（同曲多文件时保留乐句最多的）
best = {}
for r in rows:
    k = r['title']
    if k not in best or r['phrases'] > best[k]['phrases']:
        best[k] = r
vals = list(best.values())
summary = {
    "schema": "phrase_structure/v1",
    "songs_analyzed": len(vals),
    "end_dir_median_semitones": round(statistics.median([v['end_dir_median'] for v in vals]), 2) if vals else None,
    "end_down_share_median": round(statistics.median([v['end_down_share'] for v in vals]), 3) if vals else None,
    "low_pos_median": round(statistics.median([v['low_pos_median'] for v in vals if v['low_pos_median'] is not None]), 3) if vals else None,
    "songs": vals,
}
(ROOT / 'data' / 'phrase_structure.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps({k: v for k, v in summary.items() if k != 'songs'}, ensure_ascii=False))
print('样例:', [(v['title'], v['end_dir_median'], v['low_pos_median']) for v in vals[:6]])
