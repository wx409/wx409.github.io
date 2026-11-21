#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""comment_harvest_daily.py —— 每天按关键词补评论（微博广场 → 评论 → 私有语料库）

数据落点（没有单一“评论 json”）：
  · 私有 SQLite：E:\\wx\\私有\\王晰语料库\\comments.db（posts 表，platform=weibo-comment）
  · 原始 JSONL：E:\\wx\\私有工具\\comment_ops\\exports\\comments_all.jsonl
  · 站点聚合：D:\\wx409.github.io\\data\\voices.json（只读聚合，不含原文）

用法：
  python -X utf8 project_b\\comment_harvest_daily.py --dry
  python -X utf8 project_b\\comment_harvest_daily.py --limit 20
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
OPS = Path(r"E:\wx\私有工具\comment_ops")
TMP = ROOT / "temp"
EXPORT = OPS / "exports" / "comments_all.jsonl"
KEYWORDS = ["王晰", "王晰 演出", "王晰 活动", "王晰 新歌", "王晰 现场"]


def run(args, cwd=None):
    return subprocess.run([sys.executable, "-X", "utf8"] + args, cwd=str(cwd or ROOT)).returncode


def is_recent(s, days=3):
    s = str(s or "").strip()
    today = date.today()
    if not s:
        return False
    if s.startswith("今天") or "分钟前" in s or "小时前" in s:
        return True
    if s.startswith("昨天"):
        return True
    m = re.match(r"(\d{1,2})月(\d{1,2})日", s)
    if m:
        try:
            d = date(today.year, int(m.group(1)), int(m.group(2)))
            return (today - d).days <= days
        except Exception:
            return False
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        try:
            return (today - date(int(m.group(1)), int(m.group(2)), int(m.group(3)))).days <= days
        except Exception:
            return False
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--pages", type=int, default=2)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    TMP.mkdir(exist_ok=True)
    links = {}
    for i, kw in enumerate(KEYWORDS):
        out = TMP / ("harvest_%02d.json" % i)
        if a.dry:
            print("[dry] search", kw, "->", out.name)
            continue
        run([r"comment_ops.py", "search", "--q", kw, "--pages", str(a.pages),
             "--out", str(out)], cwd=OPS)
        try:
            for x in json.loads(out.read_text(encoding="utf-8")):
                if is_recent(x.get("date")):
                    links[x["url"]] = x
        except Exception as e:
            print("[warn]", kw, e)
    items = list(links.values())[:a.limit]
    merged = TMP / "harvest_links.json"
    merged.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print("候选帖子 %d（近 3 天，取前 %d）→ %s" % (len(links), len(items), merged.name))
    if a.dry or not items:
        return 0
    run([r"comment_ops.py", "collect-batch", "--links", str(merged), "--limit", str(a.limit),
         "--max-pages", "4", "--sleep-post", "2", "--sleep-page", "0.4"], cwd=OPS)
    run([r"comment_ops.py", "export-corpus"], cwd=OPS)
    run([r"project_b\corpus_ingest_comments.py", "--jsonl", str(EXPORT)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
