# -*- coding: utf-8 -*-
"""修 weibo_all_posts.json 的 18 条畸形日期（20260824 → 2026-08-24）。

用法：python -X utf8 project_b/fix_weibo_dates.py [--check]
幂等：已规范的日期不动。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime

P = r'E:\wx\私有工具\weibo_merged\weibo_all_posts.json'
PAT = re.compile(r'^(\d{4})(\d{2})(\d{2})$')


def fix(d):
    m = PAT.match(str(d or '').strip())
    if m:
        return '%s-%s-%s' % m.groups()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    doc = json.loads(io.open(P, encoding='utf-8').read())
    posts = doc.get('posts') or []
    n = 0
    for p in posts:
        new = fix(p.get('date'))
        if new:
            p['date'] = new
            n += 1
    print('weibo_all_posts.json：待修 %d 条' % n)
    if not n:
        print('[OK] 已全部规范 ✅')
        return 0
    if a.check:
        print('[FAIL] 仍有 %d 条畸形日期' % n)
        return 1
    doc['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    doc['note'] = str(doc.get('note') or '') + '（2026-09-14 修复 18 条畸形日期 YYYYMMDD→YYYY-MM-DD）'
    io.open(P, 'w', encoding='utf-8').write(json.dumps(doc, ensure_ascii=False, indent=1))
    print('[OK] 已写回 %s' % P)
    return 0


if __name__ == '__main__':
    sys.exit(main())
