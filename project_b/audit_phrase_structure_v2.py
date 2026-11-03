#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""句内结构审计（v2）：固定文件选择规则 + 88 首闭合对账。

文件选择（预先确定，不看结果）：
  1. 只取录音室路径 `专辑音频_分析/<专辑>/<曲名>_f0.csv`
  2. 文件名必须等于「曲名_f0.csv」（不接受现场/混剪文件）
  3. 多条候选时按路径字典序取第一条
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
ANA = Path(r'E:\wx\论文素材_王晰作传\音域分析')
STUDIO_DIR = ANA / '专辑音频_分析'

full = json.loads((ROOT / 'data' / 'studio_full.json').read_text(encoding='utf-8'))['songs']
flagged = [s for s in full if s.get('f0_csv')]

picks, no_studio = {}, []
for s in flagged:
    t = s['title']
    cands = sorted([p for p in STUDIO_DIR.rglob(f'{t}_f0.csv')])
    if not cands:
        no_studio.append(t)
        continue
    picks[t] = cands[0]

included, excluded = [], []
all_low, end_dirs = [], []
for title, p in picks.items():
    try:
        df = pd.read_csv(p, encoding='utf-8-sig')[['time_s', 'midi']].dropna()
        df = df[df['midi'] > 20]
    except Exception as e:
        excluded.append({"title": title, "reason": f"读取失败:{e.__class__.__name__}", "file": p.name})
        continue
    if len(df) < 200:
        excluded.append({"title": title, "reason": f"帧数不足({len(df)})", "file": p.name})
        continue
    t = df['time_s'].to_numpy(); m = df['midi'].to_numpy()
    gaps = np.where(np.diff(t) > 0.3)[0]
    starts = np.r_[0, gaps + 1]; ends = np.r_[gaps, len(t) - 1]
    segs = [(a, b) for a, b in zip(starts, ends) if b - a >= 8]
    if len(segs) < 5:
        excluded.append({"title": title, "reason": f"自动分段不足({len(segs)})", "file": p.name})
        continue
    thr = np.percentile(m, 10)
    lows, ed = [], []
    for a, b in segs:
        seg = m[a:b + 1]
        if len(seg) >= 30:
            ed.append(float(np.median(seg[-8:]) - np.median(seg[-30:-16])))
        li = np.where(seg <= thr)[0]
        if len(li):
            lows.append(float(li.mean() / max(1, len(seg) - 1)))
    included.append({"title": title, "file": p.name, "segments": len(segs),
                     "low_events": len(lows),
                     "low_pos_median": round(float(np.median(lows)), 3) if lows else None,
                     "end_dir_median": round(float(np.median(ed)), 2) if ed else None})
    all_low += lows
    end_dirs += ed

bins = Counter()
for v in all_low:
    bins['0-0.25' if v < 0.25 else '0.25-0.5' if v < 0.5 else '0.5-0.75' if v < 0.75 else '0.75-1.0'] += 1
tot = sum(bins.values()) or 1
out = {
    "schema": "phrase_structure_audit/v2",
    "file_rule": "只取 专辑音频_分析/<专辑>/<曲名>_f0.csv；多条取字典序第一条；不看分段数",
    "reconciliation": {
        "flagged_88": len(flagged),
        "included": len(included),
        "excluded": len(excluded),
        "no_studio_file": len(no_studio),
        "no_studio_titles": no_studio,
        "sum_check": len(included) + len(excluded) + len(no_studio),
    },
    "definitions": {
        "segment": "帧间隔 >0.3s 切段（自动分段，不等同乐句）",
        "low": "每曲 MIDI 的 P10 及以下 → 称「曲内低十分位读数」，不是绝对低音",
        "end_direction": "段末 8 帧中位 − 段末前 16–30 帧中位",
    },
    "low_pos_distribution": {k: f"{v/tot*100:.1f}%" for k, v in bins.items()},
    "per_song_median_low_pos": round(statistics.median([r['low_pos_median'] for r in included if r['low_pos_median'] is not None]), 3),
    "pooled_low_pos": round(float(np.median(all_low)), 3) if all_low else None,
    "end_dir_median": round(float(np.median(end_dirs)), 2) if end_dirs else None,
    "low_events": tot,
    "included": included,
    "excluded": excluded,
}
(ROOT / 'data' / 'phrase_structure_audit.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(out['reconciliation'], ensure_ascii=False))
print('分布', out['low_pos_distribution'])
print('逐曲中位', out['per_song_median_low_pos'], '｜合并', out['pooled_low_pos'], '｜尾向', out['end_dir_median'])
