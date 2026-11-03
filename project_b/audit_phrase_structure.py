#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""句内结构审计版：纳入/排除清单、分布、两种汇总口径。

规则（写死并随结果保存）：
  · 音符：逐帧 F0 连续有声；抖动 >0.6 半音即切
  · 段：帧间隔 >0.3 秒即切（称“自动分段”，不称“句子”）
  · 低音：全曲 MIDI 的 P10 及以下
  · 句尾方向：段末 8 帧中位 − 段末前 16–30 帧中位
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

songs = json.loads((ROOT / 'data' / 'studio_full.json').read_text(encoding='utf-8'))['songs']
titles = {s['title'] for s in songs if len(s['title']) >= 2}

files = []
for p in ANA.rglob('*_f0.csv'):
    stem = p.stem.replace('_f0', '')
    hit = [t for t in titles if t in stem]
    if hit:
        files.append((p, max(hit, key=len)))

included, excluded = [], []
all_low_pos, per_song = [], []
end_dirs_all = []

seen = {}
for p, title in files:
    try:
        df = pd.read_csv(p, encoding='utf-8-sig')[['time_s', 'midi']].dropna()
        df = df[df['midi'] > 20]
    except Exception as e:
        excluded.append({"title": title, "file": p.name, "reason": f"读取失败:{e.__class__.__name__}"})
        continue
    if len(df) < 200:
        excluded.append({"title": title, "file": p.name, "reason": f"帧数不足({len(df)})"})
        continue
    t = df['time_s'].to_numpy(); m = df['midi'].to_numpy()
    gaps = np.where(np.diff(t) > 0.3)[0]
    starts = np.r_[0, gaps + 1]; ends = np.r_[gaps, len(t) - 1]
    phrases = [(a, b) for a, b in zip(starts, ends) if b - a >= 8]
    if len(phrases) < 5:
        excluded.append({"title": title, "file": p.name, "reason": f"自动分段不足({len(phrases)})"})
        continue
    thr = np.percentile(m, 10)
    lows, ends_dir = [], []
    for a, b in phrases:
        seg = m[a:b + 1]
        if len(seg) >= 30:
            ends_dir.append(float(np.median(seg[-8:]) - np.median(seg[-30:-16])))
        li = np.where(seg <= thr)[0]
        if len(li):
            lows.append(float(li.mean() / max(1, len(seg) - 1)))
    rec = {"title": title, "file": p.name, "phrases": len(phrases),
           "low_events": len(lows), "low_pos_median": round(float(np.median(lows)), 3) if lows else None,
           "end_dir_median": round(float(np.median(ends_dir)), 2) if ends_dir else None,
           "end_down_share": round(float(np.mean([d < -0.3 for d in ends_dir])), 3) if ends_dir else None}
    k = title
    if k not in seen or rec['phrases'] > seen[k]['phrases']:
        seen[k] = rec
    all_low_pos += lows
    end_dirs_all += ends_dir

included = list(seen.values())
bins = Counter()
for v in all_low_pos:
    bins['0-0.25' if v < 0.25 else '0.25-0.5' if v < 0.5 else '0.5-0.75' if v < 0.75 else '0.75-1.0'] += 1
total_low = sum(bins.values()) or 1
out = {
    "schema": "phrase_structure_audit/v1",
    "rules": {
        "frame": "逐帧 F0（hop 512 @44.1k ≈ 11.6ms）",
        "segment": "帧间隔 >0.3s 切段；称“自动分段”，不等同乐句/句子",
        "low_threshold": "全曲 MIDI 的 P10 及以下",
        "end_direction": "段末 8 帧中位 − 段末前 16–30 帧中位",
        "min_frames": 200, "min_segments": 5,
    },
    "counts": {"included": len(included), "excluded": len(excluded), "low_events": total_low},
    "low_pos_distribution": {k: f"{v/total_low*100:.1f}%" for k, v in bins.items()},
    "per_song_equal_weight": {
        "low_pos_median": round(statistics.median([r['low_pos_median'] for r in included if r['low_pos_median'] is not None]), 3),
        "end_dir_median": round(statistics.median([r['end_dir_median'] for r in included if r['end_dir_median'] is not None]), 2),
    },
    "per_low_event_pooled": {
        "low_pos_median": round(float(np.median(all_low_pos)), 3) if all_low_pos else None,
        "end_dir_median": round(float(np.median(end_dirs_all)), 2) if end_dirs_all else None,
    },
    "included": included,
    "excluded": excluded[:40],
}
(ROOT / 'data' / 'phrase_structure_audit.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('纳入', len(included), '｜排除', len(excluded), '｜低音事件', total_low)
print('分布', out['low_pos_distribution'])
print('逐曲等权', out['per_song_equal_weight'])
print('逐事件汇总', out['per_low_event_pooled'])
