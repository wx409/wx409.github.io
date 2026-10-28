#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按 songs_meta.json 派生 songs.html 的 title/description/JSON-LD 计数。

正文统计已在前端实时计算；这里只负责 <head> 与结构化数据里必须写死的数字。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
data = json.loads((ROOT / 'data' / 'songs_meta.json').read_text(encoding='utf-8'))['songs']
total = len(data)
lyr = sum(1 for s in data.values() if s.get('lyrics'))
alb = sum(1 for s in data.values() if s.get('album'))
live = sum(1 for s in data.values() if (s.get('show_count') or 0) > 0)

p = ROOT / 'songs.html'
s = p.read_text(encoding='utf-8')
s = re.sub(r'<title>[^<]*</title>', f'<title>王晰歌曲库 | {total}首 · 歌词/专辑/演唱记录</title>', s, count=1)
s = re.sub(r'(<meta name="description" content=")[^"]*(")',
           lambda m: f'{m.group(1)}王晰歌曲库：{total} 首歌曲元数据（{lyr} 首含歌词、{alb} 首有专辑关联、{live} 首有巡演演唱记录）。{m.group(2)}',
           s, count=1)
s = re.sub(r'(<meta property="og:title" content=")[^"]*(")', lambda m: f'{m.group(1)}王晰歌曲库 | {total}首{m.group(2)}', s, count=1)
s = re.sub(r'("description": ")[^"]*(")', lambda m: f'{m.group(1)}王晰作品歌曲库：{total} 首歌曲元数据，含歌词片段、专辑、发行与巡演演唱记录。{m.group(2)}', s, count=1)
p.write_text(s, encoding='utf-8')
print(f'songs.html 头部已更新：{total} 首 / 歌词 {lyr} / 专辑 {alb} / 巡演 {live}')
