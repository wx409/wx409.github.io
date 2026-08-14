#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 Atom Feed feed.xml —— 站点内容更新订阅（RSS/Atom 1.0）。

收录内容（按时间倒序，取最近 N 条）：
  - 小酒馆 EP 页（106 期，tavern/ep/*.html，含主题/时长）
  - live 演出详情页（live/*.html）
  - 站点主要页面（story/city-guides/现场实录 等，静态条目）

用法：python project_b/build_feed.py
输出：D:\\wx409.github.io\\feed.xml
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
EP_DIR = ROOT / "tavern" / "ep"
LIVE_DIR = ROOT / "live"
OUT = ROOT / "feed.xml"
SITE = "https://wx409.github.io"
MAX_ITEMS = 60

# 静态页面条目（title, url, date, summary）
STATIC_ITEMS = [
    ("数据故事｜王晰巡演足迹", "story.html", "2026-08-14", "从 59 场巡演与 106 期小酒馆数据中自动计算的故事：跨城之王、酒馆之声、巡演足迹。"),
    ("城市攻略｜22 城观演指南", "city-guides.html", "2026-08-14", "22 城演出历史、常唱歌曲、酒馆声音与网络观演贴士。"),
    ("现场实录｜六轮巡演索引", "live-reviews.html", "2026-08-14", "2019-2026 六轮巡演全部场次索引与听众反馈。"),
    ("巡演地图｜22 城 59 场", "map/", "2026-08-14", "Leaflet 巡演地图：场馆、日期、巡次与数据效应。"),
    ("数据大屏｜QQ音乐指数监测", "dashboard/", "2026-08-14", "382 首歌曲指数追踪、巡演效应与数据谱系。"),
]


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=False)


def parse_ep_meta(path: Path) -> dict | None:
    """从 EP 页提取 title/date/desc/主题"""
    t = path.read_text(encoding="utf-8")
    title = ""
    m = re.search(r"<title>(.*?)｜深夜小酒馆", t)
    if m:
        title = m.group(1).strip()
    desc = ""
    m = re.search(r'<meta name="description" content="([^"]*)"', t)
    if m:
        desc = m.group(1)
    # 时长
    dur = ""
    m = re.search(r"(\d+分\d+秒)", t)
    if m:
        dur = m.group(1)
    # 主题标签
    tags = re.findall(r'class="topic-tag[^"]*"[^>]*>([^<]+)</a>', t)
    return {"title": title, "url": f"{SITE}/tavern/ep/{quote(path.stem)}.html",
            "date": "2026-08-14", "summary": desc, "tags": tags, "dur": dur}


def build_feed() -> str:
    items = []

    # EP 页
    for f in sorted(EP_DIR.glob("*.html")):
        meta = parse_ep_meta(f)
        if meta and meta["title"]:
            tag_txt = " · ".join(meta["tags"]) if meta["tags"] else ""
            summary = meta["summary"]
            if meta["dur"]:
                summary = f"{summary}（时长 {meta['dur']}）"
            items.append({
                "title": f"小酒馆 {meta['title']}",
                "url": meta["url"],
                "date": meta["date"],
                "summary": summary,
                "tags": tag_txt,
            })

    # live 页
    for f in sorted(LIVE_DIR.glob("*.html")):
        if f.name == "index.html":
            continue
        t = f.read_text(encoding="utf-8")
        m = re.search(r"<title>(.*?)</title>", t)
        title = m.group(1).strip() if m else f.stem
        m = re.search(r'<meta name="description" content="([^"]*)"', t)
        desc = m.group(1) if m else ""
        m = re.search(r'<meta name="live-date" content="([^"]*)"', t)
        date = m.group(1) if m else "2026-08-14"
        items.append({
            "title": title,
            "url": f"{SITE}/live/{quote(f.name)}",
            "date": date,
            "summary": desc,
            "tags": "演出实录",
        })

    # 静态页
    for title, url, date, summary in STATIC_ITEMS:
        items.append({"title": title, "url": f"{SITE}/{url}", "date": date, "summary": summary, "tags": ""})

    # 按日期倒序（EP 无日期则按文件名序兜底），截取最近 N 条
    items.sort(key=lambda x: x["date"], reverse=True)
    items = items[:MAX_ITEMS]

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = []
    for it in items:
        summary = esc(it["summary"])
        if it["tags"]:
            summary += f"<br/>标签：{esc(it['tags'])}"
        entries.append(
            "  <entry>\n"
            f"    <title>{esc(it['title'])}</title>\n"
            f"    <link href=\"{esc(it['url'])}\" rel=\"alternate\" type=\"text/html\"/>\n"
            f"    <id>{esc(it['url'])}</id>\n"
            f"    <updated>{esc(it['date'])}T00:00:00Z</updated>\n"
            f"    <summary type=\"html\">{summary}</summary>\n"
            "  </entry>"
        )

    newline = "\n"
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>王晰 GEO 资料站 · 更新订阅</title>
  <subtitle>华语男低音歌手王晰的垂直资料站：巡演、小酒馆、数据大屏与城市攻略更新。</subtitle>
  <link href="{SITE}/feed.xml" rel="self" type="application/atom+xml"/>
  <link href="{SITE}/" rel="alternate" type="text/html"/>
  <id>{SITE}/feed.xml</id>
  <updated>{now}</updated>
  <author><name>王晰 GEO 资料站</name></author>
  <generator uri="https://wx409.github.io/" version="1.0">wangxi-geo-builder</generator>
{newline.join(entries)}
</feed>
"""


def main() -> None:
    OUT.write_text(build_feed(), encoding="utf-8")
    print(f"[OK] 已生成 -> {OUT}")
    import xml.dom.minidom
    try:
        xml.dom.minidom.parseString(OUT.read_text(encoding="utf-8"))
        print("[OK] XML 语法验证通过")
    except Exception as e:
        print(f"[X] XML 解析失败: {e}")
        raise


if __name__ == "__main__":
    main()
