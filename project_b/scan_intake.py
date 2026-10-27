#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""官宣扫描 → 候选箱：只收集，不自动入库。

数据源（默认两个都扫）：
  · weibo_search：微博关键词搜索「王晰」（能拿到比账号更早的路人/粉丝动态）
  · weibo_archive：工作室微博本地归档（兜底）

规则：
  · 命中官宣类关键词（新歌/单曲/发行/上线/官宣/开票/预售/首演/定档）
  · 排除直拍/花絮/返图/转发等噪声
  · 与 timeline、候选箱去重
  · 只写 pending，必须人工确认
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
INBOX = ROOT / 'data' / 'intake_inbox.json'
TIMELINE = ROOT / 'data' / 'timeline.json'
ARCHIVE = Path(r'E:\wx\私有工具\weibo_archive_studio\posts')
COOKIE = Path(r'E:\wx\私有工具\weibo_proxy\weibo_cookie.json')

KEYS = ('新歌', '单曲', '发行', '上线', '官宣', '开票', '预售', '首演', '定档')
NOISE = ('直拍', '花絮', '返图', '转发', '后台', '排练', '混剪')
# 官方账号：命中官宣词即自动入库，不用人工确认
OFFICIAL_UIDS = {1292815744: '王晰本人', 7215995153: '王晰工作室'}


def parse_wb_date(s: str) -> str:
    try:
        return datetime.strptime(s, '%a %b %d %H:%M:%S %z %Y').strftime('%Y-%m-%d')
    except Exception:
        return ''


def fetch_weibo_search(days: int, max_pages: int = 3):
    import urllib.parse
    import requests
    if not COOKIE.exists():
        print('无 cookie，跳过微博搜索')
        return []
    cookie = json.loads(COOKIE.read_text(encoding='utf-8')).get('cookie')
    S = requests.Session()
    S.headers.update({'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
                      'Referer': 'https://m.weibo.cn/', 'Cookie': cookie,
                      'X-Requested-With': 'XMLHttpRequest'})
    since = (date.today() - timedelta(days=days)).isoformat()
    out = []
    q = urllib.parse.quote('王晰')
    for page in range(1, max_pages + 1):
        url = (f'https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D{q}'
               f'&page_type=searchall&page={page}')
        try:
            r = S.get(url, timeout=25)
            d = r.json()
        except Exception as e:
            print('搜索失败:', e)
            break
        cards = (d.get('data') or {}).get('cards') or []
        got = 0
        for c in cards:
            for g in (c.get('card_group') or []):
                mb = g.get('mblog') or {}
                txt = re.sub('<[^>]+>', '', mb.get('text') or '')
                day = parse_wb_date(mb.get('created_at') or '')
                if not txt or not day or day < since:
                    continue
                got += 1
                out.append({"date": day, "text": txt, "id": mb.get('id'),
                            "uid": (mb.get("user") or {}).get("id")})
        if got == 0:
            break
    return out


def fetch_archive(days: int):
    since = (date.today() - timedelta(days=days)).isoformat()
    out = []
    if not ARCHIVE.exists():
        return out
    for f in sorted(ARCHIVE.glob('*/*/*.json')):
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except Exception:
            continue
        day = str(d.get('date') or '')
        if day and day >= since and d.get('text'):
            out.append({"date": day, "text": d['text'], "id": d.get('id')})
    return out


RELEASE_KEYS = ('新歌', '单曲', '发行', '上线')
SHOW_KEYS = ('巡演', '音乐会', '开票', '首演', '剧场', '演出')
MATERIAL_KEYS = ('直拍', '花絮', '返图', '后台', '排练')


def classify_content(text: str) -> str:
    """内容性质分流：release / show / material / other。"""
    if any(k in text for k in MATERIAL_KEYS):
        return 'material'
    if any(k in text for k in RELEASE_KEYS):
        return 'release'
    if any(k in text for k in SHOW_KEYS):
        return 'show'
    return 'other'


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=7)
    ap.add_argument('--source', default='both', choices=['weibo_search', 'weibo_archive', 'both'])
    args = ap.parse_args()

    inbox = json.loads(INBOX.read_text(encoding='utf-8')) if INBOX.exists() else {"schema": "intake_inbox/v1", "items": []}
    timeline = json.loads(TIMELINE.read_text(encoding='utf-8'))
    seen = " ".join(e.get('title', '') for e in timeline) + " " + " ".join(x.get('title', '') for x in inbox['items'])

    # 已知作品/活动名（去书名号），命中即视为“旧事重提”，不再入箱
    import re as _re
    known = set()
    for e in timeline:
        t = e.get('title', '')
        for m in _re.findall(r'《([^》]{2,12})》', t):
            known.add(m)
        for tok in ('火光', '长城长', '草原之夜', '沉响与长歌'):
            if tok in t:
                known.add(tok)

    posts = []
    if args.source in ('weibo_search', 'both'):
        posts += fetch_weibo_search(args.days)
    if args.source in ('weibo_archive', 'both'):
        posts += fetch_archive(args.days)

    added = 0
    for p in posts:
        txt = p['text']
        if not any(k in txt for k in KEYS) or any(nk in txt for nk in NOISE):
            continue
        title = txt[:40].replace('\n', ' ')
        if title[:12] in seen:
            continue
        if any(k in txt for k in known):
            continue
        nid = f"c{len(inbox['items'])+1:03d}"
        official = p.get('uid') in OFFICIAL_UIDS
        kind = classify_content(txt)
        if kind == 'material':
            continue
        # 只有"新歌发行"这类可结构化落点，才允许官方源自动写时间轴；
        # 演出/剧目需要场馆、场次、卡司等字段，走现有管道（add_show），仍进候选箱。
        if official and kind == 'release':
            tl = json.loads(TIMELINE.read_text(encoding='utf-8'))
            tl.append({"date": p['date'], "type": "album",
                       "title": f"新歌发行：{title[:36]}",
                       "source": f"{OFFICIAL_UIDS[p['uid']]}微博 {p.get('id')}",
                       "stage": "发行"})
            tl.sort(key=lambda e: e.get('date', ''))
            TIMELINE.write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding='utf-8')
        inbox['items'].append({
            "id": nid, "kind": "activity", "title": title, "date": p['date'],
            "city": "", "source": f"微博搜索/归档 {p.get('id')}",
            "note": txt[:120], "status": "pending",
            "detected_at": date.today().isoformat(),
            "matched": [k for k in KEYS if k in txt],
        })
        seen += " " + title[:12]
        added += 1
    INBOX.write_text(json.dumps(inbox, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"扫描 {args.source} 近 {args.days} 天：帖子 {len(posts)}｜新增候选 {added}｜候选总数 {len(inbox['items'])}")


if __name__ == '__main__':
    main()
