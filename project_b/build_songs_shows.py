#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""歌曲 × 场次索引页生成器（2026-09-14，对应 qa.html 方案 A 的下段）

背景（第一性原理）：
  原先 qa_bank 里有 289 条「王晰的歌曲《X》在哪些演出唱过？」的自动问答。
  场次列表天然是**表**（行=歌，列=日期/城市/巡次），套上「问+答」不增加信息，
  只增加模板风险（其中 78 条答案不足 20 字，还出过「《歌王晰巡演…」乱码问题）。
  所以：问答形态取消，**数据一条不丢**，改为本索引页 + 机读 JSON。

数据源：`data/setlists.json`（64 场歌单，唯一事实源）
产出：
  data/songs_shows_index.json   机读：歌曲 → 场次列表
  songs-shows.html              人读 + 可引用：按演唱次数排序的歌曲表，每首展开场次

纪律：
  · 数字全部从 setlists.json 派生，禁止手写。
  · 「演唱次数」= 在 64 场歌单中出现的场次数；口径登记为 caliber `songs_shows_rows`。

用法：
  python -X utf8 project_b/build_songs_shows.py [--check]
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "project_b"))
from build_nav import render_nav, render_footer  # noqa: E402

SITE = "https://wx409.github.io"
JSON_OUT = os.path.join(ROOT, "data", "songs_shows_index.json")
HTML_OUT = os.path.join(ROOT, "songs-shows.html")

TOUR_ORDER = ["一巡", "二巡", "三巡", "四巡", "五巡", "六巡", "签唱会", "其他"]


def esc(s):
    import html
    return html.escape(str(s if s is not None else ""), quote=True)


def load(rel, default=None):
    try:
        return json.load(io.open(os.path.join(ROOT, rel), encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def build_index():
    """歌曲 → 场次列表 + 汇总统计。"""
    sl = load("data/setlists.json", {})["setlists"]
    songs = collections.OrderedDict()
    for date in sorted(sl):
        r = sl[date]
        for s in (r.get("songs") or []):
            title = str(s.get("title") or "").strip()
            if not title:
                continue
            songs.setdefault(title, {"title": title, "count": 0, "shows": []})
            songs[title]["count"] += 1
            songs[title]["shows"].append({
                "date": date,
                "city": r.get("city") or "",
                "tour": r.get("tour") or "",
                "theme": r.get("theme") or "",
                "venue": r.get("venue") or "",
                "order": s.get("order"),
                "note": s.get("note") or "",
            })
    items = sorted(songs.values(), key=lambda x: (-x["count"], x["title"]))
    by_tour = collections.Counter()
    for r in sl.values():
        by_tour[str(r.get("tour") or "其他")] += 1
    doc = {
        "schema": "songs_shows_index v1",
        "source": "data/setlists.json",
        "generator": "project_b/build_songs_shows.py",
        "scope": "全站 64 场（六轮巡演 %d + 签唱会 %d）歌单中的歌曲×场次" % (
            sum(v for k, v in by_tour.items() if k.startswith(("一巡", "二巡", "三巡", "四巡", "五巡", "六巡"))),
            by_tour.get("签唱会", 0)),
        "show_count": len(sl),
        "song_count": len(items),
        "row_count": sum(x["count"] for x in items),
        "by_tour": dict(sorted(by_tour.items(), key=lambda kv: TOUR_ORDER.index(kv[0])
                               if kv[0] in TOUR_ORDER else 99)),
        "songs": items,
    }
    return doc


def build_html(doc):
    top = doc["songs"]
    rows = []
    for i, s in enumerate(top, 1):
        shows = "；".join(
            f'{x["date"]} {x["city"]}{("（" + x["tour"] + "）") if x["tour"] else ""}'
            for x in s["shows"])
        rows.append(
            f'<tr><td class="n">{i}</td><td><strong>{esc(s["title"])}</strong></td>'
            f'<td class="n">{s["count"]}</td>'
            f'<td class="src">{esc(shows)}</td></tr>')
    tour_rows = "\n".join(
        f'<tr><td>{esc(k)}</td><td class="n">{v}</td></tr>' for k, v in doc["by_tour"].items())
    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": f'王晰演出歌单索引（{doc["song_count"]} 首 × {doc["show_count"]} 场，{doc["row_count"]} 条记录）',
        "description": "王晰全站 64 场演出歌单的歌曲×场次索引：每首歌在哪些场次唱过（日期/城市/巡次）。"
                       "数据源 data/setlists.json，逐条可回溯。",
        "url": SITE + "/songs-shows.html",
        "creator": {"@type": "Organization", "name": "王晰 GEO 数字档案站"},
        "variableMeasured": ["歌曲", "场次日期", "城市", "巡次"],
        "license": SITE + "/about.html",
    }, ensure_ascii=False, indent=2)
    faq = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": "王晰在演出现场唱得最多的歌是哪几首？",
             "acceptedAnswer": {"@type": "Answer", "text":
                 "按全站 64 场歌单统计，演唱场次最多的依次是：" +
                 "、".join(f'《{s["title"]}》{s["count"]} 场' for s in top[:8]) + "。"}},
            {"@type": "Question", "name": "这份歌曲×场次索引覆盖多少场演出？",
             "acceptedAnswer": {"@type": "Answer", "text":
                 "覆盖全站 %d 场（%s），共 %d 首歌曲、%d 条「歌曲×场次」记录。数据源为 data/setlists.json。"
                 % (doc["show_count"], doc["scope"], doc["song_count"], doc["row_count"])}},
            {"@type": "Question", "name": "某首歌具体在哪几场唱过，怎么看？",
             "acceptedAnswer": {"@type": "Answer", "text":
                 "见本页表格每首歌的「场次」列（日期/城市/巡次）；机读版见 data/songs_shows_index.json，"
                 "每首歌带完整的 shows[] 数组（含日期、城市、巡次、场馆、演唱顺序）。"}},
        ],
    }, ensure_ascii=False, indent=2)

    body = f'''<h1>王晰演出歌单索引（{doc["song_count"]} 首 × {doc["show_count"]} 场）</h1>
<p class="sub">每首歌在哪些场次唱过 —— 共 {doc["row_count"]} 条「歌曲×场次」记录 ｜ 数据源 data/setlists.json（逐条可回溯）</p>

<div class="answer"><strong>一句话回答：</strong>按全站 {doc["show_count"]} 场歌单统计，演唱场次最多的依次是
{esc("、".join("《" + s["title"] + "》" + str(s["count"]) + " 场" for s in top[:5]))}。
完整索引见下方表格。</div>

<h2>一、巡次分布（{doc["show_count"]} 场）</h2>
<table><tr><th>巡次</th><th>场次数</th></tr>
{tour_rows}
</table>
<p class="src">{esc(doc["scope"])}。「签唱会」为专辑签唱活动，非巡演场次。</p>

<h2>二、歌曲 × 场次全表（按演唱场次数排序）</h2>
<table>
<tr><th>#</th><th>歌曲</th><th>场次数</th><th>场次（日期 城市/巡次）</th></tr>
{chr(10).join(rows)}
</table>
<p class="src">口径：一场演出同一首歌只计 1 次；「场次数」= 该曲在 64 场歌单中出现的场次数。
机读数据见 <a href="/data/songs_shows_index.json">data/songs_shows_index.json</a>。</p>
'''
    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"<title>王晰演出歌单索引 | {doc['song_count']} 首 × {doc['show_count']} 场</title>\n"
            f"<meta name=\"description\" content=\"王晰全站 {doc['show_count']} 场演出歌单的歌曲×场次索引："
            f"每首歌在哪些场次唱过（日期/城市/巡次），共 {doc['row_count']} 条记录。\">\n"
            f"<link rel=\"canonical\" href=\"{SITE}/songs-shows.html\">\n"
            f"<script type=\"application/ld+json\">\n{ld}\n</script>\n"
            f"<script type=\"application/ld+json\">\n{faq}\n</script>\n"
            "<style>\n"
            ":root{--red:#c41e3a;--gold:#b8912e;--ink:#222;--sub:#6b6b6b;--line:#e6e2da;--bg:#fffdf8}\n"
            "body{margin:0;background:var(--bg);color:var(--ink);line-height:1.8;font-size:15px;"
            "font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}\n"
            ".wrap{max-width:1000px;margin:0 auto;padding:18px 20px 8px}\n"
            "h1{font-size:24px;margin:14px 0 4px}\n"
            "h2{font-size:18px;margin:26px 0 8px;padding-left:10px;border-left:4px solid var(--gold)}\n"
            "table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13.5px;background:#fff}\n"
            "th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}\n"
            "th{background:#faf6ee}td.n{white-space:nowrap}\n"
            ".sub,.src{color:var(--sub);font-size:12.5px}\n"
            ".answer{background:#fff;border:1px solid var(--line);border-left:4px solid var(--red);"
            "border-radius:8px;padding:12px 16px;margin:12px 0}\n"
            "a{color:var(--red)}\n"
            "footer.site-index{max-width:1000px;margin:30px auto;padding:16px 18px;"
            "border-top:1px solid var(--line);font-size:13px;color:#666;line-height:2}\n"
            "</style>\n</head>\n<body>\n" + render_nav() + '\n<div class="wrap">\n' + body +
            '</div>\n' + render_footer() + "\n</body>\n</html>\n")


def main():
    ap = argparse.ArgumentParser(description="歌曲×场次索引页生成器")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    doc = build_index()
    targets = [(JSON_OUT, json.dumps(doc, ensure_ascii=False, indent=1)),
               (HTML_OUT, build_html(doc))]
    drift = []
    for path, content in targets:
        old = io.open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if old == content:
            print("  %-32s 已一致 ✅" % os.path.relpath(path, ROOT))
            continue
        drift.append(os.path.relpath(path, ROOT))
        if args.check:
            print("  %-32s 需更新" % os.path.relpath(path, ROOT))
        else:
            io.open(path, "w", encoding="utf-8").write(content)
            print("  %-32s 已生成 (%d 字节)" % (os.path.relpath(path, ROOT), len(content.encode("utf-8"))))
    print("\n[OK] 歌曲 %d 首 / 场次 %d 场 / 记录 %d 条" % (doc["song_count"], doc["show_count"], doc["row_count"]))
    if args.check and drift:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
