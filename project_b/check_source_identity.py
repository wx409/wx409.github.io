#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""40 段来源身份检查：目录/曲目/歌手是否属于王晰录音室曲库。

只查来源与元数据，不做任何 F0 测量。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
EXP = ROOT / 'data/research/experiments/exp-20261025-01'
albums = json.loads((ROOT / 'data/albums.json').read_text(encoding='utf-8'))
titles = {a.get('name') or a.get('title') for a in albums.get('albums', []) if (a.get('name') or a.get('title'))}
man = json.loads((EXP / 'segment_manifest.json').read_text(encoding='utf-8'))['items']

rows, ok, flagged, invalid = [], 0, [], []
for i in man:
    ident = i['identity']
    album = ident.split('/')[0] if '/' in ident else ident
    layer = i['layer']
    if layer == '录音室人声轨':
        if album == '赵鹏':
            state, why = 'invalid', '非目标歌手'
            invalid.append(i['segment_id'])
        elif album in titles:
            state, why = 'ok', '专辑在王晰曲库登记内'
            ok += 1
        elif album == '龙源之声':
            state, why = 'confirmed_by_listener', '听者确认为王晰《鸿雁》，元数据缺失'
            ok += 1
        else:
            state, why = 'unknown_album', '专辑未在王晰曲库登记'
            flagged.append(i['segment_id'])
    else:
        state, why = 'stage', '现场素材，按文件名标识'
    rows.append({"segment_id": i['segment_id'], "layer": layer, "identity": ident,
                 "album": album, "state": state, "note": why})

out = {"experiment_id": "exp-20261025-01", "status": "exploratory", "publishable": False,
       "checked": len(rows), "ok": ok, "invalid": invalid, "flagged": flagged,
       "rows": rows}
(EXP / 'source_identity_check.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(f"检查 {len(rows)} 段｜合格 {ok}｜无效 {invalid}｜待确认 {flagged}")
for r in rows:
    if r['state'] not in ('ok', 'stage'):
        print(' ', r['segment_id'], r['identity'], '->', r['state'])
