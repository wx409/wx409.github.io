#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全文检索：在 data/corpus/corpus.db 里搜微博/百家号/抖音的正文与转写。

用法：
  python -X utf8 project_b/corpus_search.py 送别
  python -X utf8 project_b/corpus_search.py 送别 --platform 抖音 --limit 5
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DB = Path(r"D:\wx409.github.io\data\corpus\corpus.db")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("q")
    ap.add_argument("--platform", default="")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--song", default="", help="按曲名过滤")
    a = ap.parse_args()

    con = sqlite3.connect(DB)
    like = "%" + a.q + "%"
    sql = ("select platform, account, date, text, transcript, url, media, songs from posts "
           "where (text like ? or transcript like ?)")
    args = [like, like]
    if a.platform:
        sql += " and platform=?"
        args.append(a.platform)
    if a.song:
        sql += " and songs like ?"
        args.append("%" + a.song + "%")
    sql += " order by date desc limit ?"
    args.append(a.limit)
    rows = con.execute(sql, args).fetchall()
    print(f"命中 {len(rows)} 条（显示前 {a.limit}）")
    for plat, acct, date, text, tr, url, media, songs in rows:
        snip = (tr or text or "")[:120].replace("\n", " ")
        print(f"\n[{plat}/{acct}] {date}\n  {snip}")
        if url:
            print("  ", url)
        if songs:
            print("   曲目:", songs)
        if media:
            print("   媒体:", media.split("|")[0])
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
