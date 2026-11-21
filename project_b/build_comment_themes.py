#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_comment_themes.py —— 12.8 万条私有评论 → 主题/场次聚合（公开、匿名）

输入：E:\\wx\\私有\\王晰语料库\\comments.db
输出：D:\\wx409.github.io\\data\\comment_themes.json
只发布：主题计数、年份分布、≤60 字匿名短引用、场次计数与短引用；不含昵称/原文全量/本地路径。
"""
from __future__ import annotations

import json
import re
import sqlite3
from bisect import bisect_left, bisect_right
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DB = Path(r"E:\wx\私有\王晰语料库\comments.db")
ACT = ROOT / "data" / "activity_master.json"
OUT = ROOT / "data" / "comment_themes.json"

THEMES = [
    ("低音与音色", re.compile(r"低音|低音炮|男低音|音色|嗓音|声线|声音")),
    ("现场与唱功", re.compile(r"现场|live|Live|稳|清唱|真唱|声压|唱功|高音|转音|开麦")),
    ("情感与治愈", re.compile(r"治愈|感动|哭|温柔|陪伴|晚安|心动|暖|抚慰|情绪|安心")),
    ("作品与专辑", re.compile(r"专辑|新歌|单曲|OST|循环|这首歌|听|曲|作品")),
    ("综艺与舞台", re.compile(r"声入人心|歌手|综艺|舞台|节目|春晚|晚会|音乐剧|歌舞剧")),
    ("人品与状态", re.compile(r"可爱|帅|真诚|努力|敬业|感冒|照顾|辛苦|认真|谦逊")),
    ("期待与祝福", re.compile(r"期待|等你|加油|祝福|顺利|健康|平安|越来越好")),
]


def clean(t: str) -> str:
    t = re.sub(r"@[\w\-\u4e00-\u9fa5]+", "", t or "")
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def load_shows():
    rows = json.loads(ACT.read_text(encoding="utf-8")).get("rows") or []
    out = []
    for x in rows:
        d = str(x.get("date") or "")[:10]
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            continue
        out.append({"date": dt, "city": str(x.get("city") or ""), "title": str(x.get("title") or "")})
    out.sort(key=lambda x: x["date"])
    return out


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT p.key,p.date,p.text,p.url,m.likes FROM posts p "
        "LEFT JOIN comment_meta m ON m.key=p.key WHERE p.platform='weibo-comment'"
    ).fetchall()
    shows = load_shows()
    show_dates = [s["date"] for s in shows]

    themes = {name: {"name": name, "n": 0, "by_year": {}, "quotes": []} for name, _ in THEMES}
    by_show = {}
    for r in rows:
        txt = clean(r["text"])
        if len(txt) < 6:
            continue
        try:
            dt = datetime.strptime(str(r["date"])[:10], "%Y-%m-%d").date()
        except Exception:
            continue
        y = dt.strftime("%Y")
        for name, rx in THEMES:
            if rx.search(txt):
                t = themes[name]
                t["n"] += 1
                t["by_year"][y] = t["by_year"].get(y, 0) + 1
                t["quotes"].append((int(r["likes"] or 0), txt[:60]))
        # 场次：日期 ±10 天 + 城市/剧名命中
        lo = bisect_left(show_dates, dt - timedelta(days=10))
        hi = bisect_right(show_dates, dt + timedelta(days=10))
        for s in shows[lo:hi]:
            hit = (s["city"] and s["city"] in txt)
            key_title = "草原之夜" if "草原之夜" in s["title"] else ("沉响与长歌" if "沉响与长歌" in s["title"] else "")
            hit = hit or (key_title and key_title in txt)
            if not hit:
                continue
            k = "%s %s" % (s["date"].isoformat(), s["city"])
            b = by_show.setdefault(k, {"show": k, "n": 0, "quotes": []})
            b["n"] += 1
            b["quotes"].append((int(r["likes"] or 0), txt[:60]))

    out = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "total_comments": len(rows),
           "themes": [], "by_show": []}
    for name, _ in THEMES:
        t = themes[name]
        qs = sorted(t["quotes"], key=lambda x: -x[0])[:6]
        out["themes"].append({"name": name, "n": t["n"],
                              "by_year": dict(sorted(t["by_year"].items())),
                              "quotes": [{"text": q, "likes": n} for n, q in qs]})
    for k, v in sorted(by_show.items(), key=lambda kv: -kv[1]["n"])[:30]:
        qs = sorted(v["quotes"], key=lambda x: -x[0])[:3]
        out["by_show"].append({"show": k, "n": v["n"],
                               "quotes": [{"text": q, "likes": n} for n, q in qs]})
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("评论", len(rows), "｜主题", [(t["name"], t["n"]) for t in out["themes"]])
    print("场次", len(out["by_show"]), "→", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
