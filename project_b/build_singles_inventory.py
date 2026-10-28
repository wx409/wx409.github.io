#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""正式发行单曲 / OST 清单：有没有 mid、有没有本地音频、是否已分析。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
XLSX = Path(r'E:\wx\index_records\王晰歌曲信息汇总.xlsx')
SITE = Path(r'D:\wx409.github.io')
OUT = SITE / 'data' / 'singles_inventory.json'

x = pd.read_excel(XLSX, sheet_name='OST&单曲')
sm = json.loads((SITE / 'data' / 'songs_meta.json').read_text(encoding='utf-8'))['songs']
albums = json.loads((SITE / 'data' / 'albums.json').read_text(encoding='utf-8'))
album_songs = {(s.get('title') or '').strip() for a in albums['albums'] for s in (a.get('songs') or [])}

# 本地音频索引
audio_roots = [Path(r'E:\wx\论文素材_王晰作传\专辑音频'), Path(r'E:\wx\论文素材_王晰作传\音域分析\专辑音频')]
audio_names = set()
for r in audio_roots:
    if r.exists():
        for f in r.rglob('*'):
            if f.suffix.lower() in ('.mp3', '.flac', '.wav', '.m4a'):
                audio_names.add(f.stem)

rows = []
for _, r in x.iterrows():
    name = str(r.get('歌名') or '').strip()
    if not name or name == 'nan':
        continue
    dt = pd.to_datetime(r.get('发行时间'), errors='coerce')
    rec = sm.get(name) or {}
    rows.append({
        "name": name,
        "release": dt.strftime('%Y-%m-%d') if pd.notna(dt) else '',
        "content": str(r.get('内容') or '').strip(),
        "has_mid": bool(rec.get('mid')),
        "mid": rec.get('mid') or '',
        "has_audio": name in audio_names,
        "in_albums": name in album_songs,
    })

OUT.write_text(json.dumps({"schema": "singles_inventory/v1", "count": len(rows),
                           "rows": rows}, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'单曲/OST {len(rows)} 条')
print(f'  有 mid  {sum(1 for r in rows if r["has_mid"])}')
print(f'  有音频  {sum(1 for r in rows if r["has_audio"])}')
print(f'  在专辑  {sum(1 for r in rows if r["in_albums"])}')
print(f'  可下载  {sum(1 for r in rows if r["has_mid"] and not r["has_audio"])}')
