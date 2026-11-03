#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""录音室全量（155 首）特征：聚合统计，供作传/社媒取材。"""
from __future__ import annotations

import json
import sys
from statistics import median
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
d = json.loads((ROOT / 'data' / 'studio_full.json').read_text(encoding='utf-8'))
songs = d['songs']
alb = [s for s in songs if s['source'] == 'album']
sgl = [s for s in songs if s['source'] == 'single']


def med(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(median(xs), 2) if xs else None


def share(cond, arr=songs):
    n = sum(1 for s in arr if cond(s))
    return round(n / len(arr) * 100, 1) if arr else None


stats = {
    "total": len(songs), "album": len(alb), "single": len(sgl),
    "stability": {"median": med([s['stability_cents'] for s in songs]),
                  "album_median": med([s['stability_cents'] for s in alb]),
                  "single_median": med([s['stability_cents'] for s in sgl]),
                  "le8_share": share(lambda s: (s['stability_cents'] or 99) <= 8),
                  "le6_share": share(lambda s: (s['stability_cents'] or 99) <= 6)},
    "span": {"median": med([s['span_octaves'] for s in songs]),
             "max": max((s['span_octaves'] or 0) for s in songs),
             "ge2_5_share": share(lambda s: (s['span_octaves'] or 0) >= 2.5)},
    "vibrato": {"rate_median": med([s['vibrato_hz'] for s in songs]),
                "extent_median": med([s['vibrato_cents'] for s in songs])},
    "density": {"median": med([s['density'] for s in songs])},
    "register": {
        "below_C3_median": med([(s.get('register_share') or {}).get('low_lt_C3') for s in songs]),
        "mid_median": med([(s.get('register_share') or {}).get('mid_C3_B3') for s in songs]),
        "high_median": med([(s.get('register_share') or {}).get('high_ge_C4') for s in songs]),
    },
    "low": {
        "le_C2": sum(1 for s in songs if (s['low_hz'] or 999) <= 65.5),
        "le_D2": sum(1 for s in songs if (s['low_hz'] or 999) <= 75.5),
        "b1": [s['title'] for s in songs if s['low_note'] == 'B1'],
        "lowest": min(((s['low_hz'] or 999), s['title'], s['low_note']) for s in songs),
    },
    "high": {"highest": max(((s['high_hz'] or 0), s['title'], s['high_note']) for s in songs)},
}
# 专辑 vs 单曲 对比
for k, f in (('stability_cents', 'stability'), ('span_octaves', 'span'), ('density', 'density')):
    stats[f][f'album_vs_single_{k}'] = [med([s[k] for s in alb]), med([s[k] for s in sgl])]

top = {
    "most_stable": sorted([s for s in songs if s['stability_cents']],
                          key=lambda s: s['stability_cents'])[:8],
    "widest": sorted([s for s in songs if s['span_octaves']],
                     key=lambda s: -s['span_octaves'])[:8],
    "highest_share": sorted([s for s in songs if (s.get('register_share') or {}).get('high_ge_C4')],
                            key=lambda s: -(s['register_share']['high_ge_C4']))[:8],
}
out = {"schema": "studio_characteristics/v1", "stats": stats,
       "top": {k: [{"title": s['title'], "source": s['source'],
                    "v": (s['stability_cents'] if k == 'most_stable' else
                          s['span_octaves'] if k == 'widest' else s['register_share']['high_ge_C4'])}
                   for s in v] for k, v in top.items()}}
(ROOT / 'data' / 'studio_characteristics.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(stats, ensure_ascii=False, indent=1)[:1800])
