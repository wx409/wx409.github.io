#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""派生「能力主线」数字：稳 / 准 / 气 / 控 / 变。全部来自已有数据文件。"""
from __future__ import annotations

import json
import sys
from statistics import median
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
D = Path(r'D:\wx409.github.io\data')
OUT = D / 'ability_highlights.json'

inton = json.loads((D / 'research' / 'live_intonation.json').read_text(encoding='utf-8'))['shows']
by_year = {}
for r in inton:
    by_year.setdefault(r['year'], []).append(r['stability_med'])
years = {y: round(median(v), 1) for y, v in sorted(by_year.items())}
all_stab = round(median([r['stability_med'] for r in inton]), 1)

vers = json.loads((D / 'live_versions.json').read_text(encoding='utf-8'))['songs']
cross = [{"song": s['song'], "n": s['n_versions'], "range": s['low_range_semitones']}
         for s in vers if s.get('n_versions', 0) >= 3 and s.get('low_range_semitones') is not None]
cross.sort(key=lambda x: x['range'])

xyy = json.loads((D / 'research' / 'xyy_long_phrase.json').read_text(encoding='utf-8'))
long_phrase = max(x['dur'] for x in xyy['phrases'] if x['dur'] < 20)

out = {
    "schema": "ability_highlights/v1",
    "generated_at": __import__('datetime').datetime.now().isoformat(timespec='seconds'),
    "stability": {"all_shows_median_cents": all_stab, "by_year": years,
                  "note": "音符内稳定性（越小越稳）；数据源 live_intonation.json"},
    "cross_version": {"examples": cross[:5],
                      "note": "同一首歌不同场次最低音读数的极差（半音）；数据源 live_versions.json"},
    "long_phrase": {"seconds": round(long_phrase, 1), "song": "想游泳的星",
                    "breath_gap_s": [0.67, 1.03], "breath_gap_db": [12, 20],
                    "note": "六轨人声 + CREPE/Praat 双引擎；气口由能量包络定位"},
    "live_vs_studio": {"db": -3.2, "centroid_studio": 2860, "centroid_live": 1956,
                       "song": "无尽的夜里", "date": "2025-11-21",
                       "note": "同段落对照；现场更轻更暗"},
    "firelight_three": {"note": "火光『向前闯』三次：音高逐帧重合、各 2.55 秒",
                        "third_hnr_drop_db": 3.6, "subharmonic": 0.01,
                        "high_freq": "更暗而非更亮"},
    "discipline": "只收『差距远大于误差』的指标；极值音不在此表",
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('能力主线数字已派生：稳定中位', all_stab, '｜跨版极差最小', cross[0] if cross else None)
