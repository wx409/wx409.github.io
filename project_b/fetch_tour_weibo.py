#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取「王晰个人巡回音乐会」微博（uid 7091660310）并归档。

该号主要发布乐华系个人巡演/音乐会信息，含历史场次，是巡演信息的主要来源。
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding='utf-8')
COOKIE = Path(r'E:\wx\私有工具\weibo_proxy\weibo_cookie.json')
OUT = Path(r'E:\wx\私有工具\weibo_archive_tour\posts')
UID = '7091660310'


def wb_date(s: str) -> str:
    try:
        return datetime.strptime(s, '%a %b %d %H:%M:%S %z %Y').strftime('%Y-%m-%d')
    except Exception:
        return ''


def main() -> None:
    cookie = json.loads(COOKIE.read_text(encoding='utf-8')).get('cookie')
    S = requests.Session()
    S.headers.update({'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
                      'Referer': 'https://m.weibo.cn/', 'Cookie': cookie,
                      'X-Requested-With': 'XMLHttpRequest'})
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    saved = 0
    for page in range(1, max_pages + 1):
        url = (f'https://m.weibo.cn/api/container/getIndex?type=uid&value={UID}'
               f'&containerid=107603{UID}&page={page}')
        try:
            d = S.get(url, timeout=25).json()
        except Exception as e:
            print('page', page, '失败', e)
            break
        cards = (d.get('data') or {}).get('cards') or []
        got = 0
        for c in cards:
            mb = c.get('mblog') or {}
            if not mb.get('id'):
                continue
            day = wb_date(mb.get('created_at') or '')
            if not day:
                continue
            txt = re.sub('<[^>]+>', '', mb.get('text') or '')
            rec = {"id": mb['id'], "uid": UID, "date": day, "text": txt,
                   "screen_name": (mb.get('user') or {}).get('screen_name'),
                   "pics": [p.get('url') for p in (mb.get('pics') or [])],
                   "source": "王晰个人巡回音乐会 微博"}
            sub = OUT / day[:4] / day[:7]
            sub.mkdir(parents=True, exist_ok=True)
            f = sub / f'{mb["id"]}.json'
            if not f.exists():
                f.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding='utf-8')
                saved += 1
            got += 1
        print(f'page {page}: {got} 条（新增 {saved}）')
        if got == 0:
            break
        time.sleep(1.2)
    print('完成，新增归档', saved, '->', OUT)


if __name__ == '__main__':
    main()
