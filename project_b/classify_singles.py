#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单曲/OST/宣传曲/合唱 分类（读歌曲信息汇总 + QQ 演唱者）。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import openpyxl

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
XLSX = r'E:\wx\index_records\王晰歌曲信息汇总.xlsx'

wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
ws = wb['OST&单曲'] if 'OST&单曲' in wb.sheetnames else wb.active
rows = list(ws.iter_rows(values_only=True))
hdr, body = rows[0], rows[1:]
idx = {str(h): i for i, h in enumerate(hdr) if h}

meta = {}
for r in body:
    name = r[idx.get('歌名', 2)]
    if not name:
        continue
    content = str(r[idx.get('内容', 4)] or '')
    date = r[idx.get('发行时间', 3)]
    meta[str(name).strip()] = {
        "date": str(date)[:10] if date else None,
        "content": content,
    }

qq = json.loads((ROOT / 'data' / 'qq_singer_songs.json').read_text(encoding='utf-8'))['songs']
singers = {}
for s in qq:
    singers.setdefault(s['name'], s.get('singers') or '')

OST_KEYS = ('电视剧', '网剧', '电影', '动画', '动漫', '插曲', '片尾', '片头', '主题曲', '原声')
PROMO_KEYS = ('宣传', '推广', '公益', '活动', '亚运', '运动会', '主题推广', '晚会')


def classify(title: str) -> str:
    sg = singers.get(title, '')
    names = [x for x in sg.replace('／', '/').split('/') if x.strip()]
    if len(names) > 1:
        return '合唱'
    c = meta.get(title, {}).get('content', '')
    if any(k in c for k in PROMO_KEYS):
        return '宣传/公益'
    if any(k in c for k in OST_KEYS):
        return '影视OST'
    return '正式单曲'


songs = json.loads((ROOT / 'data' / 'studio_full.json').read_text(encoding='utf-8'))['songs']
for s in songs:
    s['category'] = classify(s['title'])
    s['release'] = meta.get(s['title'], {}).get('date')
    s['singers'] = singers.get(s['title'], '')

from collections import Counter
cnt = Counter(s['category'] for s in songs if s['source'] == 'single')
out = {
    "schema": "singles_category/v1",
    "counts": dict(cnt),
    "songs": [{"title": s['title'], "category": s['category'], "release": s['release'],
               "singers": s['singers']} for s in songs if s['source'] == 'single'],
}
(ROOT / 'data' / 'singles_category.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('单曲分类', dict(cnt))
for k in cnt:
    ex = [x['title'] for x in out['songs'] if x['category'] == k][:6]
    print(' ', k, '→', '、'.join(ex))
