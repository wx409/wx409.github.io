#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并录音室全量：72 首专辑曲 + 83 首单曲/OST → data/studio_full.json

统一字段，并标注每首是否有逐帧 F0 落盘。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
ANA = Path(r'E:\wx\论文素材_王晰作传\音域分析')

albums = json.loads((ROOT / 'data' / 'archive_vocal_albums.json').read_text(encoding='utf-8'))['songs']
singles = json.loads((ROOT / 'data' / 'research' / 'singles_analysis.json').read_text(encoding='utf-8'))['songs']

f0_names = {p.stem.replace('_f0', '') for p in ANA.rglob('*_f0.csv')}


def has_f0(title: str) -> bool:
    return any(title in n for n in f0_names)


rows = []
for s in albums:
    rows.append({
        "title": s['title'], "source": "album", "album": s.get('album'),
        "low_note": s.get('low'), "low_hz": s.get('low_hz'),
        "high_note": s.get('high'), "high_hz": s.get('high_hz'),
        "span_octaves": s.get('span_octaves'), "note_count": s.get('notes'),
        "density": s.get('density'), "stability_cents": s.get('stability_cents'),
        "intonation_cents": s.get('intonation_cents'),
        "vibrato_hz": s.get('vibrato_hz'), "vibrato_cents": s.get('vibrato_cents'),
        "hnr_db": s.get('hnr_db'), "register_share": s.get('register_share'),
        "duration_s": None, "rms_db": None, "centroid_hz": None,
        "f0_csv": has_f0(s['title']),
    })
for s in singles:
    rows.append({
        "title": s['title'], "source": "single", "album": s.get('album'),
        "low_note": (s.get('low_stable') or {}).get('note'), "low_hz": (s.get('low_stable') or {}).get('hz'),
        "high_note": (s.get('high_stable') or {}).get('note'), "high_hz": (s.get('high_stable') or {}).get('hz'),
        "span_octaves": s.get('span_octaves'), "note_count": s.get('note_count'),
        "density": s.get('note_density_per_s'), "stability_cents": s.get('stability_cents_median'),
        "intonation_cents": s.get('intonation_cents_median'),
        "vibrato_hz": s.get('vibrato_rate_hz_median'), "vibrato_cents": s.get('vibrato_extent_cents_median'),
        "hnr_db": s.get('hnr_db_median'), "register_share": s.get('register_share'),
        "duration_s": s.get('duration_s'), "rms_db": s.get('rms_db'), "centroid_hz": s.get('spectral_centroid_hz_median'),
        "f0_csv": has_f0(s['title']),
    })

out = {
    "schema": "studio_full/v1",
    "note": "录音室全量：专辑曲（72）+ 单曲/OST（83）；逐帧 F0 是否落盘用 f0_csv 标注",
    "counts": {"album": len(albums), "single": len(singles), "total": len(rows),
               "with_f0_csv": sum(1 for r in rows if r['f0_csv'])},
    "songs": rows,
}
p = ROOT / 'data' / 'studio_full.json'
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('合并', len(rows), '首｜有 F0 CSV', out['counts']['with_f0_csv'])
