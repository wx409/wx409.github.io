#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 59 场巡演歌单索引页 live/setlists.html —— 数据全部来自 data/setlists.json，零写死。

用法：python project_b/build_setlists_page.py
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "setlists.json"
OUT = ROOT / "live" / "setlists.html"
SITE = "https://wx409.github.io"


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=False)


def build_page(data: dict) -> str:
    setlists = data["setlists"]
    total_songs = sum(len(v["songs"]) for v in setlists.values())

    # 按巡次分组
    by_tour = {}
    for d, v in sorted(setlists.items()):
        by_tour.setdefault(v.get("tour", ""), []).append((d, v))

    # 顶部导航（锚点）
    nav = []
    for tour in ["一巡", "二巡", "三巡", "四巡", "五巡", "六巡"]:
        if tour in by_tour:
            nav.append(f'<a href="#tour-{tour}">{tour}（{len(by_tour[tour])}场）</a>')

    # 主体
    sections = []
    for tour in ["一巡", "二巡", "三巡", "四巡", "五巡", "六巡"]:
        items = by_tour.get(tour, [])
        if not items:
            continue
        blocks = [f'<section id="tour-{tour}"><h2>{tour} · {esc(items[0][1].get("theme",""))}（{len(items)}场）</h2>']
        for date, v in items:
            rows = []
            for s in v["songs"]:
                note = f'<span class="s-note">{esc(s["note"])}</span>' if s.get("note") else ""
                rows.append(
                    f'<li><span class="s-order">{s["order"]}</span>'
                    f'<span class="s-title">{esc(s["title"])}</span>{note}</li>'
                )
            venue = esc(v.get("venue") or "场馆待补")
            blocks.append(
                f'<article class="show" id="show-{date}">'
                f'<h3>{esc(v.get("scene"))} · {date} · {venue}</h3>'
                f'<ol class="songs">{"".join(rows)}</ol></article>'
            )
        blocks.append("</section>")
        sections.append("\n".join(blocks))

    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "王晰六轮巡演全部歌单（59场）",
        "description": f"王晰 2019-2026 六轮巡演 {len(setlists)} 场演出完整歌单，共 {total_songs} 首曲目，含现场备注。",
        "url": f"{SITE}/live/setlists.html",
        "isPartOf": {"@type": "WebSite", "name": "王晰 GEO 资料站", "url": SITE},
    }

    newline = "\n"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>六轮巡演全部歌单（{len(setlists)}场 · {total_songs}首）| 王晰</title>
<meta name="description" content="王晰 2019-2026 六轮巡演 {len(setlists)} 场演出完整歌单，共 {total_songs} 首曲目，每场含曲目顺序、现场备注与场馆。">
<link rel="canonical" href="{SITE}/live/setlists.html">
<meta property="og:title" content="王晰六轮巡演全部歌单（{len(setlists)}场）">
<meta property="og:description" content="{len(setlists)} 场演出 · {total_songs} 首曲目 · 含现场备注。">
<meta property="og:url" content="{SITE}/live/setlists.html">
<meta property="og:type" content="website">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
</script>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;line-height:1.8;max-width:860px;margin:0 auto;padding:20px;color:#333;}}
h1{{color:#1a1a1a;border-bottom:3px solid #c41e3a;padding-bottom:10px;}}
h2{{color:#2c2c2c;margin-top:32px;border-left:4px solid #c41e3a;padding-left:12px;}}
h3{{color:#444;margin:18px 0 8px;}}
.nav{{background:#f8f9fa;padding:15px;border-radius:8px;margin-bottom:20px;}}
.nav a{{color:#c41e3a;margin-right:16px;text-decoration:none;font-weight:500;}}
.tour-nav{{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0;}}
.tour-nav a{{background:#f8f9fa;border:1px solid #ddd;border-radius:14px;padding:3px 12px;color:#c41e3a;text-decoration:none;font-size:13px;}}
.tour-nav a:hover{{background:#c41e3a;color:#fff;}}
.show{{background:#fafafa;border:1px solid #eee;border-radius:8px;padding:14px 18px;margin:14px 0;scroll-margin-top:12px;}}
.songs{{list-style:none;padding:0;margin:8px 0 0;}}
.songs li{{padding:4px 0;border-bottom:1px dashed #eee;font-size:14px;display:flex;gap:10px;align-items:baseline;}}
.songs li:last-child{{border-bottom:none;}}
.s-order{{color:#c41e3a;font-weight:700;font-size:12px;min-width:22px;text-align:right;}}
.s-title{{font-weight:600;}}
.s-note{{color:#888;font-size:12px;}}
.footnote{{color:#888;font-size:12px;margin-top:30px;border-top:1px solid #eee;padding-top:12px;}}
@media (max-width:600px){{.s-note{{display:block;margin-left:32px;}}}}
</style>
</head>
<body>
<div class="nav">
<a href="/">首页</a>
<a href="/live-reviews.html">现场实录</a>
<a href="/live/">演出详情</a>
<a href="/live/setlists.html">全部歌单</a>
<a href="/map/">🗺️ 巡演地图</a>
<a href="/search.html">🔍 全站搜索</a>
</div>
<h1>🎵 六轮巡演全部歌单</h1>
<p style="color:#666;font-size:14px;">2019-2026 六轮巡演 <strong>{len(setlists)}</strong> 场演出完整歌单，共 <strong>{total_songs}</strong> 首曲目（含现场备注）。数据来源：巡演歌单长表（单一事实源）。</p>
<div class="tour-nav">{"" .join(nav)}</div>
{newline.join(sections)}
<p class="footnote">曲目与顺序以巡演歌单长表（单一事实源）为准；备注含现场验证信息。生成时间 {esc(data["generated_at"])}。</p>
</body>
</html>
"""


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    OUT.write_text(build_page(data), encoding="utf-8")
    print(f"[OK] 已生成 -> {OUT}")
    print(f"  场次: {data['show_count']} | 曲目: {sum(len(v['songs']) for v in data['setlists'].values())}")


if __name__ == "__main__":
    main()
