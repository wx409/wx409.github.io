# -*- coding: utf-8 -*-
"""系列页（Quartz 模式）：data/share/series.json + series-<id>.html（上一篇/下一篇 + 目录）。

每个系列复用既有卡片 HTML（不重写内容）；页与页之间按系列顺序给出 prev/next。
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
SER = D / "share" / "series.json"
REND = D / "share" / "rendered"

SERIES = [
    {"id": "low-line", "title": "低音线", "desc": "录音室与现场的最低稳定音、低音占比与基线",
     "cards": ["card_low_baseline", "card_low_floor", "card_low_dynamic"]},
    {"id": "long-tone", "title": "长声", "desc": "一口气的长度与音高稳定",
     "cards": ["card_long_tone", "card_pick_16s_breath"]},
    {"id": "vibrato", "title": "颤音", "desc": "十年来同一个抖法",
     "cards": ["card_vibrato", "card_vibrato_8y"]},
    {"id": "chenxiang", "title": "沉响纪实", "desc": "两晚同曲、跨源与点歌段",
     "cards": ["card_pair_54", "card_pick_low_superlative"]},
    {"id": "copyright", "title": "版权梗", "desc": "一首想唱七年的歌与它的传播",
     "cards": ["card_woyaoni_selfignite", "card_selfignite_latest"]},
]


def card_html(cid: str) -> str:
    p = REND / f"{cid}.html"
    return p.read_text(encoding="utf-8") if p.exists() else f"<p class=meta>（缺卡 {cid}）</p>"


def main() -> int:
    SER.parent.mkdir(parents=True, exist_ok=True)
    SER.write_text(json.dumps({"series": SERIES}, ensure_ascii=False, indent=1), encoding="utf-8")
    pages = []
    for i, s in enumerate(SERIES):
        prev = SERIES[i - 1] if i > 0 else None
        nxt = SERIES[i + 1] if i + 1 < len(SERIES) else None
        nav = []
        if prev:
            nav.append(f'<a href="series-{prev["id"]}.html">← 上一篇：{html.escape(prev["title"])}</a>')
        if nxt:
            nav.append(f'<a href="series-{nxt["id"]}.html">下一篇：{html.escape(nxt["title"])} →</a>')
        H = ["<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
             "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
             f"<title>{html.escape(s['title'])}｜系列</title>",
             f"<link rel=\"canonical\" href=\"https://wx409.github.io/series-{s['id']}.html\">",
             "<style>body{font:15px/1.7 -apple-system,Segoe UI,Microsoft YaHei,sans-serif;max-width:860px;"
             "margin:24px auto;padding:0 16px}.meta{color:#666;font-size:.9em}.nav{display:flex;"
             "justify-content:space-between;margin:18px 0;font-size:14px}</style></head><body>",
             "<!-- NAV_START --><!-- NAV_END -->",
             f"<h1>{html.escape(s['title'])}</h1><p class=\"meta\">{html.escape(s['desc'])}</p>",
             '<div class="nav">' + (nav[0] if nav else "") + " " + (nav[1] if len(nav) > 1 else "") + "</div>"]
        for cid in s["cards"]:
            H.append(f"<section>{card_html(cid)}</section>")
        H.append('<h2>系列目录</h2><ul>')
        for t in SERIES:
            mark = "（当前）" if t["id"] == s["id"] else ""
            H.append(f'<li><a href="series-{t["id"]}.html">{html.escape(t["title"])}</a>{mark}</li>')
        H.append('</ul><div class="nav">' + (nav[0] if nav else "") + " " + (nav[1] if len(nav) > 1 else "") + "</div>")
        H.append('<p class="meta"><a href="stories.html">场次故事</a>｜<a href="share.html">素材与引用</a></p></body></html>')
        out = SITE / f"series-{s['id']}.html"
        out.write_text("\n".join(H), encoding="utf-8")
        pages.append(out.name)
        print("[ok]", out.name)
    print("[ok] series.json｜", len(SERIES), "个系列；页", len(pages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
