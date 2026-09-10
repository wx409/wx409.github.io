#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导航单一事实源：把全站根页面的顶部导航 + 底部全站索引统一成一份，幂等可重跑。

为什么需要它（第一性原理）：
  导航在 20+ 个生成器里各写一份 → 必然漂移（2026-09-08 总检：qa.html/story.html/jazz.html
  成孤儿页，voice.html/notifications.html 多数页缺失）。导航是**派生数据**，不是内容，
  必须由单一事实源生成，禁止手写多份。

机制：
  1. 顶部导航：用 <!-- NAV_START -->…<!-- NAV_END --> 标记包裹；已标记则替换，
     未标记但存在 <div class="nav">…</div> 则整块替换，都没有则在 <body> 后插入。
  2. 底部索引：用 <!-- FOOTER_NAV_START -->…<!-- FOOTER_NAV_END --> 标记包裹，
     自动列出仓库根目录全部页面（保证零孤儿页 + 爬虫可达）。
  3. 幂等：重复运行结果一致；--check 只报告不写入（可用于 CI/部署前置检查）。

用法：
  python project_b/build_nav.py            # 写入
  python project_b/build_nav.py --check    # 只检查是否需要更新（退出码 1 = 有漂移）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NAV_START = "<!-- NAV_START -->"
NAV_END = "<!-- NAV_END -->"
FOOT_START = "<!-- FOOTER_NAV_START -->"
FOOT_END = "<!-- FOOTER_NAV_END -->"

# 顶部导航（顺序即优先级）；href 一律用站点根绝对路径，根页/子页通用
NAV_ITEMS = [
    ("/index.html", "🏠 首页", ""),
    ("/live-reviews.html", "现场实录", ""),
    ("/live/", "演出详情", ""),
    ("/discography.html", "作品百科", ""),
    ("/songs.html", "歌曲库", ""),
    ("/live/setlists.html", "全部歌单", ""),
    ("/timeline.html", "生涯时间轴", ""),
    ("/data-timeline.html", "📈 数据时间线", ""),
    ("/story.html", "📖 数据故事", ""),
    ("/voice.html", "🎼 音域实测", "color:#a8323d;"),
    ("/skill.html", "🎙️ 唱功实测", "color:#a8323d;"),
    ("/stage.html", "🎤 舞台实测", ""),
    ("/dashboard/", "数据大屏", ""),
    ("/map/", "巡演地图", ""),
    ("/culture/index.html", "文化足迹", ""),
    ("/tavern/", "深夜小酒馆", ""),
    ("/city-guides.html", "城市攻略", ""),
    ("/academic.html", "学术研究", ""),
    ("/qa.html", "问答库", ""),
    ("/gallery.html", "视觉记录", ""),
    ("/notifications.html", "📋 自动通知", ""),
    ("/submit.html", "📮 投稿", "background:#c9a227;color:#fff;padding:4px 12px;border-radius:16px;"),
    ("/search.html", "🔍 全站搜索", "background:#c41e3a;color:#fff;padding:4px 12px;border-radius:16px;"),
]

# 底部全站索引分组（(分组名, [路径])）；路径必须存在才会输出
FOOTER_GROUPS = [
    ("核心", ["index.html", "live-reviews.html", "discography.html", "songs.html", "timeline.html",
              "data-timeline.html", "story.html", "notifications.html"]),
    ("数据", ["dashboard/", "map/", "data-timeline.html", "live/", "live/setlists.html",
              "data/music-index.html", "data/calibers.md", "data/kb/kb_digest.md"]),
    ("内容", ["voice.html", "skill.html", "stage.html", "academic.html", "qa.html", "jazz.html", "gallery.html", "city-guides.html",
              "culture/index.html", "tavern/", "live-reviews.html"]),
    ("关于", ["about.html", "submit.html", "search.html", "feed.xml", "sitemap.xml", "llms.txt",
              "robots.txt", "404.html"]),
]

SKIP = {"404.html", "live_template.html", "kb-semantic.html", "social_wall.html"}

# 底部索引的显示名（未列出的用文件名）
LABELS = {
    "index.html": "首页", "live-reviews.html": "现场实录", "discography.html": "作品百科",
    "songs.html": "歌曲库", "timeline.html": "生涯时间轴", "data-timeline.html": "数据时间线",
    "story.html": "数据故事", "notifications.html": "自动通知", "voice.html": "音域实测", "skill.html": "唱功实测", "stage.html": "舞台实测（综艺/晚会/商演）",
    "academic.html": "学术研究", "qa.html": "问答库", "jazz.html": "爵士专题",
    "gallery.html": "视觉记录", "city-guides.html": "城市攻略", "about.html": "关于本站",
    "submit.html": "投稿", "search.html": "全站搜索", "dashboard/": "数据大屏", "map/": "巡演地图",
    "live/": "演出详情目录", "live/setlists.html": "全部歌单", "data/music-index.html": "音乐数据周报",
    "data/kb/kb_digest.md": "知识库摘要", "data/calibers.md": "口径登记表（数字字典）", "culture/index.html": "文化足迹", "tavern/": "深夜小酒馆",
    "feed.xml": "RSS 订阅", "sitemap.xml": "站点地图", "llms.txt": "AI 摘要（llms.txt）",
    "robots.txt": "robots.txt", "404.html": "404 页",
}

# 处理范围（相对仓库根）：根页面 + 有统一导航的内容子目录；dashboard/map 为应用页（自带布局）不处理
PAGE_GLOBS = ["*.html", "culture/*.html", "data/*.html", "live/*.html", "tavern/*.html"]


def target_pages() -> list[Path]:
    """需要统一导航的页面清单（供本脚本与 audit_nav.py 共用，避免两处口径漂移）。"""
    out: list[Path] = []
    for g in PAGE_GLOBS:
        for p in sorted(ROOT.glob(g)):
            if p.name in SKIP or ".bak" in p.name or p.name.endswith(".utf8"):
                continue
            out.append(p)
    return out


def render_nav() -> str:
    lines = [NAV_START, '<div class="nav">']
    for href, label, style in NAV_ITEMS:
        st = f' style="{style}"' if style else ""
        lines.append(f'    <a href="{href}"{st}>{label}</a>')
    lines.append("</div>")
    lines.append(NAV_END)
    return "\n".join(lines)


def render_footer() -> str:
    parts = [FOOT_START,
             '<footer class="site-index" style="margin:40px auto;max-width:1100px;padding:18px 22px;'
             'border-top:1px solid #e5e5e5;font-size:13px;color:#666;line-height:2;">',
             '<strong style="color:#333;">🧭 全站索引</strong>'
             '<span style="color:#999;font-size:12px;">（本区块由 project_b/build_nav.py 自动生成，'
             '保证每个页面都有入口、可被爬虫抓取）</span>']
    for name, items in FOOTER_GROUPS:
        links = []
        for it in items:
            p = ROOT / it.rstrip("/")
            if not p.exists():
                continue
            label = LABELS.get(it, it.rstrip("/").split("/")[-1] or it)
            href = "/" + it
            links.append(f'<a href="{href}" style="color:#c41e3a;text-decoration:none;">{label}</a>')
        if links:
            parts.append(f'<div style="margin-top:6px;"><b>{name}：</b>' + " · ".join(links) + "</div>")
    parts.append("</footer>")
    parts.append(FOOT_END)
    return "\n".join(parts)


def update_page(path: Path, html: str) -> tuple[str, bool]:
    nav = render_nav()
    foot = render_footer()
    orig = html

    if NAV_START in html and NAV_END in html:
        html = re.sub(re.escape(NAV_START) + r".*?" + re.escape(NAV_END), lambda m: nav, html, flags=re.S)
    else:
        m = re.search(r'<div class="nav">.*?</div>', html, re.S)
        if m:
            html = html[:m.start()] + nav + html[m.end():]
        elif "<body" in html:
            # 插到 <body ...> 之后
            b = re.search(r"<body[^>]*>", html)
            html = html[:b.end()] + "\n" + nav + "\n" + html[b.end():]

    if FOOT_START in html and FOOT_END in html:
        html = re.sub(re.escape(FOOT_START) + r".*?" + re.escape(FOOT_END), lambda m: foot, html, flags=re.S)
    elif "</body>" in html:
        html = html.replace("</body>", foot + "\n</body>", 1)

    return html, html != orig


def main() -> None:
    ap = argparse.ArgumentParser(description="导航单一事实源生成器")
    ap.add_argument("--check", action="store_true", help="只检查是否有漂移，不写入")
    args = ap.parse_args()

    changed = []
    pages = target_pages()
    for p in pages:
        html = p.read_text(encoding="utf-8", errors="ignore")
        new, ch = update_page(p, html)
        if ch:
            changed.append(p.relative_to(ROOT).as_posix())
            if not args.check:
                p.write_text(new, encoding="utf-8")

    print("=" * 68)
    print("导航单一事实源（build_nav.py）")
    print("=" * 68)
    print(f"扫描页面：{len(pages)}")
    if changed:
        print(f"{'需更新' if args.check else '已更新'} {len(changed)} 个页面：")
        for c in changed:
            print("  -", c)
    else:
        print("全部已一致 ✅")
    if args.check and changed:
        sys.exit(1)


if __name__ == "__main__":
    main()
