#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""区分独唱/合唱，并重算录音室特征（合唱不进能力榜单）。"""
from __future__ import annotations

import json
import sys
from statistics import median
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
full = json.loads((ROOT / 'data' / 'studio_full.json').read_text(encoding='utf-8'))['songs']
qq = json.loads((ROOT / 'data' / 'qq_singer_songs.json').read_text(encoding='utf-8'))['songs']
singers = {}
for s in qq:
    singers.setdefault(s['name'], s.get('singers') or '')


def is_duet(title: str) -> bool:
    s = singers.get(title)
    if not s:
        return False
    names = [x for x in s.replace('／', '/').split('/') if x.strip()]
    return len(names) > 1


for s in full:
    s['duet'] = is_duet(s['title'])
    s['singers'] = singers.get(s['title'], '')

solo = [s for s in full if not s['duet']]
duet = [s for s in full if s['duet']]
print('独唱', len(solo), '｜合唱', len(duet))
for s in duet:
    print('  合唱:', s['title'], '|', s['singers'])

# 音名 → Hz
NOTE = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6, 'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}


def note_hz(n: str) -> float:
    import re
    m = re.match(r'([A-G]#?)(\d)', n)
    if not m:
        return 0
    return 440 * 2 ** ((NOTE[m.group(1)] + 12 * (int(m.group(2)) + 1) - 69) / 12)


def weighted_median_pitch(hist: dict):
    if not hist:
        return None
    pairs = sorted(((note_hz(k), v) for k, v in hist.items() if v and note_hz(k)))
    total = sum(v for _, v in pairs)
    acc = 0
    for hz, v in pairs:
        acc += v
        if acc >= total / 2:
            return hz
    return pairs[-1][0]


singles_raw = json.loads((ROOT / 'data' / 'research' / 'singles_analysis.json').read_text(encoding='utf-8'))['songs']
hist = {s['title']: s.get('semitone_hist') for s in singles_raw}
pitches = []
for s in solo:
    h = hist.get(s['title'])
    p = weighted_median_pitch(h) if h else None
    s['median_pitch_hz'] = round(p, 1) if p else None
    if p:
        pitches.append(p)
print('独唱有声高直方图', len(pitches), '首｜中位音高中位 %.1f Hz' % median(pitches) if pitches else '')

out = {
    "schema": "studio_solo_duet_split/v1",
    "counts": {"total": len(full), "solo": len(solo), "duet": len(duet)},
    "duets": [{"title": s['title'], "singers": s['singers']} for s in duet],
    "solo_median_pitch_hz": round(median(pitches), 1) if pitches else None,
    "songs": full,
}
(ROOT / 'data' / 'studio_solo_duet_split.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
