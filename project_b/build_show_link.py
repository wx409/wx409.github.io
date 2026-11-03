#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""长表回连：把 37 场现场素材 + 43 曲精测层的现场记录，挂到唯一长表的 巡次/日期/场次。

输出 data/show_link.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
LONG = r'E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx'
STAGE = Path(r'E:\wx\论文素材_王晰作传\_staging_现场')

df = pd.read_excel(LONG, sheet_name='合并长表')
df['日期_s'] = pd.to_datetime(df['日期'], errors='coerce').dt.strftime('%Y-%m-%d')
shows = (df.groupby(['日期_s', '场次', '巡次'])
           .agg(songs=('曲目', lambda x: sorted(set(x.dropna().astype(str)))))
           .reset_index())

# 1) staging 专辑 → 长表场次
staging = []
for d in sorted(STAGE.iterdir()):
    if not d.is_dir() or not re.match(r'^s\d+_', d.name):
        continue
    date = d.name.split('_')[1]
    date_fmt = f'{date[:4]}-{date[4:6]}-{date[6:]}'
    hit = shows[shows['日期_s'] == date_fmt]
    staging.append({
        "album": d.name, "date": date_fmt,
        "matched": bool(len(hit)),
        "show": hit.iloc[0]['场次'] if len(hit) else None,
        "tour": hit.iloc[0]['巡次'] if len(hit) else None,
    })

# 2) 精测层里的现场证据串 → 场次（按日期关键词）
vocal = json.loads((ROOT / 'data' / 'archive_vocal.json').read_text(encoding='utf-8'))
EV_RE = re.compile(r'(20\d{2})[.\-年]?(\d{1,2})?')

out = {
    "schema": "show_link/v1",
    "source": "王晰巡演歌单长表_单一事实源.xlsx / 合并长表",
    "shows": [{"date": r['日期_s'], "show": r['场次'], "tour": r['巡次'], "n_songs": len(r['songs'])}
              for _, r in shows.iterrows()],
    "staging": staging,
}
(ROOT / 'data' / 'show_link.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
ok = sum(1 for s in staging if s['matched'])
print(f'长表场次 {len(shows)}｜staging {len(staging)} 场，回连成功 {ok}')
for s in staging[:5]:
    print('  ', s['album'], '→', s['show'], s['tour'])
