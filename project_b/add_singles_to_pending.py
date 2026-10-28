#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 49 首正式发行单曲/OST 加入 待测清单.json（供下载与分析）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
INV = Path(r'D:\wx409.github.io\data\singles_inventory.json')
PL = Path(r'E:\wx\论文素材_王晰作传\音域分析\待测清单.json')

inv = json.loads(INV.read_text(encoding='utf-8'))['rows']
pl = json.loads(PL.read_text(encoding='utf-8'))
have = {(x.get('title') or '').strip() for x in pl['items']}
added = 0
for r in inv:
    if not r['has_mid'] or r['has_audio'] or r['name'] in have:
        continue
    pl['items'].append({
        "album": "正式发行单曲/OST",
        "title": r['name'],
        "mid": r['mid'],
        "note": f"发行 {r['release']}｜{r['content'][:20]}",
    })
    added += 1
PL.write_text(json.dumps(pl, ensure_ascii=False, indent=1), encoding='utf-8')
print('已加入待测清单', added, '首；总条目', len(pl['items']))
