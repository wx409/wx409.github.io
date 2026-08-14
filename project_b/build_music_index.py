#!/usr/bin/env python3
"""从 dashboard/dashboard_data.json 生成 data/music-index.md 与 .html。

目标：让「音乐数据」页与数据大屏（dashboard）使用同一数据源，消除数字矛盾。
运行：python project_b/build_music_index.py
"""
import json
from pathlib import Path

WEBSITE = Path(__file__).resolve().parent.parent
SRC = WEBSITE / 'dashboard' / 'dashboard_data.json'
OUT_MD = WEBSITE / 'data' / 'music-index.md'
OUT_HTML = WEBSITE / 'data' / 'music-index.html'

SUMMARY_TITLES = {
    'sankey': '作品成长生态',
    'weekend_premium': '听众时间偏好',
    'timeline': '月度竞争格局',
    'waterfall': '排名变化瀑布',
    'tour_song_effects': '巡演歌曲效应',
}


def _sign(v):
    return '+' if v > 0 else ''


def build_md(d):
    ts = d.get('timestamp', '')
    date_str = ts.split(' ')[0]
    lines = [
        '# 王晰音乐数据趋势',
        f'> 数据更新至 {ts} · 数据范围 {d.get("date_range", "")} · 来源：[数据大屏](https://wx409.github.io/dashboard/)',
        '',
        '## 核心指标',
        '| 指标 | 数值 |',
        '|------|------|',
        f'| 追踪歌曲 | {d.get("total_songs")} 首 |',
        f'| 活跃歌曲 | {d.get("active_songs")} 首（活跃率 {d.get("active_rate")}%） |',
        f'| 数据完整率 | {d.get("complete_rate")}% |',
        '',
        '## 近 7 日平均指数',
        '| 日期 | 平均指数 | 覆盖歌曲 |',
        '|------|---------|---------|',
    ]
    for r in d.get('recent_7days', []):
        lines.append(f'| {r.get("date")} | {r.get("avg_index")} | {r.get("total_songs")} 首 |')

    lines += ['', '## 当前热点歌曲 TOP10', '| 歌名 | 变化幅度 | 标签 |', '|------|---------|------|']
    for s in d.get('top_songs', []):
        trend = s.get('trend', 0)
        lines.append(f'| {s.get("name")} | {_sign(trend)}{trend}% | {s.get("tag")} |')

    lines += ['', '## 异常监测']
    for a in d.get('daily_anomalies', []):
        lines.append(f'- **{a.get("song")}**：{a.get("type")}（{a.get("desc")}）')

    lines += ['', '## 趋势洞察']
    for key, title in SUMMARY_TITLES.items():
        text = d.get('chart_summaries', {}).get(key)
        if text:
            lines.append(f'- **{title}**：{text}')

    lines += [
        '',
        f'> 本页数据取自 [dashboard_data.json](https://wx409.github.io/dashboard/dashboard_data.json)，与数据大屏保持一致。',
    ]
    return '\n'.join(lines) + '\n'


def build_html(d, md_text):
    ts = d.get('timestamp', '')
    date_str = ts.split(' ')[0]
    desc = f'王晰音乐数据趋势 · 更新至 {ts}。追踪 {d.get("total_songs")} 首歌曲、活跃 {d.get("active_songs")} 首，含热点TOP10与趋势洞察，与数据大屏一致。'

    # 核心指标卡
    cards = (
        f'<div class="stat"><div class="num">{d.get("total_songs")}</div><div class="lbl">追踪歌曲（首）</div></div>'
        f'<div class="stat"><div class="num">{d.get("active_songs")}</div><div class="lbl">活跃歌曲（首）</div></div>'
        f'<div class="stat"><div class="num">{d.get("active_rate")}%</div><div class="lbl">活跃率</div></div>'
        f'<div class="stat"><div class="num">{d.get("complete_rate")}%</div><div class="lbl">数据完整率</div></div>'
    )

    # 近7日
    rows7 = ''.join(
        f'<tr><td>{r.get("date")}</td><td>{r.get("avg_index")}</td><td>{r.get("total_songs")}</td></tr>'
        for r in d.get('recent_7days', [])
    )

    # 热点 TOP10
    rows_top = ''
    for i, s in enumerate(d.get('top_songs', []), 1):
        trend = s.get('trend', 0)
        rows_top += (
            f'<tr><td>{i}</td><td>{s.get("name")}</td>'
            f'<td>{_sign(trend)}{trend}%</td><td>{s.get("tag")}</td></tr>'
        )

    # 异常
    anomalies = ''.join(
        f'<li><strong>{a.get("song")}</strong>：{a.get("type")}（{a.get("desc")}）</li>'
        for a in d.get('daily_anomalies', [])
    )

    # 洞察
    insights = ''
    for key, title in SUMMARY_TITLES.items():
        text = d.get('chart_summaries', {}).get(key)
        if text:
            insights += f'<p><strong>{title}</strong>：{text}</p>\n        '

    jsonld = json.dumps({
        '@context': 'https://schema.org',
        '@type': 'Dataset',
        'name': '王晰音乐数据趋势',
        'description': desc,
        'dateModified': date_str,
        'temporalCoverage': d.get('date_range', ''),
        'isBasedOn': 'https://wx409.github.io/dashboard/dashboard_data.json',
        'publisher': {'@type': 'Organization', 'name': '王晰GEO资料站', 'url': 'https://wx409.github.io/'},
    }, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>王晰音乐数据趋势 | 数据大屏同步</title>
    <meta name="description" content="{desc}">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; line-height: 1.8; max-width: 820px; margin: 0 auto; padding: 20px; color: #333; }}
        h1 {{ color: #1a1a1a; border-bottom: 3px solid #c41e3a; padding-bottom: 10px; }}
        h2 {{ color: #2c2c2c; margin-top: 30px; border-left: 4px solid #c41e3a; padding-left: 12px; }}
        .nav {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
        .nav a {{ color: #c41e3a; margin-right: 20px; text-decoration: none; font-weight: 500; }}
        .stats {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 20px 0; }}
        .stat {{ flex: 1 1 120px; background: #fafafa; border-top: 4px solid #c41e3a; border-radius: 8px; padding: 14px; text-align: center; }}
        .stat .num {{ font-size: 26px; font-weight: 700; color: #c41e3a; }}
        .stat .lbl {{ font-size: 13px; color: #666; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; font-size: 14px; }}
        th, td {{ border: 1px solid #e0e0e0; padding: 8px 10px; text-align: left; }}
        th {{ background: #f8f9fa; }}
        blockquote {{ color: #666; border-left: 4px solid #c41e3a; padding-left: 15px; margin: 20px 0; }}
        a {{ color: #c41e3a; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .footer {{ color: #888; font-size: 13px; margin-top: 40px; border-top: 1px solid #eee; padding-top: 15px; }}
    </style>
    <script type="application/ld+json">{jsonld}</script>
    <link rel="canonical" href="https://wx409.github.io/data/music-index.html">
</head>
<body>
    <div class="nav">
        <a href="../index.html">首页</a>
        <a href="../live-reviews.html">现场实录</a>
        <a href="../discography.html">作品百科</a>
        <a href="../academic.html">学术研究</a>
        <a href="../gallery.html">视觉记录</a>
        <a href="../city-guides.html">城市攻略</a>
        <a href="music-index.html">音乐数据</a>
        <a href="../culture/index.html">文化足迹</a>
    </div>

    <h1>王晰音乐数据趋势</h1>
    <blockquote>数据更新至 {ts} · 数据范围 {d.get("date_range", "")} · 与<a href="../dashboard/">数据大屏</a>同步</blockquote>

    <div class="stats">{cards}</div>

    <h2>近 7 日平均指数</h2>
    <table><tr><th>日期</th><th>平均指数</th><th>覆盖歌曲</th></tr>{rows7}</table>

    <h2>当前热点歌曲 TOP10</h2>
    <table><tr><th>#</th><th>歌名</th><th>变化幅度</th><th>标签</th></tr>{rows_top}</table>

    <h2>异常监测</h2>
    <ul>{anomalies}</ul>

    <h2>趋势洞察</h2>
        {insights}

    <div class="footer">
        最后更新：{date_str} · 数据来源：<a href="../dashboard/dashboard_data.json">dashboard_data.json</a> · 本页与数据大屏使用同一数据源
    </div>
</body>
</html>'''


def main():
    if not SRC.exists():
        print(f'[!] 未找到数据源: {SRC}')
        return
    d = json.loads(SRC.read_text(encoding='utf-8'))
    md_text = build_md(d)
    OUT_MD.write_text(md_text, encoding='utf-8')
    OUT_HTML.write_text(build_html(d, md_text), encoding='utf-8')
    print(f'[OK] 已生成 {OUT_MD.relative_to(WEBSITE)}')
    print(f'[OK] 已生成 {OUT_HTML.relative_to(WEBSITE)}')


if __name__ == '__main__':
    main()
