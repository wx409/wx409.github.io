#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""官宣扫描 → 候选箱：只收集，不自动入库。

数据源（本地，无网络）：
  · 工作室微博归档  E:\\wx\\私有工具\\weibo_archive_studio\\posts\\YYYY\\YYYY-MM\\*.json
规则：
  · 近 N 天；文本命中关键词（新歌/单曲/发行/上线/官宣/巡演/音乐会/首演/开票/剧场）
  · 与 data/timeline.json、data/intake_inbox.json 去重
  · 只写 pending 候选，必须人工确认
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
ARCHIVE = Path(r'E:\wx\私有工具\weibo_archive_studio\posts')
INBOX = ROOT / 'data' / 'intake_inbox.json'
TIMELINE = ROOT / 'data' / 'timeline.json'
KEYS = ('新歌', '单曲', '发行', '上线', '官宣', '开票', '预售', '首演', '定档')
NOISE = ('直拍', '花絮', '返图', '转发', '后台', '排练')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', type=int, default=14)
    args = ap.parse_args()
    inbox = json.loads(INBOX.read_text(encoding='utf-8')) if INBOX.exists() else {"schema": "intake_inbox/v1", "items": []}
    timeline = json.loads(TIMELINE.read_text(encoding='utf-8'))
    seen = " ".join(e.get('title', '') for e in timeline) + " " + " ".join(x.get('title', '') for x in inbox['items'])
    since = (date.today() - timedelta(days=args.days)).isoformat()
    added = 0
    if ARCHIVE.exists():
        for f in sorted(ARCHIVE.glob('*/*/*.json')):
            try:
                d = json.loads(f.read_text(encoding='utf-8'))
            except Exception:
                continue
            day = str(d.get('date') or '')
            if not day or day < since:
                continue
            text = (d.get('text') or '').strip()
            if not text or not any(k in text for k in KEYS):
                continue
            if any(nk in text for nk in NOISE):
                continue
            title = text[:40].replace('\n', ' ')
            if title[:12] in seen:
                continue
            nid = f"c{len(inbox['items'])+1:03d}"
            inbox['items'].append({
                "id": nid, "kind": "activity", "title": title, "date": day,
                "city": "", "source": f"微博归档 {d.get('id')}",
                "note": text[:120], "status": "pending", "detected_at": date.today().isoformat(),
            })
            seen += " " + title[:12]
            added += 1
    INBOX.write_text(json.dumps(inbox, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f"扫描近 {args.days} 天：新增候选 {added} 条｜候选总数 {len(inbox['items'])}")


if __name__ == '__main__':
    main()
