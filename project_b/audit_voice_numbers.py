#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""voice.html 数字一致性体检：页面关键数字 vs 数据源。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
page = (ROOT / 'voice.html').read_text(encoding='utf-8')
text = re.sub(r'<script.*?</script>', ' ', page, flags=re.S)
text = re.sub(r'<[^>]+>', ' ', text)
text = re.sub(r'\s+', ' ', text)

v = json.loads((ROOT / 'data' / 'archive_vocal.json').read_text(encoding='utf-8'))
alb = json.loads((ROOT / 'data' / 'archive_vocal_albums.json').read_text(encoding='utf-8'))
s = alb['summary']
sel = v['count']
b1_sel = v['conclusion']['b1_count']
b1_alb = len(v['conclusion']['album_b1_songs'])

checks = [
    ('72 曲全量', f"{s['songs']} 曲", f"{s['songs']} 曲" in text or f"{s['songs']} 首" in text),
    ('精测层曲数', str(sel), f"{sel} 曲" in text or f"{sel} 首" in text),
    ('最低音', f"{s['lowest']['note']} {s['lowest']['hz']}Hz", f"{s['lowest']['hz']}" in text),
    ('最高稳定音', f"{s['highest']['hz']}Hz", f"{s['highest']['hz']}" in text),
    ('跨度中位', str(s['span_median_octaves']), str(s['span_median_octaves']) in text),
    ('稳定性中位', str(s['stability_cents_median']), str(s['stability_cents_median']) in text),
    ('颤音', str(s['vibrato_rate_hz_median']), str(s['vibrato_rate_hz_median']) in text),
    ('精测层 B1 数', str(b1_sel), f"{b1_sel} 首" in text),
    ('全量层 B1 数', str(b1_alb), f"{b1_alb} 首" in text),
    ('主区上界', '75.5', '75.5' in text),
    ('男低音下限', '82.4', '82.4' in text),
]
bad = 0
for name, expect, ok in checks:
    print(('✅' if ok else '❌'), name, '=', expect)
    bad += 0 if ok else 1
print(f'\n不一致 {bad} 项')
