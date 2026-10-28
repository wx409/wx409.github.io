#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取「王晰的小卡带」(uid 3788372265) 的现场音频分享帖 → 表格。

做法：
  1. 翻账号时间线（containerid=107603<uid>）
  2. 正文含"网盘/提取码/链接/资源/音频"的帖子，再抓评论（hotflow），找 pan.baidu.com 链接与提取码
  3. 输出 data/audio_shares.json + data/audio_shares.csv（可直接拿去下载）
"""
from __future__ import annotations

import csv
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import urllib.parse

sys.stdout.reconfigure(encoding='utf-8')
COOKIE = Path(r'E:\wx\私有工具\weibo_proxy\weibo_cookie.json')
ROOT = Path(r'D:\wx409.github.io')
UID = '3788372265'
OUT_JSON = ROOT / 'data' / 'audio_shares.json'
OUT_CSV = ROOT / 'data' / 'audio_shares.csv'

KEYS = ('网盘', '提取码', '链接', '资源', '音频', '录音', '无损', '下载', '分享')
PAN = re.compile(r'(https?://pan\.baidu\.com/s/[\w\-]+)')
CODE = re.compile(r'(?:提取码|密码|码)[：:\s]*([a-zA-Z0-9]{4})')


def pan_from_html(raw: str) -> str:
    """从微博 HTML 片段里解出真实网盘链接（含 sinaurl 跳转）。"""
    for h in re.findall(r'href="([^"]+)"', raw or ''):
        h = h.replace('&amp;', '&')
        if 'sinaurl' in h:
            q = urllib.parse.parse_qs(urllib.parse.urlparse(h).query)
            h = (q.get('u') or [''])[0]
        if 'pan.baidu.com' in h:
            return h
    m = re.search(r'https?://pan\.baidu\.com/s/[\w\-]+', raw or '')
    return m.group(0) if m else ''


def wb_date(s: str) -> str:
    try:
        return datetime.strptime(s, '%a %b %d %H:%M:%S %z %Y').strftime('%Y-%m-%d')
    except Exception:
        return ''


def main() -> None:
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    cookie = json.loads(COOKIE.read_text(encoding='utf-8')).get('cookie')
    S = requests.Session()
    S.headers.update({'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
                      'Referer': 'https://m.weibo.cn/', 'Cookie': cookie,
                      'X-Requested-With': 'XMLHttpRequest'})
    posts = []
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
            txt = re.sub('<[^>]+>', '', mb.get('text') or '')
            posts.append({"id": mb['id'], "date": wb_date(mb.get('created_at') or ''),
                          "text": txt})
            got += 1
        print(f'page {page}: {got}')
        if got == 0:
            break
        time.sleep(1.0)

    rows = []
    for p in posts:
        if not any(k in p['text'] for k in KEYS) and not PAN.search(p['text']):
            continue
        link_url = pan_from_html(p['text'])
        code = CODE.search(re.sub('<[^>]+>', '', p['text']))
        ctext = ''
        if not link_url:
            try:
                cu = (f'https://m.weibo.cn/comments/hotflow?id={p["id"]}&mid={p["id"]}'
                      f'&max_id_type=0')
                cd = S.get(cu, timeout=20).json()
                items = ((cd.get('data') or {}).get('data') or [])
                ctext = ' '.join((x.get('text') or '') for x in items)
            except Exception:
                pass
            link_url = pan_from_html(ctext)
            code = code or CODE.search(re.sub('<[^>]+>', '', ctext))
        rows.append({**p, "pan": link_url,
                     "code": code.group(1) if code else '',
                     "comment_hit": bool(link_url) if ctext else False})

    OUT_JSON.write_text(json.dumps({"schema": "audio_shares/v1", "uid": UID,
                                    "count": len(rows), "rows": rows},
                                   ensure_ascii=False, indent=1), encoding='utf-8')
    with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['日期', '微博ID', '百度网盘链接', '提取码', '正文摘要', '链接位置'])
        for r in rows:
            w.writerow([r['date'], r['id'], r['pan'], r['code'], r['text'][:60],
                        '评论' if r['comment_hit'] else ('正文' if r['pan'] else '')])
    print(f'候选分享帖 {len(rows)}｜带链接 {sum(1 for r in rows if r["pan"])}｜输出 {OUT_CSV}')


if __name__ == '__main__':
    main()
