#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""登记新歌《火光》完整信息：发行日、制作名单、歌词、时间轴。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
D = Path(r'D:\wx409.github.io\data')

LYRICS = """弥漫的尘埃
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
化作火光无悔这一场
那是关于你 关于你
笃定这一程悲欢
不会再孤身一人上岸
都是关于你 关于你
一路冲破了黑暗
撕裂腐朽 不羁的勇敢
谁能阻挡
在命运的废墟之上
披上不可一世的装
做彼此的信仰 对峙绝望
向前闯
捍卫尊严的力量
让畏惧溃败给倔强
燃尽了血泪 也要
化作火光无悔这一场
谁能阻挡
在命运的废墟之上
披上不可一世的装
做彼此的信仰 对峙绝望
向前闯
捍卫尊严的力量
让畏惧溃败给倔强
燃尽了血泪 也要
化作火光无悔这一场""".splitlines()

CREDITS = {
    "发行时间": "2026-10-27",
    "制作人": "Bryan (孙伟)",
    "曲": "Bryan (孙伟)",
    "词": "Bryan (孙伟)",
    "编曲": "刘苏毅@U.M.C",
    "吉他/贝斯": "刘苏毅@U.M.C",
    "配唱制作人": "胡宸@U.M.C",
    "和声": "海青",
    "制作统筹": "胡宸@U.M.C",
    "混音/母带": "王路遥",
    "音乐制作": "The U.M.C",
    "人声录音": "吕自雯",
    "录音棚": "韶愔音乐 Studio",
    "总监制": "王锋",
    "音乐总监": "丁爽",
    "OP": "韶愔音乐娱乐 (北京)有限公司",
    "音乐出品发行": "韶愔音乐娱乐 (北京)有限公司",
}

# 1) songs_meta
p = D / 'songs_meta.json'
raw = json.loads(p.read_text(encoding='utf-8'))
sm = raw['songs']
song = sm.get('火光') if '火光' in sm else None
if song is None:
    for k, v in sm.items():
        if isinstance(v, dict) and v.get('name') == '火光':
            song = v
            break
assert song is not None, 'songs_meta 里找不到 火光'
song['release'] = '2026-10-27'
song['album'] = '火光'
song['single'] = True
song['credits'] = CREDITS
song['lyrics'] = [{"text": line, "moods": []} for line in LYRICS if line.strip()]
song['lyrics_source'] = '用户提供的官方文案（2026-10-27 发行）'
raw['songs'] = sm
p.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding='utf-8')
print('songs_meta 已更新：release=2026-10-27，含制作名单与歌词')

# 2) timeline
t = D / 'timeline.json'
tl = json.loads(t.read_text(encoding='utf-8'))
hit = False
for e in tl:
    if '火光' in e.get('title', ''):
        e['date'] = '2026-10-27'
        e['title'] = '新歌《火光》发行（单曲）'
        e['source'] = '官方发行信息（用户提供）：制作 The U.M.C / 出品 韶愔音乐娱乐'
        hit = True
if not hit:
    tl.append({"date": "2026-10-27", "type": "album", "title": "新歌《火光》发行（单曲）",
               "source": "官方发行信息（用户提供）", "stage": "发行"})
tl.sort(key=lambda e: e.get('date', ''))
t.write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding='utf-8')
print('时间轴已更新为 2026-10-27')
