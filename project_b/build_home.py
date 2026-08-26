# -*- coding: utf-8 -*-
"""首页重构 build_home.py：方案 B 五层架构 + 最新动态槽自动更新
用法：
  python project_b/build_home.py --rebuild          # 一次性重排：最新动态槽 + 核心资产矩阵 + 底部聚合收敛
  python project_b/build_home.py --dynamic-only     # 只更新「最新场次摘要卡」（auto_update/deploy_all 每日调用）

五层架构：hero/档案 → 最新动态（自动槽）→ 核心资产入口矩阵 → 长尾QA/入门 → 官方+溯源
数据源：
  - 效应：dashboard/dashboard_data.json tour_song_effects（最新日期场次，三口径+pattern）
  - 歌单数：data/setlists.json；反馈数/金句数：live/<场次>.html 正则计数
  - 场次状态/链接：live/manifest.json（update_index_table.py 自动补齐）
标记约定（互不干扰）：
  - LATEST_CARD_START/END：最新场次摘要卡（本脚本维护）
  - LIVE_TABLE_START/END：全部场次表格（update_index_table.py 维护）
"""
import argparse, json, re, sys, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ROOT = Path(r'D:\wx409.github.io')
INDEX = ROOT / 'index.html'
DASH = ROOT / 'dashboard' / 'dashboard_data.json'
SETLISTS = ROOT / 'data' / 'setlists.json'
LIVE_DIR = ROOT / 'live'
CARD_START = '<!-- LATEST_CARD_START -->'
CARD_END = '<!-- LATEST_CARD_END -->'

ASSETS = [
    ('live/setlists.html', '🎵 巡演歌单', '59 场全部歌单与说明'),
    ('live/hui-回-广州-2026.html', '🎤 广州站实录', '歌单 · 反馈 · 金句'),
    ('live/hui-回-重庆-2026.html', '🎤 重庆站实录', '首站完整记录'),
    ('live-reviews.html', '📝 观众repo与摘录', '多平台匿名反馈'),
    ('social_wall.html', '📱 同担动态聚合', '微博 / 小红书 / B站'),
    ('map/index.html', '🗺 巡演地图', '22 城演出足迹'),
    ('dashboard/index.html', '📊 数据大屏', '场次效应 · 曲目池'),
    ('songs.html', '🎶 歌曲库', '正式作品与翻唱'),
    ('tavern/index.html', '🍷 深夜小酒馆', '106 期逐字稿'),
    ('story.html', '📖 数据故事', '文化足迹时间线'),
]


def _fmt(v):
    if v is None:
        return '—'
    return f'{v:+.1f}%'


def latest_effects():
    try:
        d = json.loads(DASH.read_text(encoding='utf-8'))
    except Exception:
        return {}
    evs = [e for e in d.get('tour_song_effects', []) if e.get('date')]
    if not evs:
        return {}
    evs.sort(key=lambda e: e['date'], reverse=True)
    return evs[0]


def manifest_map():
    mp = LIVE_DIR / 'manifest.json'
    out = {}
    if mp.exists():
        try:
            for e in json.loads(mp.read_text(encoding='utf-8')):
                if e.get('date'):
                    out[e['date']] = e
        except Exception:
            pass
    return out


def live_counts(date, city):
    cand = LIVE_DIR / f'hui-回-{city}-{date[:4]}.html'
    if not cand.exists():
        return 0, 0
    html = cand.read_text(encoding='utf-8', errors='ignore')
    repo = re.search(r'<section id="audience-repo".*?</section>', html, re.S)
    qw = re.search(r'<section id="quotes-wall".*?</section>', html, re.S)
    return (len(re.findall(r'<li>', repo.group(0))) if repo else 0,
            len(re.findall(r'<blockquote', qw.group(0))) if qw else 0)


def setlist_count(date):
    try:
        s = json.loads(SETLISTS.read_text(encoding='utf-8'))
        g = (s.get('setlists') or {}).get(date) or {}
        return len(g.get('songs') or [])
    except Exception:
        return 0


def build_card():
    e = latest_effects()
    if not e:
        return '<!-- LATEST_CARD_START --><!-- LATEST_CARD_END -->'
    date, city = e['date'], e.get('city', '')
    mm = manifest_map().get(date, {})
    venue = mm.get('venue') or e.get('venue') or ''
    status = mm.get('status') or e.get('status') or ''
    link = mm.get('link') or f"live/hui-回-{city}-{date[:4]}.html"
    repo_n, qw_n = live_counts(date, city)
    sl_n = setlist_count(date)
    fx = (f"追踪曲目池 {_fmt(e.get('total_uplift'))} ｜ "
          f"歌单内 {_fmt(e.get('setlist_uplift'))} ｜ "
          f"辐射带动 {_fmt(e.get('radiance_uplift'))}")
    pat = e.get('pattern') or ''
    L = [CARD_START]
    L.append('<div class="latest-card" style="background:#f6f8fa;border-left:4px solid #c41e3a;'
             'padding:10px 14px;margin:10px 0;border-radius:4px;">')
    L.append(f'<strong>{date.replace("-", ".")} · {city} · {venue}</strong>'
             f'<span style="color:#777;font-size:13px;">（{status}）</span>')
    L.append(f'<div style="font-size:13px;color:#444;margin-top:4px;">效应：{fx}'
             + (f'（{pat}）' if pat else '') + '</div>')
    bits = []
    if sl_n:
        bits.append(f'歌单 {sl_n} 首')
    if repo_n:
        bits.append(f'观众反馈 {repo_n} 条')
    if qw_n:
        bits.append(f'现场金句 {qw_n} 条')
    if bits:
        L.append(f'<div style="font-size:13px;color:#444;margin-top:2px;">{" · ".join(bits)}</div>')
    L.append(f'<div style="font-size:13px;margin-top:6px;">'
             f'<a href="{link}">完整实录 →</a> '
             f'<a href="live/setlists.html" style="margin-left:12px;">全部歌单 →</a> '
             f'<a href="live-reviews.html" style="margin-left:12px;">观众repo →</a></div>')
    L.append('</div>')
    L.append(CARD_END)
    return '\n'.join(L)


def asset_grid():
    items = ''.join(
        f'<a href="{u}" style="display:block;padding:10px 12px;border:1px solid #e1e4e8;'
        f'border-radius:8px;text-decoration:none;color:#24292e;background:#fff;">'
        f'<strong>{t}</strong><br><span style="font-size:12px;color:#777;">{d}</span></a>'
        for u, t, d in ASSETS)
    return (
        '\n    <h2>核心资产</h2>\n'
        '    <p style="font-size:13px;color:#666;">歌单 / 现场实录 / 观众反馈 / 地图 / 大屏 / 酒馆——站内主要内容入口。</p>\n'
        '    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;">\n'
        f'        {items}\n    </div>\n'
    )


def rebuild():
    html = INDEX.read_text(encoding='utf-8')
    # 1) 保留 LIVE_TABLE 块（update_index_table 维护）
    tm = re.search(r'<!-- LIVE_TABLE_START -->.*?<!-- LIVE_TABLE_END -->', html, re.S)
    table_block = tm.group(0) if tm else ''

    # 2) 动态区（近期动态 + 最新演出动态 + 重庆明细 + 现场亮点 + 观众矩阵）→ 新动态槽 + 资产矩阵
    start = html.find('<p><strong>近期动态：')
    faq = html.find('<section id="faq">')
    if start < 0 or faq < 0 or start >= faq:
        print('!! 定位动态区失败（近期动态/faq 标记缺失）'); return
    dyn_zone = (
        '\n    <h2>最新演出动态</h2>\n'
        '    <p style="font-size:13px;color:#666;">实时更新：最新场次摘要 + 全部场次表格（数据来源：大麦网、主办方官方通告；'
        '效应为演出后 7 日三口径监测：追踪曲目池 / 歌单内 / 辐射带动）。</p>\n'
        + '\n' + build_card() + '\n\n'
        + (table_block + '\n' if table_block else '')
        + asset_grid()
    )
    html = html[:start] + dyn_zone + html[faq:]

    # 3) 底部聚合区（同担动态聚合 + 社交墙卡片）→ 一行入口
    agg = re.search(r'<h2[^>]*>📱 同担动态聚合.*?SOCIAL_WALL_END -->', html, re.S)
    if agg:
        entry = (
            '\n    <h2>📱 同担动态聚合</h2>\n'
            '    <p style="font-size:13px;color:#666;">观众在微博 / 小红书 / B站 / 抖音的公开反馈与二创，'
            '匿名化呈现（不公开账号）。\n'
            '    <a href="live-reviews.html">观众repo与摘录 →</a> '
            '<a href="social_wall.html" style="margin-left:12px;">社交动态墙 →</a></p>\n'
        )
        html = html[:agg.start()] + entry + html[agg.end():]
    else:
        print('!! 未找到底部聚合区（可能已收敛）')

    INDEX.write_text(html, encoding='utf-8')
    print('[OK] 首页重排完成：动态槽 + 资产矩阵 + 底部收敛')


def dynamic_only():
    html = INDEX.read_text(encoding='utf-8')
    card = build_card()
    if CARD_START in html and CARD_END in html:
        html = re.sub(r'<!-- LATEST_CARD_START -->.*?<!-- LATEST_CARD_END -->',
                      lambda _m: card, html, count=1, flags=re.S)
    else:
        # 兜底：在 LIVE_TABLE_START 前插入卡片标记
        if 'LIVE_TABLE_START' in html:
            html = html.replace('<!-- LIVE_TABLE_START -->', card + '\n    <!-- LIVE_TABLE_START -->', 1)
        else:
            print('!! 找不到插入点'); return
    INDEX.write_text(html, encoding='utf-8')
    e = latest_effects()
    print('[OK] 动态摘要卡已更新：%s %s（%s）' % (e.get('date', '?'), e.get('city', '?'),
                                             e.get('pattern', '')))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rebuild', action='store_true', help='一次性重排首页')
    ap.add_argument('--dynamic-only', action='store_true', help='只更新最新场次摘要卡')
    args = ap.parse_args()
    if args.rebuild:
        rebuild()
    elif args.dynamic_only:
        dynamic_only()
    else:
        # 默认（deploy_all 调用无参）：更新动态摘要卡
        dynamic_only()


if __name__ == '__main__':
    main()
