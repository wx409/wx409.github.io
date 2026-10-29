#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并：37 场两轨初筛 + 录音笔/六轨高质量素材，按同曲取最优，输出排行榜。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
RANK = ROOT / 'data' / 'research' / 'live_long_phrase_rank.json'
EXTRA = ROOT / 'temp' / 'long_phrase_extra.json'
OUT = ROOT / 'data' / 'research' / 'live_long_phrase_final.json'

rank = json.loads(RANK.read_text(encoding='utf-8'))['rows'] if RANK.exists() else []
extra = json.loads(EXTRA.read_text(encoding='utf-8')) if EXTRA.exists() else []
for r in rank:
    r['source'] = r.get('source', 'two-stem')
    r['verified'] = False
for r in extra:
    r['verified'] = True

# 同曲去重：优先 verified（录音笔/六轨）
by_song = {}
for r in rank + extra:
    key = (r['song'][:20], r['show'][:12])
    if key not in by_song or (r.get('verified') and not by_song[key].get('verified')):
        by_song[key] = r
rows = sorted(by_song.values(), key=lambda r: -r['dur'])
OUT.write_text(json.dumps({"schema": "live_long_phrase_final/v1", "count": len(rows),
                           "note": "两轨结果需六轨复核；录音笔/六轨结果视为已核",
                           "rows": rows[:50]}, ensure_ascii=False, indent=1), encoding='utf-8')
print('合并后', len(rows), '条｜前 10：')
for r in rows[:10]:
    print(f"  {r['dur']:6.2f}s｜{r['show'][:22]:22s}｜{r['song'][:18]:18s}｜{'已核' if r.get('verified') else '待核'}")
