#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 data/excluded_songs.json 剔除歌曲（生成后过滤，幂等）。

覆盖：指数大屏主库/仓库副本、tavern 精简曲表。
命中规则：uid 相同，或 name 相同/含别名。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
EXCL = ROOT / 'data' / 'excluded_songs.json'
TARGETS = [
    Path(r'E:\wx\index_records\dashboard\dashboard_data.json'),
    Path(r'E:\wx\index_records\dashboard\dashboard_lite.json'),
    ROOT / 'dashboard' / 'dashboard_data.json',
    ROOT / 'dashboard' / 'dashboard_lite.json',
    ROOT / 'tavern' / 'songs_compact.json',
]

d = json.loads(EXCL.read_text(encoding='utf-8'))
UIDS = {i['uid'] for i in d.get('items', []) if i.get('uid')}
NAMES = set()
for i in d.get('items', []):
    if i.get('name'):
        NAMES.add(i['name'].replace(' ', ''))
    for a in i.get('aliases', []) or []:
        NAMES.add(a.replace(' ', ''))


def match(o: dict) -> bool:
    if o.get('uid') in UIDS:
        return True
    for k in ('name', 'song', 'title', 'song_name', '曲目', '歌名'):
        v = o.get(k)
        if v is None:
            continue
        n = str(v).replace(' ', '')
        if n and any(x and x in n for x in NAMES):
            return True
    return False


def walk(o):
    if isinstance(o, dict):
        if match(o):
            return None
        return {k: walk(v) for k, v in o.items()}
    if isinstance(o, list):
        out = []
        for v in o:
            nv = walk(v)
            if nv is not None:
                out.append(nv)
        return out
    return o


total = 0
for p in TARGETS:
    if not p.exists():
        continue
    obj = json.loads(p.read_text(encoding='utf-8'))
    new = walk(obj)
    if new != obj:
        p.write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding='utf-8')
        total += 1
        print('已剔除:', p)
print('处理文件', total, '个')
