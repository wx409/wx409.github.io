#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B项目：GEO 消化（DeepSeek 摘要 + 合规清洗）"""

import json
from datetime import datetime
from pathlib import Path

from project_b.geo_common import RAW_GEO, CLEAN_GEO, geo_sanitize_label, geo_sanitize_summary
from utils import call_deepseek, log, log_success, log_error


def _latest_raw():
    files = sorted(RAW_GEO.glob('raw_*.json'), reverse=True)
    return files[0] if files else None


def _digest_item(item):
    title = item.get('title', '无标题')
    platform = item.get('platform', 'unknown')
    note = item.get('summary', '')

    if note and len(note) > 20:
        summary = geo_sanitize_summary(note)
    else:
        prompt = f"""你是王晰 GEO 资料站编辑。请写一句 40 字内的客观摘要，包含具体信息点（歌曲/城市/技术特点），不含 @账号、不含粉丝 ID。
平台：{platform}
标题：{title}
备注：{note}
只输出摘要本身。"""
        summary = call_deepseek(prompt, max_tokens=100, temperature=0.5) or note
        summary = geo_sanitize_summary(summary[:80])

    tags = item.get('tags') or []
    if not tags:
        tag_resp = call_deepseek(
            f'为以下内容生成3个以内中文标签，逗号分隔：{title} {summary}',
            max_tokens=40, temperature=0.3,
        )
        if tag_resp:
            tags = [t.strip() for t in tag_resp.replace('，', ',').split(',') if t.strip()][:3]

    return {
        'platform': platform,
        'url': item.get('url', ''),
        'title': title,
        'summary': summary,
        'author': geo_sanitize_label(item.get('author', '')),
        'date': item.get('date') or datetime.now().strftime('%Y-%m-%d'),
        'tags': tags,
        'status': 'ready',
        'geo_compliant': True,
    }


def run_geo_digest(input_path=None):
    src = Path(input_path) if input_path else _latest_raw()
    if not src or not src.exists():
        log_error('未找到原始抓取文件，请先运行 scrape', 'B')
        return None

    with open(src, 'r', encoding='utf-8') as f:
        data = json.load(f)
    items = data.get('items', [])
    log(f'GEO 消化: {len(items)} 条 | {src.name}', 'B')

    digested = []
    for i, item in enumerate(items, 1):
        log(f'  [{i}/{len(items)}] {item.get("title", "")[:30]}...', 'B')
        digested.append(_digest_item(item))

    today = datetime.now().strftime('%Y%m%d_%H%M')
    out = CLEAN_GEO / f'digest_{today}.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({
            'digested_at': datetime.now().isoformat(),
            'source': str(src),
            'items': digested,
        }, f, ensure_ascii=False, indent=2)

    log_success(f'消化完成: {out}', 'B')
    return out
