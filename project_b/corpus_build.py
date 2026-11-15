#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全平台语料库：扫描微博/工作室/百家号/抖音/小红书 → SQLite FTS5 索引。

用法：
  python -X utf8 project_b/corpus_build.py            # 重建索引
  python -X utf8 project_b/corpus_build.py --stats    # 只看统计
产物：data/corpus/corpus.db（表 posts + FTS 表 posts_fts）
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DB = ROOT / "data" / "corpus" / "corpus.db"
SRC = [
    (Path(r"E:\wx\私有工具\weibo_merged\合并"), "微博", "王晰"),
    (Path(r"E:\wx\私有工具\weibo_merged\工作室微博"), "微博", "工作室"),
    (Path(r"E:\wx\私有工具\weibo_merged\工作室微博_完整"), "微博", "工作室"),
    (Path(r"E:\wx\私有工具\weibo_merged\百家号"), "百家号", "百家号"),
]
DOUYIN = Path(r"E:\wx\论文素材_王晰作传\抖音\awemes.json")
TRANS_DIR = ROOT / "data" / "corpus" / "transcripts"


def load_songs():
    names = set()
    try:
        for x in json.loads((ROOT / "data" / "archive_vocal_albums.json").read_text(encoding="utf-8"))["songs"]:
            if x.get("title"):
                names.add(x["title"])
    except Exception:
        pass
    try:
        for x in json.loads(Path(r"E:\wx\论文素材_王晰作传\曲谱_网友扒谱\index.json").read_text(encoding="utf-8"))["items"]:
            if x.get("song"):
                names.add(x["song"])
    except Exception:
        pass
    try:
        for x in json.loads(Path(r"E:\wx\论文素材_王晰作传\单曲音频_汇总.json").read_text(encoding="utf-8"))["songs"]:
            if x.get("title"):
                names.add(x["title"])
    except Exception:
        pass
    return sorted({n for n in names if len(n) >= 2}, key=len, reverse=True)


def clean(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", t or "")
    t = re.sub(r"https?://\S+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def read_post(d: Path):
    """读一个微博/百家号帖目录 → (date, text, media[])"""
    txt = ""
    for f in sorted(d.glob("*.txt"), key=lambda p: -p.stat().st_size):
        try:
            txt = f.read_text(encoding="utf-8", errors="ignore")
            if txt.strip():
                break
        except Exception:
            continue
    if not txt:
        for f in d.glob("*.json"):
            try:
                j = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
                txt = j.get("text") or j.get("content") or ""
                if txt:
                    break
            except Exception:
                continue
    media = [str(p) for p in d.glob("*.mp4")] + [str(p) for p in d.glob("*.mov")]
    m = re.match(r"(\d{8})", d.name)
    date = f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}" if m else ""
    return date, clean(txt), media


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stats", action="store_true")
    a = ap.parse_args()

    DB.parent.mkdir(parents=True, exist_ok=True)
    TRANS_DIR.mkdir(parents=True, exist_ok=True)

    if a.stats and DB.exists():
        con = sqlite3.connect(DB)
        for q in ("select platform,count(*) from posts group by platform",
                  "select count(*) from posts where transcript<>''"):
            print(q, "→", con.execute(q).fetchall())
        con.close()
        return 0

    con = sqlite3.connect(DB)
    con.executescript("""
    DROP TABLE IF EXISTS posts_fts;
    DROP TABLE IF EXISTS posts;
    CREATE TABLE posts(
      key TEXT PRIMARY KEY, platform TEXT, account TEXT, date TEXT,
      text TEXT, url TEXT, media TEXT, transcript TEXT, duration REAL, songs TEXT);
    CREATE VIRTUAL TABLE posts_fts USING fts5(
      key UNINDEXED, text, transcript, tokenize='unicode61');
    """)

    SONGS = load_songs()
    rows = 0
    for base, platform, account in SRC:
        if not base.exists():
            continue
        for d in base.iterdir():
            if not d.is_dir():
                continue
            date, text, media = read_post(d)
            if not text and not media:
                continue
            key = f"{platform}:{account}:{d.name}"
            tr = TRANS_DIR / (re.sub(r"[^\w\-]+", "_", key)[:120] + ".txt")
            transcript = tr.read_text(encoding="utf-8", errors="ignore") if tr.exists() else ""
            _blob = text + " " + transcript
            _sg = "|".join([n for n in SONGS if n in _blob][:8])
            con.execute("INSERT OR REPLACE INTO posts VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (key, platform, account, date, text, "", "|".join(media),
                         transcript, None, _sg))
            con.execute("INSERT INTO posts_fts(key,text,transcript) VALUES(?,?,?)",
                        (key, text, transcript))
            rows += 1

    if DOUYIN.exists():
        aw = json.loads(DOUYIN.read_text(encoding="utf-8"))
        from datetime import datetime
        for vid, v in aw.items():
            date = (datetime.fromtimestamp(v["ct"]).strftime("%Y-%m-%d")
                    if v.get("ct") else "")
            key = f"抖音:王晰:{vid}"
            tr = TRANS_DIR / f"抖音_王晰_{vid}.txt"
            transcript = tr.read_text(encoding="utf-8", errors="ignore") if tr.exists() else ""
            mp4 = next(iter(Path(r"E:\wx\论文素材_王晰作传\抖音").glob(f"*_{vid}.mp4")), None)
            _blob = (v.get("desc", "") or "") + " " + transcript
            _sg = "|".join([n for n in SONGS if n in _blob][:8])
            con.execute("INSERT OR REPLACE INTO posts VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (key, "抖音", "王晰", date, v.get("desc", ""),
                         f"https://www.douyin.com/video/{vid}",
                         str(mp4) if mp4 else "", transcript, v.get("dur"), _sg))
            con.execute("INSERT INTO posts_fts(key,text,transcript) VALUES(?,?,?)",
                        (key, v.get("desc", ""), transcript))
            rows += 1

    con.commit()
    stat = con.execute("select platform,count(*) from posts group by platform").fetchall()
    con.close()
    print(f"入库 {rows} 条 → {DB}")
    for p, c in stat:
        print(f"  {p}: {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
