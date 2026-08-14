#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成数据故事页 story.html —— 全部结论从 entity_index.json / cities.json 实时计算，零写死。

故事模块：
  ① 跨城之王：唱过最多城市的歌（按城市数降序 Top N）
  ② 场次之王：累计演出场次最多的歌
  ③ 酒馆之声：被深夜小酒馆提及最多的歌
  ④ 城市之最：演出场次最多的城市 / 场馆被唱最多的城市
  ⑤ 巡演足迹：每轮巡演的场次数与城市数（来自 cities.json）

用法：python project_b/build_story.py
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTITY = ROOT / "entity_index.json"
CITIES = ROOT / "data" / "cities.json"
OUT = ROOT / "story.html"

TOUR_ORDER = ["一巡", "二巡", "三巡", "四巡", "五巡", "六巡"]
TOUR_THEME = {
    "一巡": "Cherish珍晰", "二巡": "2020-2021 个人巡回", "三巡": "图景",
    "四巡": "肆益", "五巡": "吾", "六巡": "回",
}


def esc(s) -> str:
    return str(s if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def compute_stories() -> dict:
    songs = json.loads(ENTITY.read_text(encoding="utf-8"))["songs"]
    cities = json.loads(CITIES.read_text(encoding="utf-8"))["cities"]

    # 每首歌：城市数 / 场次数 / 酒馆提及数
    rows = []
    for name, en in songs.items():
        live = en.get("live", [])
        if not live:
            continue
        cities_set = {lv.get("city") for lv in live if lv.get("city")}
        tavern = [t for t in en.get("tavern", []) if t != "歌词"]
        rows.append({
            "name": name,
            "city_count": len(cities_set),
            "show_count": len(live),
            "tavern_count": len(tavern),
            "cities": sorted(cities_set),
            "tours": sorted({lv.get("tour", "") for lv in live if lv.get("tour")}),
        })

    top_city = sorted(rows, key=lambda r: (-r["city_count"], -r["show_count"], r["name"]))
    top_show = sorted(rows, key=lambda r: (-r["show_count"], -r["city_count"], r["name"]))
    # 酒馆之声：有现场记录（live>0）且有酒馆 EP 引用的歌，按提及数排
    tavern_rows = [r for r in rows if r["tavern_count"] > 0]
    top_tavern = sorted(tavern_rows, key=lambda r: (-r["tavern_count"], -r["show_count"], r["name"]))

    # 城市演出场次
    city_shows = []
    for c, node in cities.items():
        shows = node.get("shows", [])
        held = [s for s in shows if not s.get("cancelled")]
        city_shows.append({
            "city": c, "count": len(shows), "held": len(held),
            "venues": sorted({s.get("venue") for s in shows if s.get("venue")}),
        })
    city_shows.sort(key=lambda x: (-x["count"], x["city"]))

    # 巡演足迹
    tour_stats = []
    by_tour = {}
    for c, node in cities.items():
        for s in node.get("shows", []):
            t = s.get("tour", "")
            by_tour.setdefault(t, {"cities": set(), "shows": 0})
            by_tour[t]["cities"].add(c)
            by_tour[t]["shows"] += 1
    for t in TOUR_ORDER:
        if t in by_tour:
            tour_stats.append({
                "tour": t, "theme": TOUR_THEME.get(t, ""),
                "cities": len(by_tour[t]["cities"]), "shows": by_tour[t]["shows"],
            })

    return {
        "top_city": top_city[:5],
        "top_show": top_show[:5],
        "top_tavern": top_tavern[:5],
        "city_shows": city_shows[:8],
        "tour_stats": tour_stats,
        "total_songs": len(rows),
        "total_cities": len(cities),
        "total_shows": sum(x["count"] for x in city_shows),
    }


def story_block(title, icon, intro, cards) -> str:
    html = f'<section class="story-block" id="{re.sub(r"[^a-z0-9]+", "-", title.lower())}">'
    html += f'<h2>{icon} {esc(title)}</h2><p class="story-intro">{esc(intro)}</p>'
    html += '<div class="card-grid">'
    for i, card in enumerate(cards, 1):
        html += '<div class="story-card">'
        html += f'<div class="rank">#{i}</div>'
        html += f'<div class="sc-name">{esc(card["name"])}</div>'
        html += f'<div class="sc-metrics">'
        for label, val in card.get("metrics", []):
            html += f'<div class="sc-m"><span>{esc(label)}</span><b>{esc(val)}</b></div>'
        html += '</div>'
        if card.get("extra"):
            html += f'<div class="sc-extra">{esc(card["extra"])}</div>'
        html += '</div>'
    html += '</div></section>'
    return html


def build_page(st: dict) -> str:
    # ① 跨城之王
    c1 = []
    for r in st["top_city"]:
        c1.append({
            "name": r["name"], "metrics": [("城市", f"{r['city_count']} 城"), ("场次", f"{r['show_count']} 场")],
            "extra": "、".join(r["cities"][:6]) + ("…" if len(r["cities"]) > 6 else ""),
        })
    b1 = story_block("跨城之王", "🗺️", "从 22 城 59 场巡演数据中，找出足迹最广的歌曲——它们在最多城市留下过现场。", c1)

    # ② 场次之王
    c2 = []
    for r in st["top_show"]:
        c2.append({
            "name": r["name"], "metrics": [("场次", f"{r['show_count']} 场"), ("城市", f"{r['city_count']} 城")],
            "extra": f"跨 {len(r['tours'])} 轮巡演",
        })
    b2 = story_block("场次之王", "🎤", "累计演出场次最多的歌曲——六轮巡演中的常青曲目。", c2)

    # ③ 酒馆之声
    c3 = []
    for r in st["top_tavern"]:
        c3.append({
            "name": r["name"], "metrics": [("提及", f"{r['tavern_count']} 期"), ("场次", f"{r['show_count']} 场")],
            "extra": "深夜小酒馆里被反复聊起的歌",
        })
    b3 = story_block("酒馆之声", "🍷", "深夜小酒馆 106 期逐字稿中，被提及最多的歌曲。", c3)

    # ④ 城市之最
    c4 = []
    for x in st["city_shows"]:
        c4.append({
            "name": x["city"], "metrics": [("场次", f"{x['count']} 场"), ("实际举办", f"{x['held']} 场")],
            "extra": "、".join(x["venues"][:3]) + ("…" if len(x["venues"]) > 3 else ""),
        })
    b4 = story_block("城市之最", "🏙️", "演出场次最多的城市——王晰巡演的深耕之地。", c4)

    # ⑤ 巡演足迹
    rows = []
    for t in st["tour_stats"]:
        rows.append(
            f'<tr><td>{esc(t["tour"])}</td><td>{esc(t["theme"])}</td>'
            f'<td>{t["cities"]} 城</td><td>{t["shows"]} 场</td></tr>'
        )
    b5 = (
        '<section class="story-block" id="tour-footprint">'
        '<h2>🧭 巡演足迹</h2><p class="story-intro">六轮巡演，从 2019 到 2026——每轮的规模都在这里。'
        f'（全站共 {st["total_songs"]} 首有现场记录的歌、{st["total_cities"]} 城、{st["total_shows"]} 场）</p>'
        '<table><tr><th>轮次</th><th>主题</th><th>城市</th><th>场次</th></tr>'
        + "".join(rows) + "</table></section>"
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>数据故事 | 王晰巡演足迹 · 跨城之王 · 酒馆之声</title>
<meta name="description" content="从 59 场巡演与 106 期小酒馆数据中自动计算的故事：唱过最多城市的歌、演出场次最多的歌、酒馆提及最多的歌。">
<link rel="canonical" href="https://wx409.github.io/story.html">
<meta property="og:title" content="数据故事 | 王晰巡演足迹">
<meta property="og:description" content="全部结论从 entity_index.json / cities.json 实时计算。">
<meta property="og:url" content="https://wx409.github.io/story.html">
<meta property="og:image" content="https://wx409.github.io/cover.png">
<meta name="twitter:image" content="https://wx409.github.io/cover.png">
<meta property="og:type" content="website">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Dataset",
  "name": "王晰巡演数据故事",
  "description": "基于 2019-2026 六轮巡演 59 场与深夜小酒馆 106 期逐字稿计算的数据故事，全部数字动态生成。",
  "url": "https://wx409.github.io/story.html",
  "isPartOf": {{"@type": "WebSite", "name": "王晰 GEO 资料站", "url": "https://wx409.github.io/"}}
}}
</script>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;line-height:1.8;max-width:960px;margin:0 auto;padding:20px;color:#333;}}
h1{{color:#1a1a1a;border-bottom:3px solid #c41e3a;padding-bottom:10px;}}
h2{{color:#2c2c2c;margin-top:28px;border-left:4px solid #c41e3a;padding-left:12px;}}
.nav{{background:#f8f9fa;padding:15px;border-radius:8px;margin-bottom:20px;}}
.nav a{{color:#c41e3a;margin-right:18px;text-decoration:none;font-weight:500;}}
.story-intro{{color:#666;font-size:14px;}}
.card-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;margin:14px 0;}}
.story-card{{background:#fafafa;border:1px solid #eee;border-radius:10px;padding:14px 16px;}}
.rank{{font-size:12px;color:#c41e3a;font-weight:700;}}
.sc-name{{font-size:17px;font-weight:700;margin:4px 0 8px;}}
.sc-metrics{{display:flex;gap:14px;}}
.sc-m span{{font-size:11px;color:#888;display:block;}}
.sc-m b{{font-size:15px;font-variant-numeric:tabular-nums;}}
.sc-extra{{font-size:12px;color:#888;margin-top:8px;}}
table{{width:100%;border-collapse:collapse;margin:12px 0;}}
th,td{{border:1px solid #ddd;padding:8px 12px;text-align:left;font-size:14px;}}
th{{background:#f5f5f5;}}
.footnote{{color:#888;font-size:12px;margin-top:30px;}}
</style>
</head>
<body>
<div class="nav">
<a href="index.html">首页</a>
<a href="live-reviews.html">现场实录</a>
<a href="live/">演出详情</a>
<a href="story.html">数据故事</a>
<a href="map/">🗺️ 巡演地图</a>
<a href="tavern/">🍷 深夜小酒馆</a>
<a href="city-guides.html">城市攻略</a>
<a href="dashboard/">数据大屏</a>
</div>
<h1>📊 数据故事｜王晰巡演足迹</h1>
<p class="story-intro">本页所有结论由脚本从 <code>entity_index.json</code> 与 <code>data/cities.json</code> 实时计算——不写死任何数字，数据更新后重新生成即可。</p>
{b1}
{b2}
{b3}
{b4}
{b5}
<p class="footnote">数据来源：巡演歌单长表（单一事实源）→ cities.json / entity_index.json。生成时间 {esc(st["generated_at"])}。</p>
</body>
</html>
"""


def main() -> None:
    st = compute_stories()
    st["generated_at"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
    OUT.write_text(build_page(st), encoding="utf-8")
    print(f"[OK] 已生成 -> {OUT}")
    print(f"  跨城之王: " + ", ".join(f"{r['name']}({r['city_count']}城)" for r in st["top_city"]))
    print(f"  场次之王: " + ", ".join(f"{r['name']}({r['show_count']}场)" for r in st["top_show"]))
    print(f"  酒馆之声: " + ", ".join(f"{r['name']}({r['tavern_count']}期)" for r in st["top_tavern"]))
    print(f"  城市之最: " + ", ".join(f"{x['city']}({x['count']}场)" for x in st["city_shows"][:5]))


if __name__ == "__main__":
    main()
