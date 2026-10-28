#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""【已停用】原意：把 albums.json 全文歌词同步到 songs_meta。

停用原因：songs_meta 只允许存歌词片段（版权口径，见 build_songs_meta.py 注释）；
全文歌词不得进入公开 JSON。保留脚本仅作记录，默认不执行。

背景：歌词长期只存在 albums.json，songs_meta 的 lyrics 字段几乎为空，
导致 songs.html 显示“42 首含歌词”且新歌无歌词。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
D = Path(r'D:\wx409.github.io\data')
albums = json.loads((D / 'albums.json').read_text(encoding='utf-8'))
raw = json.loads((D / 'songs_meta.json').read_text(encoding='utf-8'))
songs = raw['songs']

# 火光歌词（用户提供）
HUOGUANG = """弥漫的尘埃
无法掩盖 你的存在
烈火 迎面袭来
冲破硝烟沾染过后的阴霾
那是关于你 关于你
笃定这一程悲欢
不会再孤身一人上岸
都是关于你 关于你
一路冲破了黑暗
撕裂腐朽不羁的勇敢
谁能阻挡
在命运的废墟之上
披上不可一世的装
做彼此的信仰 对峙绝望
向前闯
捍卫尊严的力量
让畏惧溃败给倔强
燃尽了血泪 也要
化作火光无悔这一场"""

added_lyrics = 0
added_credits = 0
for a in albums.get('albums', []):
    for s in (a.get('songs') or []):
        title = (s.get('title') or '').strip()
        if not title:
            continue
        rec = songs.get(title)
        if rec is None:
            continue
        lyr = s.get('lyrics') or []
        if lyr and not rec.get('lyrics'):
            rec['lyrics'] = lyr
            added_lyrics += 1
        if s.get('credits') and not rec.get('credits'):
            rec['credits'] = s['credits']
            added_credits += 1

# 火光：若 albums 里没有歌词，用内置文本补齐，并回写 albums
if '火光' in songs and not songs['火光'].get('lyrics'):
    songs['火光']['lyrics'] = [{"text": x, "moods": []} for x in HUOGUANG.splitlines() if x.strip()]
    for a in albums.get('albums', []):
        for s in (a.get('songs') or []):
            if (s.get('title') or '') == '火光' and not s.get('lyrics'):
                s['lyrics'] = songs['火光']['lyrics']
                (D / 'albums.json').write_text(json.dumps(albums, ensure_ascii=False, indent=1), encoding='utf-8')

raw['songs'] = songs
(D / 'songs_meta.json').write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding='utf-8')
have = sum(1 for v in songs.values() if v.get('lyrics'))
print(f'同步歌词 {added_lyrics} 首｜同步制作名单 {added_credits} 首｜现有歌词曲目 {have}/{len(songs)}')
