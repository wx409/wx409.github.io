#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 albums.json 的完整歌词移出公开目录（方案 1），只留元数据。

- 私有留存：E:\\wx\\论文素材_王晰作传\\歌词_私有\\albums_lyrics.json（不入 git）
- 公开 albums.json：删除 songs[].lyrics，保留其余字段
- 生成对照：每首歌仍有 lyric_frags（片段）在 songs_meta
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
SITE = Path(r'D:\wx409.github.io')
PRIV = Path(r'E:\wx\论文素材_王晰作传\歌词_私有')
PRIV.mkdir(parents=True, exist_ok=True)

alb = json.loads((SITE / 'data' / 'albums.json').read_text(encoding='utf-8'))
store = {"schema": "albums_lyrics_private/v1",
         "note": "完整歌词私有留存；公开目录只留元数据。禁止进入 git 或站点。",
         "exported_at": datetime.now().isoformat(timespec='seconds'),
         "albums": []}
moved = 0
for a in alb.get('albums', []):
    songs = []
    for s in (a.get('songs') or []):
        if s.get('lyrics'):
            songs.append({"title": s.get('title'), "lyrics": s['lyrics']})
            s.pop('lyrics', None)
            moved += 1
    if songs:
        store['albums'].append({"name": a.get('name'), "songs": songs})

(PRIV / 'albums_lyrics.json').write_text(
    json.dumps(store, ensure_ascii=False, indent=1), encoding='utf-8')
(SITE / 'data' / 'albums.json').write_text(
    json.dumps(alb, ensure_ascii=False, indent=1), encoding='utf-8')
print(f'移出完整歌词 {moved} 首 -> {PRIV / "albums_lyrics.json"}')
print('公开 albums.json 剩余 lyrics 字段:',
      sum(1 for a in alb['albums'] for s in (a.get('songs') or []) if s.get('lyrics')))
