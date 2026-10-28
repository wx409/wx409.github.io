#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QQ 拿不到的单曲/OST → 网易云搜索取源（outer url 直链）→ 供声学实测。

来源清单：data/singles_inventory.json 中 has_mid 且本地无音频的曲目。
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
OUT = Path(r'E:\wx\论文素材_王晰作传\音域分析\网易云补_单曲')
OUT.mkdir(parents=True, exist_ok=True)
UA = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://music.163.com/'}


def search(name: str) -> list[dict]:
    url = 'https://music.163.com/api/search/get?s=' + urllib.parse.quote(f'王晰 {name}') + '&type=1&limit=8'
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.loads(r.read().decode('utf-8'))
    return ((d.get('result') or {}).get('songs') or [])


def main() -> None:
    inv = json.loads((ROOT / 'data' / 'singles_inventory.json').read_text(encoding='utf-8'))['rows']
    todo = [r for r in inv if not r['has_audio']]
    done = hit = miss = 0
    for r in todo:
        name = r['name']
        dst = OUT / f'{name}.mp3'
        if dst.exists() and dst.stat().st_size > 200_000:
            done += 1
            continue
        try:
            songs = search(name)
        except Exception as e:
            print('搜索失败', name, e); miss += 1; continue
        best = None
        for s in songs:
            singers = ' '.join(a.get('name', '') for a in (s.get('artists') or []))
            if '王晰' in singers:
                best = s
                break
        if not best:
            print('未命中', name); miss += 1; time.sleep(0.4); continue
        url = f"https://music.163.com/song/media/outer/url?id={best['id']}.mp3"
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            if len(data) < 200_000:
                print('取源过小', name, len(data)); miss += 1; continue
            dst.write_bytes(data)
            hit += 1
            print('OK', name, round(len(data) / 1e6, 1), 'MB')
        except Exception as e:
            print('下载失败', name, e); miss += 1
        time.sleep(0.5)
    print(f'完成：已存在 {done}｜新增 {hit}｜未命中/失败 {miss}')


if __name__ == '__main__':
    main()
