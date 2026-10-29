#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hot_hooks.py —— 抓热榜 → 生成「王晰可以怎么蹭」的选题钩子。

数据源（公开接口，无需登录）：
  · 抖音热榜  https://www.douyin.com/aweme/v1/web/hot/search/list/
  · 微博热搜  m.weibo.cn container 接口（带本地 cookie 更稳）

输出：data/hot_hooks.json（当天）＋ 控制台可读列表。
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
COOKIE = Path(r'E:\wx\私有工具\weibo_proxy\weibo_cookie.json')
OUT = ROOT / 'data' / 'hot_hooks.json'
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36',
      'Referer': 'https://www.douyin.com/'}

# 钩子模板：把热点套进王晰的四类题材
TEMPLATES = [
    ("反差", "「{hot}」很热闹，但你可能没注意：这个人唱歌时，音准五年没飘过 2 音分。"),
    ("挑战", "普通人试唱「{hot}」里那种低音，90% 会掉八度——他唱的是 B1。"),
    ("怀旧", "「{hot}」刷屏这天，想起他 2019 年在巡演台上唱的那句低音。"),
    ("技术", "从「{hot}」聊到唱功：什么叫「换气藏在伴奏里」——波形上只低 12–20 dB。"),
    ("歌", "如果「{hot}」需要一首配乐，我会投《火光》：4.4 音分的稳定，像一条直线。"),
]


def douyin() -> list[str]:
    try:
        r = requests.get('https://www.douyin.com/aweme/v1/web/hot/search/list/?device_platform=webapp'
                         '&aid=6383&channel=channel_pc_web&detail_list=1', headers=UA, timeout=20)
        ws = (r.json().get('data') or {}).get('word_list') or []
        return [w.get('word') for w in ws if w.get('word')][:30]
    except Exception:
        return []


def weibo() -> list[str]:
    try:
        ck = json.loads(COOKIE.read_text(encoding='utf-8')).get('cookie') if COOKIE.exists() else ''
        h = {'User-Agent': 'Mozilla/5.0', 'Cookie': ck, 'Referer': 'https://m.weibo.cn/'}
        r = requests.get('https://m.weibo.cn/api/container/getIndex?containerid='
                         '106003type%3D25%26t%3D3%26disable_hot%3D1%26filter_type%3Drealtimehot',
                         headers=h, timeout=20)
        cards = (r.json().get('data') or {}).get('cards') or []
        items = (cards[0].get('card_group') or []) if cards else []
        return [i.get('desc') for i in items if i.get('desc')][:30]
    except Exception:
        return []


# 只保留「娱乐/生活/文化」类热点，过滤时政军事体育
DROP = re.compile(r'公报|全会|国防部|外交部|军委|纪委|党建|党员|中央|国务院|发布会|简历|军演|'
                  r'世界杯|足球|女足|男足|篮球|NBA|CBA|联赛|奥运|亚运|夺冠|金牌|'
                  r'股价|股市|人民币|央行|经济|政策|条例|法案|处罚')
KEEP = re.compile(r'歌|唱|音乐|专辑|单曲|舞台|演唱会|巡演|晚会|剧|综艺|电影|声音|配音|歌手|'
                  r'演员|明星|热搜|恋爱|结婚|离婚|生日|怀旧|回忆|青春|治愈|深夜|职场|'
                  r'城市|旅行|美食|穿搭|生活|情绪')


def pick(hots, limit=8):
    out = []
    for h in hots:
        if DROP.search(h) or not KEEP.search(h):
            continue
        out.append(h)
        if len(out) >= limit:
            break
    return out


def main() -> None:
    dy, wb = douyin(), weibo()
    hots = pick(dy, 8) + pick(wb, 8)
    hooks = []
    for i, hot in enumerate(hots):
        tpl = TEMPLATES[i % len(TEMPLATES)]
        hooks.append({"hot": hot, "type": tpl[0], "hook": tpl[1].format(hot=hot)})
    OUT.write_text(json.dumps({"date": date.today().isoformat(), "douyin": dy, "weibo": wb,
                               "hooks": hooks}, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'抖音 {len(dy)}｜微博 {len(wb)}｜钩子 {len(hooks)}')
    for h in hooks[:8]:
        print(f"  [{h['type']}] 热点「{h['hot']}」→ {h['hook'][:60]}...")


if __name__ == '__main__':
    main()
