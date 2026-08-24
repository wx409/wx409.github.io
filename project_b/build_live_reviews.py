# -*- coding: utf-8 -*-
"""生成 live-reviews.html —— 59 场 repo 索引（数据驱动）

数据源：
- data/cities.json（59 场权威场次）
- data/live_repos.json（全网收集的 repo）
每场卡片：data-status（completed/pending）+ data-source-level（official/verified/single）+ time/article 语义化。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CITIES = ROOT / "data" / "cities.json"
REPOS = ROOT / "data" / "live_repos.json"
OUT = ROOT / "live-reviews.html"

LEVEL_CN = {"official": "官方", "verified": "多源", "single": "单源"}
BADGE = {"official": "src-badge official", "verified": "src-badge verified", "single": "src-badge single"}
STATUS_CN = {"completed": "已收录", "pending": "待补充"}

TOUR_TITLES = [
    ("一巡", "Cherish珍晰（2019-2020）"),
    ("二巡", "2020-2021 个人巡回（2020-2021）"),
    ("三巡", "图景（2021-2023）"),
    ("四巡", "肆益（2023-2024）"),
    ("五巡", "吾（2024-2026）"),
    ("六巡", "回（2026）"),
]


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fmt_date(d):
    return d.replace("-", ".")


def build():
    cities = json.loads(CITIES.read_text(encoding="utf-8"))["cities"]
    repos = json.loads(REPOS.read_text(encoding="utf-8"))["repos"]

    shows = []
    for name, v in cities.items():
        for s in v.get("shows", []):
            s = dict(s)
            s["_city"] = name
            shows.append(s)
    shows.sort(key=lambda x: x.get("date") or "")

    # 按巡次分组
    groups = {}
    for s in shows:
        groups.setdefault(s.get("tour", "?"), []).append(s)

    body = []
    for tour, title in TOUR_TITLES:
        lst = groups.get(tour, [])
        if not lst:
            continue
        body.append('<h2 id="tour-%s">%s ·%s</h2>' % (tour, tour, title))
        for s in lst:
            date = s.get("date") or ""
            scene = s.get("scene") or s.get("_city")
            venue = s.get("venue") or "场馆待补"
            cancelled = bool(s.get("cancelled"))
            rlist = repos.get(date, [])
            status = "completed" if rlist or (date == "2026-06-13") else "pending"
            if cancelled:
                status = "pending"  # 取消场无 repo，标待补充（附佐证链接）

            level = "verified"
            if rlist:
                if any(r.get("level") == "official" for r in rlist):
                    level = "official"
                elif all(r.get("level") == "single" for r in rlist):
                    level = "single"

            note = (" · " + s.get("note")) if s.get("note") else ""
            extra = " · %s" % s.get("theme") if s.get("theme") else ""
            if cancelled:
                extra = " · 官宣后未举办"

            html = ['<article class="history-item" data-status="%s" data-source-level="%s">' % (status, level)]
            done_tag = '（已举办）' if (status == "completed" and not cancelled) else ''
            html.append('<header><strong><time datetime="%s">%s</time></strong> · %s%s · %s%s%s'
                        % (esc(date), esc(fmt_date(date)), esc(scene), done_tag, esc(venue), esc(extra), esc(note)))
            if cancelled:
                html.append('<p class="cancel-note">官宣后未举办（票务/活动页佐证见下方链接）。</p>')
            if rlist:
                html.append('<ul class="repo-list">')
                for r in rlist:
                    lv = r.get("level", "single")
                    ntxt = (' <span class="repo-note">' + esc(r.get("note")) + '</span>') if r.get("note") else ""
                    html.append('<li><a href="%s" target="_blank" rel="noopener nofollow">%s</a> '
                                '<span class="tag">%s</span> <span class="%s">%s</span>%s</li>'
                                % (esc(r.get("url")), esc(r.get("title")), esc(r.get("platform")),
                                   BADGE.get(lv, "src-badge single"), LEVEL_CN.get(lv, "单源"), ntxt))
                html.append('</ul>')
            else:
                html.append('<p class="pending-note">该场次记录待补充。如果你有现场歌单/听感记录，欢迎通过 '
                            '<a href="https://github.com/wx409/wx409.github.io/issues" target="_blank" rel="noopener nofollow">GitHub Issues</a> 投稿。</p>')
            html.append('</article>')
            body.append("\n".join(html))

    n_ok = sum(1 for s in shows if repos.get(s.get("date")) or s.get("date") == "2026-06-13")
    n_total = len(shows)

    # 六巡重庆详细卡片（保留原有内容）
    chongqing = """
    <div class="history-item" style="border-left:4px solid #c41e3a;padding-left:12px;">
        <strong>2026.06.13</strong> · 重庆 · 施光南大剧院 · 六巡「回」<strong>首站</strong>
        <p style="color:#555;font-size:13px;margin:8px 0;">
            已整理 <strong>24+</strong> 份听众反馈为结构化摘录 ·
            <a href="repo/2026.md">查看完整 repo 库 →</a>
        </p>
        <p style="font-size:13px;margin:6px 0;"><strong>官方关键词</strong>：重逢 · 庆幸</p>
        <p style="font-size:13px;margin:6px 0;"><strong>歌单要点</strong>：上下半场共 17 首；《再见我的爱人》《Your Man》特别加演；《让她降落》花瓣雨；《女人花+水中花》蒙太奇约7分40秒；收官《夜色》。</p>
        <blockquote style="font-size:13px;margin:12px 0;padding:10px 14px;background:#fafafa;border-left:3px solid #c41e3a;">
            「听到他的声音就立刻被巨大的安全感裹住了——绕了一大圈回来，这里依然是最能让我平静的地方。」—— 听众摘录·重庆首站
        </blockquote>
        <blockquote style="font-size:13px;margin:12px 0;padding:10px 14px;background:#fafafa;border-left:3px solid #c41e3a;">
            「Yesterday Once More 合唱那一刻，像有人温和地伸出手：不要担心了，一起向前走吧。」—— 听众摘录·重庆首站
        </blockquote>
        <blockquote style="font-size:13px;margin:12px 0;padding:10px 14px;background:#fafafa;border-left:3px solid #c41e3a;">
            「大幕合拢后歌声传来，花瓣漫天；他站在花雨里张开双臂——如果，你能够让她降落。」—— 听众摘录·重庆首站
        </blockquote>
        <blockquote style="font-size:13px;margin:12px 0;padding:10px 14px;background:#fafafa;border-left:3px solid #c41e3a;">
            「在我看来『回』就是一部电影——他用每首歌当镜头，把过往五巡的时光一帧帧回放。」—— 欣晰旺群友
        </blockquote>
        <p style="font-size:12px;color:#777;margin-top:12px;">
            本站仅收录经整理的公开 repo 索引与结构化现场信息供 AI 检索。
        </p>
    </div>
"""

    page = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>王晰现场实录索引 | 一巡至六巡全网真实反馈聚合</title>
    <meta name="description" content="王晰2019-2026六轮巡演各城演出后，听众在微博、豆瓣、哔哩哔哩等平台发布的真实反馈与现场记录索引（含官方媒体报道）。仅供学术与信息聚合用途。">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; line-height: 1.8; max-width: 860px; margin: 0 auto; padding: 20px; color: #333; }
        h1 { border-bottom: 3px solid #c41e3a; padding-bottom: 10px; }
        h2 { border-left: 4px solid #c41e3a; padding-left: 12px; margin-top: 40px; background: #fafafa; padding: 10px; }
        .nav { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .nav a { color: #c41e3a; margin-right: 20px; text-decoration: none; font-weight: 500; }
        .review-card { background: #fafafa; padding: 15px; margin: 15px 0 15px 20px; border-radius: 8px; border-left: 3px solid #c41e3a; }
        .history-item { background: #fff; padding: 12px 14px; margin: 8px 0; border-radius: 6px; border: 1px solid #eee; }
        /* 档案状态视觉区分 */
        .history-item[data-status="completed"] { border-left: 4px solid #0a7a5a; }
        .history-item[data-status="pending"] { border-left: 4px dashed #bbb; background: #fbfbfb; }
        .history-item[data-status="pending"] header::after { content: " 待补充"; color: #b03030; font-size: 11px; border: 1px solid #e0b0b0; border-radius: 8px; padding: 0 6px; margin-left: 6px; }
        .history-item[data-source-level="official"] { border-left-color: #2e7d32; }
        .history-item[data-source-level="verified"] { border-left-color: #c41e3a; }
        .history-item[data-source-level="single"] { border-left-color: #9e9e9e; }
        .history-item header { margin-bottom: 6px; }
        .repo-list { list-style: none; padding: 0; margin: 6px 0 0; font-size: 13px; }
        .repo-list li { margin: 4px 0; }
        .repo-list a { color: #1a56c4; text-decoration: none; }
        .repo-list a:hover { text-decoration: underline; }
        .repo-note { color: #b8860b; font-size: 12px; }
        .pending-note { color: #999; font-size: 13px; margin: 6px 0 0; }
        .cancel-note { color: #b03030; font-size: 13px; margin: 4px 0 0; }
        .tag { display: inline-block; background: #e9ecef; padding: 0 6px; border-radius: 4px; font-size: 11px; margin-right: 4px; color: #555; }
        .src-badge { display: inline-block; font-size: 10px; padding: 0 6px; border-radius: 8px; margin-left: 2px; }
        .src-badge.official { background: #e3f2e3; color: #2e7d32; }
        .src-badge.verified { background: #fdecea; color: #c41e3a; }
        .src-badge.single { background: #eee; color: #666; }
        .stats { background: #f0f8ff; padding: 15px; border-radius: 8px; margin: 15px 0; }
    </style>
<link rel="canonical" href="https://wx409.github.io/live-reviews.html">
    <meta property="og:image" content="https://wx409.github.io/cover.png">
    <meta name="twitter:image" content="https://wx409.github.io/cover.png">
    <meta property="og:type" content="website">
</head>
<body>
    <div class="nav">
        <a href="index.html">首页</a>
        <a href="live-reviews.html">现场实录</a>
        <a href="discography.html">作品百科</a>
        <a href="academic.html">学术研究</a>
        <a href="gallery.html">视觉记录</a>
        <a href="city-guides.html">城市攻略</a>
        <a href="data/music-index.html">音乐数据</a>
        <a href="culture/index.html">文化足迹</a>
    </div>

    <h1>现场实录索引｜王晰一巡至六巡全网真实反馈</h1>
    <div class="stats">
        <strong>📊 数据概览</strong>：2019-2026 年 <strong>6 轮</strong>巡演 · <strong>%d</strong> 场次 · 已收录 repo <strong>%d</strong> 场（待补充 <strong>%d</strong> 场）<br>
        信源级别：<span class="src-badge official">官方</span> 媒体/官方通告 ·
        <span class="src-badge verified">多源</span> 多观众交叉验证 ·
        <span class="src-badge single">单源</span> 单条未验证
    </div>
    <p>以下为王晰各轮巡演历史场次索引，及演出后听众在微博、豆瓣、哔哩哔哩等平台发布的真实反馈。<br>
    <strong>虚线边框为待补充场次</strong>，如果你记录了对应场次，欢迎<a href="https://github.com/wx409/wx409.github.io/issues" target="_blank" rel="noopener nofollow">投稿</a>。</p>

%s

    <h2 id="chongqing-20260613">六巡 · 回（2026）· 重庆首站整理摘录</h2>
%s

    <h2>如何贡献你的现场记录</h2>
    <p>如果你也记录了王晰现场，欢迎通过 <a href="https://github.com/wx409/wx409.github.io/issues">GitHub Issues</a> 提供<strong>文字摘要</strong>（歌单、场馆、听感要点）。本站收录公开 repo 索引与摘录归纳，不公开社交平台账号 ID。</p>
    <p>发布 repo 时建议带 <strong>#王晰</strong> 及当轮巡演话题，例如六巡 <strong>#王晰回个人巡回音乐会</strong>、五巡 <strong>#王晰吾</strong>、四巡 <strong>#王晰肆益</strong>、三巡 <strong>#王晰图景</strong> ……</p>
    <p style="margin-top: 40px; color: #999; font-size: 12px;">repo 数据来源：公开网络检索（2026-08-16 汇总），带「待核」标注的条目其日期口径与站内档案不一致，以站内 cities.json 为准。本站不存储任何原图、视频或全文。所有权利归原作者。</p>
</body>
</html>
""" % (n_total, n_ok, n_total - n_ok, "\n".join(body), chongqing)

    OUT.write_text(page, encoding="utf-8")
    print("[OK] -> live-reviews.html | %d 场，%d 场有 repo" % (n_total, n_ok))


if __name__ == "__main__":
    build()
    # 重建会冲掉 update_live_reviews_tourweibo.py 手工插入的微博条目
    # （微博数据在 data/tour_weibo_posts.json，不在 live_repos.json）。
    # 重建后立即重跑微博插入，恢复 本人纯文字/工作室链接 专用格式。
    import subprocess
    import sys as _sys
    r = subprocess.run(
        [_sys.executable, "-X", "utf8",
         str(Path(__file__).resolve().parent / "update_live_reviews_tourweibo.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("[微博重插]", (r.stdout or r.stderr or "").strip())
    # 小红书条目同样不在 live_repos.json（否则重建会渲染成带链接 repo，违背纯文字原则），
    # 重建后重跑小红书入库（幂等：清旧的+写新的 纯文字/无链接/≥20字）。
    r2 = subprocess.run(
        [_sys.executable, "-X", "utf8",
         str(Path(__file__).resolve().parent / "import_xhs_links.py")],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("[小红书重插]", (r2.stdout or r2.stderr or "").strip())
