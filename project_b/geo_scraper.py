#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B项目：GEO 内容抓取（CSV/TXT 链接导入）"""

import csv
import json
from datetime import datetime
from pathlib import Path

from project_b.geo_common import RAW_GEO
from utils import bocha_search, log, log_success, log_error

DEFAULT_CSV = Path('/mnt/d/wx409.github.io/data/links.csv')


def _read_csv(path):
    items = []
    with open(path, 'r', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if not any(row.values()):
                continue
            clean = {k.strip(): (v or '').strip() for k, v in row.items() if k}
            url = clean.get('url', '')
            if url.startswith('http'):
                items.append({
                    'platform': clean.get('platform', 'unknown'),
                    'url': url,
                    'title': clean.get('title', '无标题'),
                    'summary': clean.get('summary', ''),
                    'author': clean.get('author', ''),
                    'date': clean.get('date', ''),
                    'tags': [t.strip() for t in clean.get('tags', '').replace(';', ',').split(',') if t.strip()],
                    'source_file': path.name,
                })
    return items


def _read_url_list(path):
    items = []
    for line in path.read_text(encoding='utf-8').splitlines():
        url = line.strip()
        if url.startswith('http'):
            items.append({
                'platform': 'unknown',
                'url': url,
                'title': '',
                'summary': '',
                'author': '',
                'date': '',
                'tags': [],
                'source_file': path.name,
            })
    return items


def run_scrape(platform=None, input_path=None):
    """从 CSV 或 URL 列表抓取/导入 GEO 素材"""
    src = Path(input_path) if input_path else DEFAULT_CSV
    if not src.exists():
        log_error(f'输入文件不存在: {src}', 'B')
        return None

    log(f'GEO 抓取: {src.name}' + (f' | 平台={platform}' if platform else ''), 'B')
    if src.suffix.lower() == '.csv':
        items = _read_csv(src)
    else:
        items = _read_url_list(src)

    if platform:
        items = [i for i in items if i['platform'] == platform]

    if not items:
        log_error('未找到有效链接', 'B')
        return None

    enriched = 0
    for item in items:
        if not item['title'] or not item['summary']:
            query = item['title'] or item['url']
            if query and not query.startswith('http'):
                results = bocha_search(query, count=3, freshness='oneYear')
            elif item['title']:
                results = bocha_search(item['title'], count=3, freshness='oneYear')
            else:
                results = []
            if results:
                r = results[0]
                item['title'] = item['title'] or r['title']
                item['summary'] = item['summary'] or r['snippet']
                item['date'] = item['date'] or r['date']
                enriched += 1

    today = datetime.now().strftime('%Y%m%d_%H%M')
    out = RAW_GEO / f'raw_{today}.json'
    payload = {
        'scraped_at': datetime.now().isoformat(),
        'platform_filter': platform,
        'source': str(src),
        'count': len(items),
        'items': items,
    }
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    log_success(f'抓取 {len(items)} 条（博查补全 {enriched} 条）→ {out}', 'B')
    return out
