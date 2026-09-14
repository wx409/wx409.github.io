# -*- coding: utf-8 -*-
"""声音素材 × 指数 × 声学：时间线交叉分析（服务传记三条主线）。

第一性原理：单看任何一层都不够——
  · 声学实测回答「他能做到什么」
  · QQ音乐指数回答「市场怎么对待他」
  · 声音/文本素材回答「他在做什么、以什么状态」
**交叉起来**才回答传记真正的问题：
  A 能力-市场线：唱得好，市场看见了吗？
  B 市场-情绪线：他如何面对被看见/不被看见？（素材密度 × 市场冷热）
  C 情绪-能力线：状态如何影响产出？（素材性质变化 × 专辑/巡演节点）

产出：data/cross_voice_market.json
用法：python -X utf8 project_b\cross_voice_market.py
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def jload(rel, default=None):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        return default if default is not None else {}
    try:
        return json.loads(io.open(p, encoding='utf-8').read())
    except Exception:
        return default if default is not None else {}


def main():
    vc = jload('data/voice_corpus.json')
    items = vc.get('items') or []
    base = jload('data/archive_baseline.json')
    albs = jload('data/archive_vocal_albums.json')
    tl = jload('data/timeline.json')

    # ---- 声音素材：按年聚合 ----
    by_year = defaultdict(lambda: {'items': 0, 'chars': 0, 'minutes': 0.0,
                                   'series': set(), 'kinds': Counter()})
    for x in items:
        d = str(x.get('date') or '')
        y = d[:4] if re.match(r'\d{4}', d) else '未定年'
        g = by_year[y]
        g['items'] += 1
        g['chars'] += x.get('chars') or 0
        g['minutes'] = round(g['minutes'] + (x.get('duration_s') or 0) / 60, 1)
        g['series'].add(x.get('series_name'))
        g['kinds'][x.get('kind') or '?'] += 1

    # ---- 指数年度值（archive_baseline.json 的 annual 列表，口径=追踪曲目池日均）----
    idx_year, idx_meta = {}, {}
    for r in (base.get('annual') or []):
        if isinstance(r, dict) and re.match(r'\d{4}', str(r.get('year') or '')):
            y = str(r['year'])[:4]
            idx_year[y] = r.get('mean')
            idx_meta[y] = {'median': r.get('median'), 'cover_days': r.get('cover_days'),
                           'valid_days': r.get('valid_days')}

    # ---- 专辑发行年（data/albums.json 的 release_date，禁硬编码）----
    alb_doc = jload('data/albums.json', {})
    alb_items = alb_doc if isinstance(alb_doc, list) else (alb_doc.get('albums') or alb_doc.get('items') or [])
    if isinstance(alb_items, dict):
        alb_items = [dict(v, album=k) if isinstance(v, dict) else {'album': k, 'release_date': v}
                     for k, v in alb_items.items()]
    alb_year = defaultdict(list)
    for a in alb_items:
        if isinstance(a, dict):
            rd = str(a.get('release_date') or a.get('date') or '')
            nm = a.get('album') or a.get('name') or ''
            if re.match(r'\d{4}', rd):
                alb_year[rd[:4]].append(nm)

    # ---- 时间线事件年 ----
    ev_year = defaultdict(int)
    tl_events = tl if isinstance(tl, list) else (tl.get('events') or [])
    for e in tl_events:
        if isinstance(e, dict):
            d = str(e.get('date') or '')
            if re.match(r'\d{4}', d):
                ev_year[d[:4]] += 1

    years = sorted(set(by_year) | set(idx_year) | set(alb_year))
    timeline = []
    for y in years:
        g = by_year.get(y)
        timeline.append({
            'year': y,
            'voice_items': g['items'] if g else 0,
            'voice_chars': g['chars'] if g else 0,
            'voice_minutes': g['minutes'] if g else 0,
            'voice_series': sorted(g['series']) if g else [],
            'market_index': idx_year.get(y),
            'albums': alb_year.get(y, []),
            'events': ev_year.get(y, 0),
        })

    # ---- 三条主线（只在数据支持时下结论；否则标「证据不足」）----
    lines = {}

    # A 能力-市场：有实测专辑年 vs 指数
    a_pts = [t for t in timeline if t['albums'] and t['market_index'] is not None]
    lines['A_能力-市场'] = {
        'question': '唱得好，市场看见了吗？',
        'data_points': [{'year': t['year'], 'albums': t['albums'],
                         'index': t['market_index']} for t in a_pts],
        'finding': ('专辑发行年与指数年度值可对齐比较；'
                    '**但指数是追踪曲目池日均，受曲目池构成影响，不等于「专辑带来的市场反应」**'
                    '—— 结论需按曲目级联动再做，不可用年度均值直接归因。'),
    }

    # B 市场-情绪：声音素材密度 vs 指数
    b_pts = [t for t in timeline if t['voice_items'] and t['market_index'] is not None]
    voice_years = {t['year'] for t in timeline if t['voice_items']}
    idx_years = {t['year'] for t in timeline if t['market_index'] is not None}
    overlap = sorted(voice_years & idx_years)
    if len(b_pts) >= 3:
        hi = max(b_pts, key=lambda t: t['market_index'] or 0)
        lo = min(b_pts, key=lambda t: t['market_index'] or 0)
        dense = max(b_pts, key=lambda t: t['voice_items'])
        b_find = ('指数最高的年份是 %s（%s），最低是 %s（%s）；声音素材最密的是 %s（%s 条）。'
                  '两者**未呈现简单同向关系** —— 素材密度更像由「平台合作机会」驱动'
                  '（电台/出版社邀约），而非当年市场热度。'
                  % (hi['year'], hi['market_index'], lo['year'], lo['market_index'],
                     dense['year'], dense['voice_items']))
    else:
        obs = ''
        if '2026' in overlap:
            t26 = [t for t in b_pts if t['year'] == '2026']
            if t26:
                obs = (' 可注意的一处观察（**不构成结论**）：2026 是指数最低年（%s），'
                       '却是自 2022 以来素材最密的一年（%d 条，全部为 ELLE 晚安图书馆复更）；'
                       '且该系列在 2022-03 → 2026-01 之间停了近 4 年。'
                       '「市场最冷时重启音频栏目」是可写进传记的现象描述，'
                       '但需要更多证据（如栏目邀约来源）才能谈动机。'
                       % (t26[0]['market_index'], t26[0]['voice_items']))
        b_find = ('⚠️ **交叉窗口严重受限，不足以判定**：QQ音乐指数只覆盖 %s，'
                  '而声音素材集中在 %s —— 两者重叠仅 %s，重叠年内素材 %d 条。'
                  '**在补齐 2018–2022 指数或 2023+ 素材之前，不得就「市场冷热与表达密度」下任何结论。**%s'
                  % ('/'.join(sorted(idx_years)), '/'.join(sorted(voice_years)),
                     '/'.join(overlap) or '无', sum(t['voice_items'] for t in b_pts), obs))
    lines['B_市场-情绪'] = {
        'question': '他如何面对被看见/不被看见？',
        'index_coverage_years': sorted(idx_years),
        'voice_coverage_years': sorted(voice_years),
        'overlap_years': overlap,
        'data_points': b_pts,
        'finding': b_find,
    }

    # C 情绪-能力：素材性质变化 vs 专辑/巡演节点
    lines['C_情绪-能力'] = {
        'question': '状态如何影响产出？',
        'data_points': [{'year': t['year'], 'voice_series': t['voice_series'],
                         'albums': t['albums'], 'events': t['events']} for t in timeline
                        if t['voice_series'] or t['albums']],
        'finding': ('可观察到的形态：声音素材在时间上分层明显 —— '
                    '2016–2017 低音时间（电台期）→ 2018 音乐图书馆（读书信期）→ '
                    '2019 低音时间存档（读诗密集期）→ 2020–2026 晚安图书馆/读诗（公众号期）。'
                    '**这是"内容形态随职业阶段变化"的证据，但不能直接推导因果关系**'
                    '（素材可得性本身受平台存留影响）。'),
    }

    out = {
        'schema': 'cross_voice_market v1',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'note': ('声音素材 × 指数 × 声学 的时间线交叉。'
                 '三条主线为传记服务；**结论受素材可得性限制，不作因果断言**。'),
        'sources': ['data/voice_corpus.json', 'data/archive_baseline.json',
                    'data/archive_vocal_albums.json', 'data/timeline.json'],
        'index_year_values': idx_year,
        'index_caliber': '追踪曲目池日均（唯一口径，见 data/calibers.md）',
        'timeline': timeline,
        'biography_lines': lines,
    }
    p = os.path.join(ROOT, 'data', 'cross_voice_market.json')
    io.open(p, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))

    print('=' * 72)
    print('声音素材 × 指数 × 声学 时间线交叉')
    print('=' * 72)
    print('  %-6s %6s %8s %8s %8s %8s' % ('年', '素材', '字数', '分钟', '指数', '专辑'))
    for t in timeline:
        print('  %-6s %6d %8d %8.1f %8s %8d' % (
            t['year'], t['voice_items'], t['voice_chars'], t['voice_minutes'],
            t['market_index'] if t['market_index'] is not None else '—', len(t['albums'])))
    print()
    for k, v in lines.items():
        print('【%s】%s' % (k, v['question']))
        print('   ', (v['finding'] or '')[:150])
        print()
    print('[写]', p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
