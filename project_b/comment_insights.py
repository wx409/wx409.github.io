# -*- coding: utf-8 -*-
"""comment_insights.py —— 从私有评论库生成公开聚合（匿名、无原文全量）

输入：E:\\wx\\私有\\王晰语料库\\comments.db（posts + comment_meta）
输出：data/voices.json（只含聚合 + ≤60 字匿名短引用）
"""
from __future__ import annotations
import json, sqlite3, re, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = Path(r"E:\wx\私有\王晰语料库\comments.db")
OUT = ROOT / "data" / "voices.json"

KEYWORDS = ["低音", "好听", "现场", "专辑", "歌声", "声音", "唱歌", "音色", "高音",
            "民歌", "巡演", "音乐会", "草原之夜", "声入人心", "王晰", "晰哥", "期待", "帅"]

def clean(t: str) -> str:
    t = re.sub(r"<[^>]+>", "", t or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def main() -> int:
    if not DB.exists():
        print("[SKIP] 私有评论库不存在（%s）——非本机环境跳过" % DB)
        return 0
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    n = con.execute("SELECT COUNT(*) n FROM posts WHERE platform='weibo-comment'").fetchone()["n"]
    posts = con.execute("SELECT COUNT(DISTINCT m.post_mid) n FROM posts p JOIN comment_meta m ON m.key=p.key "
                        "WHERE p.platform='weibo-comment'").fetchone()["n"]
    years = [dict(r) for r in con.execute(
        "SELECT substr(date,1,4) y, COUNT(*) n FROM posts WHERE platform='weibo-comment' AND date<>'' GROUP BY y ORDER BY y")]
    uniq = con.execute("SELECT COUNT(DISTINCT text) n FROM posts WHERE platform='weibo-comment'").fetchone()["n"]

    kw = []
    for k in KEYWORDS:
        c = con.execute("SELECT COUNT(*) n FROM posts WHERE platform='weibo-comment' AND text LIKE ?",
                        ("%" + k + "%",)).fetchone()["n"]
        kw.append({"word": k, "count": c, "pct": round(c / n * 100, 2) if n else 0})
    kw.sort(key=lambda x: -x["count"])

    quotes, seen = [], set()
    for r in con.execute(
            "SELECT p.text, p.date, m.likes FROM posts p JOIN comment_meta m ON m.key=p.key "
            "WHERE p.platform='weibo-comment' AND m.likes>=5 ORDER BY m.likes DESC LIMIT 500"):
        t = clean(r["text"])
        if not (8 <= len(t) <= 60):
            continue
        if "@" in t or "http" in t.lower() or t.startswith("#") or t in seen:
            continue
        seen.add(t)
        quotes.append({"text": t, "likes": r["likes"], "date": r["date"]})
        if len(quotes) >= 12:
            break

    top_posts = []
    for r in con.execute(
            "SELECT p.url, m.post_mid, COUNT(*) n, MAX(m.likes) top_like "
            "FROM posts p JOIN comment_meta m ON m.key=p.key "
            "WHERE p.platform='weibo-comment' GROUP BY m.post_mid ORDER BY n DESC LIMIT 10"):
        top_posts.append({"post": r["url"], "post_mid": r["post_mid"],
                          "comments": r["n"], "top_like": r["top_like"]})

    # 广场短帖（platform=weibo-search）：受众自述，另一类语料
    def parse_date(s: str) -> str:
        s = (s or "").strip()
        today = dt.date.today()
        if not s:
            return ""
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
        if m:
            return m.group(0)
        if s.startswith("今天") or "分钟前" in s or "小时前" in s:
            return today.isoformat()
        if s.startswith("昨天"):
            return (today - dt.timedelta(days=1)).isoformat()
        m = re.match(r"(\d{1,2})月(\d{1,2})日", s)
        if m:
            return "%d-%02d-%02d" % (today.year, int(m.group(1)), int(m.group(2)))
        return ""

    srows = con.execute("SELECT text, date, url FROM posts WHERE platform='weibo-search'").fetchall()
    syears = {}
    for r in srows:
        y = parse_date(r["date"])[:4]
        if y:
            syears[y] = syears.get(y, 0) + 1
    ssamples, sseen = [], set()
    for r in srows:
        t = clean(r["text"])
        if not (8 <= len(t) <= 60) or "@" in t or "http" in t.lower() or t in sseen:
            continue
        if not re.search(r"王晰|晰哥", t):
            continue
        pos = min([p for p in (t.find("王晰"), t.find("晰哥")) if p >= 0] or [999])
        if pos > 30:
            continue
        sseen.add(t)
        ssamples.append({"text": t, "date": parse_date(r["date"]) or r["date"]})
        if len(ssamples) >= 8:
            break

    doc = {
        "schema": 1,
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "scope": "微博评论（工作室 1100+ 帖 + 王晰本人近 30 帖）＋ 王晰广场短帖",
        "n_comments": n, "n_posts": posts,
        "n_unique_text": uniq,
        "dup_rate_pct": round((1 - uniq / n) * 100, 1) if n else 0,
        "by_year": years,
        "keywords": kw,
        "quotes": quotes,
        "top_posts": top_posts,
        "search": {
            "n": len(srows),
            "by_year": [{"y": k, "n": v} for k, v in sorted(syears.items())],
            "samples": ssamples,
        },
        "coverage_note": "每帖最多 6 页（约 30–50%），非全量；评论为粉丝自选样本，不代表大众",
        "privacy": "uid 已哈希、不含昵称；仅发布聚合与 ≤60 字匿名短引用",
        "source_db": "E:\\wx\\私有\\王晰语料库\\comments.db（本地私有，不入 git）",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("写入", OUT, "| 评论", n, "| 帖子", posts, "| 广场", len(srows), "| 引用", len(quotes))
    con.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
