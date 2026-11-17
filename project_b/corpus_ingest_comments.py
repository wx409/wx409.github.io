# -*- coding: utf-8 -*-
"""corpus_ingest_comments.py —— 把评论语料 JSONL 并入检索库（默认入私有库，不碰公开站）

输入：comment_ops.py export-corpus 产出的 JSONL（每行一条评论，uid 已哈希）
默认库：E:\\wx\\私有\\王晰语料库\\comments.db（本地私有，FTS5 可检索）
公开库：data/corpus/corpus.db 需显式 --db + --yes-publish（评论是第三方内容，默认不公开）

用法：
  python -X utf8 project_b\\corpus_ingest_comments.py --jsonl "E:\\...\\comments_xxx.jsonl"
  python -X utf8 project_b\\corpus_ingest_comments.py --jsonl ... --query 低音
  python -X utf8 project_b\\corpus_ingest_comments.py --jsonl ... --db data/corpus/corpus.db --yes-publish
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = Path(r"E:\wx\私有\王晰语料库\comments.db")
PUBLIC_DB = ROOT / "data" / "corpus" / "corpus.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts(
  key TEXT PRIMARY KEY, platform TEXT, account TEXT, date TEXT, text TEXT,
  url TEXT, media TEXT, transcript TEXT, duration REAL, songs TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(key, text, transcript);
CREATE TABLE IF NOT EXISTS comment_meta(
  key TEXT PRIMARY KEY, comment_id TEXT, post_mid TEXT, likes INTEGER
);
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--db", default=str(DEFAULT_DB))
    ap.add_argument("--query", default="")
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("--yes-publish", action="store_true")
    a = ap.parse_args()

    db = Path(a.db)
    public = db.resolve() == PUBLIC_DB.resolve()
    if public and not a.yes_publish:
        print("拒绝对公开库写入：评论是第三方内容，默认只进私有库。")
        print("确实要公开请加 --yes-publish（并确认已做匿名化/只发聚合）。")
        return 2
    db.parent.mkdir(parents=True, exist_ok=True)

    src = Path(a.jsonl)
    if not src.exists():
        print("找不到 JSONL：", src)
        return 1

    con = sqlite3.connect(db)
    con.executescript(SCHEMA)
    n = dup = bad = 0
    with src.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                bad += 1
                continue
            if not r.get("text") or not r.get("key"):
                bad += 1
                continue
            songs = r.get("songs") or []
            cur = con.execute(
                "INSERT OR IGNORE INTO posts(key,platform,account,date,text,url,media,transcript,duration,songs)"
                " VALUES(?,?,?,?,?,?,?,?,?,?)",
                (r["key"], r.get("platform") or "weibo-comment", r.get("account") or "",
                 r.get("date") or "", r["text"], r.get("url") or "", None, None, None,
                 json.dumps(songs, ensure_ascii=False)))
            if cur.rowcount:
                con.execute("INSERT INTO posts_fts(key,text,transcript) VALUES(?,?,?)",
                            (r["key"], r["text"], ""))
                con.execute("INSERT OR REPLACE INTO comment_meta(key,comment_id,post_mid,likes)"
                            " VALUES(?,?,?,?)",
                            (r["key"], r.get("comment_id") or "", r.get("post_mid") or "",
                             int(r.get("likes") or 0)))
                n += 1
            else:
                dup += 1
    con.commit()

    tot = con.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    per = con.execute("SELECT platform, COUNT(*) FROM posts GROUP BY platform ORDER BY 2 DESC").fetchall()
    print("入库 %d 条（重复 %d / 跳过 %d）｜库内合计 %d" % (n, dup, bad, tot))
    for p, c in per:
        print("  %-16s %d" % (p, c))
    print("库：", db)

    if a.query:
        print("\n=== 检索「%s」（按赞数排序，最多 10 条） ===" % a.query)
        like = "%" + a.query + "%"
        rows = con.execute(
            "SELECT p.date, substr(p.text,1,60), m.likes FROM posts p "
            "LEFT JOIN comment_meta m ON m.key=p.key "
            "WHERE p.text LIKE ? ORDER BY COALESCE(m.likes,0) DESC, p.date DESC LIMIT 10",
            (like,)).fetchall()
        if not rows:
            print("  无结果")
        for d, t, likes in rows:
            print("  %s | 赞 %s | %s" % (d or "—", likes if likes is not None else "—", t))
    if a.top:
        print("\n=== 最高赞 %d 条 ===" % a.top)
        rows = con.execute(
            "SELECT p.date, substr(p.text,1,70), m.likes FROM posts p "
            "JOIN comment_meta m ON m.key=p.key ORDER BY m.likes DESC LIMIT ?", (a.top,)).fetchall()
        for d, t, likes in rows:
            print("  %s | 赞 %s | %s" % (d or "—", likes, t))
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
