#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B项目：GEO 同步到网站仓库"""

import csv
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from project_b.geo_common import CLEAN_GEO, OUTPUT_GEO, WEBSITE_DIR
from utils import log, log_success, log_error

LINKS_CSV = WEBSITE_DIR / 'data' / 'links.csv'
SOCIAL_JSON = WEBSITE_DIR / 'data' / 'social_links.json'
REPO_MD = WEBSITE_DIR / 'repo' / '2026.md'


def _latest_digest():
    files = sorted(CLEAN_GEO.glob('digest_*.json'), reverse=True)
    return files[0] if files else None


def _merge_links_csv(items):
    """将新条目合并到 website data/links.csv（按 url 去重）"""
    existing_urls = set()
    rows = []
    fieldnames = ['platform', 'url', 'title', 'summary', 'author', 'date', 'tags']

    if LINKS_CSV.exists():
        with open(LINKS_CSV, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or fieldnames
            for row in reader:
                url = (row.get('url') or '').strip()
                if url:
                    existing_urls.add(url)
                rows.append(row)

    added = 0
    for item in items:
        url = item.get('url', '')
        if not url or url in existing_urls:
            continue
        rows.append({
            'platform': item.get('platform', ''),
            'url': url,
            'title': item.get('title', ''),
            'summary': item.get('summary', ''),
            'author': item.get('author', ''),
            'date': item.get('date', ''),
            'tags': ','.join(item.get('tags', [])),
        })
        existing_urls.add(url)
        added += 1

    if added:
        LINKS_CSV.parent.mkdir(parents=True, exist_ok=True)
        with open(LINKS_CSV, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        log_success(f'links.csv 新增 {added} 条', 'B')

    return added


def _merge_social_json(items):
    if not SOCIAL_JSON.exists():
        existing = []
    else:
        with open(SOCIAL_JSON, 'r', encoding='utf-8') as f:
            existing = json.load(f)

    seen = {i.get('url') for i in existing}
    added = 0
    for item in items:
        url = item.get('url')
        if url and url not in seen:
            existing.append(item)
            seen.add(url)
            added += 1

    if added:
        with open(SOCIAL_JSON, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        log_success(f'social_links.json 新增 {added} 条', 'B')
    return added


def _append_repo_md():
    geo_files = sorted(OUTPUT_GEO.glob('*_geo.md'), reverse=True)
    if not geo_files:
        return 0

    latest = geo_files[0]
    content = latest.read_text(encoding='utf-8')
    marker = f'\n\n---\n\n<!-- GEO_SYNC {datetime.now().strftime("%Y-%m-%d")} from {latest.name} -->\n\n'

    REPO_MD.parent.mkdir(parents=True, exist_ok=True)
    if REPO_MD.exists():
        existing = REPO_MD.read_text(encoding='utf-8')
        if latest.name in existing:
            log(f'repo/2026.md 已含 {latest.name}，跳过追加', 'B')
            return 0
        REPO_MD.write_text(existing + marker + content, encoding='utf-8')
    else:
        REPO_MD.write_text(content, encoding='utf-8')

    log_success(f'已追加到 repo/2026.md: {latest.name}', 'B')
    return 1


def _git_push(message):
    try:
        subprocess.run(['git', '-C', str(WEBSITE_DIR), 'add', 'data/', 'repo/'], check=True, capture_output=True)
        status = subprocess.run(['git', '-C', str(WEBSITE_DIR), 'diff', '--cached', '--quiet'], capture_output=True)
        if status.returncode == 0:
            log('无新变更，跳过 Git 提交', 'B')
            return True
        subprocess.run(['git', '-C', str(WEBSITE_DIR), 'commit', '-m', message], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(WEBSITE_DIR), 'push', 'origin', 'main'], check=True, capture_output=True)
        log_success('已推送到 GitHub', 'B')
        return True
    except subprocess.CalledProcessError as e:
        log_error(f'Git 推送失败: {e}', 'B')
        return False


def run_sync():
    log('GEO 同步到网站...', 'B')
    digest_file = _latest_digest()
    items = []
    if digest_file:
        with open(digest_file, 'r', encoding='utf-8') as f:
            items = json.load(f).get('items', [])

    _merge_links_csv(items)
    _merge_social_json(items)
    _append_repo_md()

    today = datetime.now().strftime('%Y%m%d')
    msg = f'{today}: GEO sync from 星厂B'
    _git_push(msg)
    log_success('GEO 同步完成', 'B')
    return True
