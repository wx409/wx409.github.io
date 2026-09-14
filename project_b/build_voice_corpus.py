# -*- coding: utf-8 -*-
"""声音素材转写稿整合器：media + transcripts + manifest → data/voice_corpus.json

第一性原理：
  声音素材的价值不在"文件躺在本地"，而在**能像微博/百家号那样被检索、被引用、
  被喂进文本挖掘管线、被传记直接引用**。所以本脚本把三处数据合成一份与既有语料同构的
  机读数据源，每条带：系列/单集/日期/时长/出处 URL/全文/是否可引用。

产出：
  data/voice_corpus.json     机读语料（条目 + 汇总统计 + 口径说明）
  <LIB>/transcripts/fulltext/<series>.txt   便于通读的整卷全文

用法：python -X utf8 project_b\build_voice_corpus.py [--check]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = r'E:\wx\声音素材库'
MEDIA = os.path.join(LIB, 'media')
TRANS = os.path.join(LIB, 'transcripts')
MANIFEST = os.path.join(LIB, 'manifest', 'media_manifest.json')
OUT = os.path.join(ROOT, 'data', 'voice_corpus.json')
FULLTEXT = os.path.join(TRANS, 'fulltext')

# 系列显示名与可引用级别（内容性质决定）
SERIES_META = {
    'yytsg_bili': ('王晰的音乐图书馆', 'B站饭制合集（原喜马拉雅已下架）', '本人原话', '高'),
    'xwntj_bili': ('晰望你听见（深夜晚安电台）', '快手原节目 / B站饭迷合集', '本人原话', '高'),
    'netease_dj_792978415': ('王晰的低音时间（DJ 电台存档）', '网易云音乐饭制存档', '本人原话', '中'),
    'xmly_544193351': ('想念雪', '喜马拉雅读诗', '本人朗读', '高'),
    'xmly_283181641': ('世间万物千景，一生恍惚而过', '喜马拉雅读诗', '本人朗读', '高'),
    'xmly_623231068': ('从前慢 / 哪有你这样你', '喜马拉雅读诗', '本人朗读', '高'),
    'weibo_kangyi_jiashu': ('爸爸坚信我们能取得胜利（抗疫家书）', '微博（王晰）', '本人朗读', '高'),
    'weibo_520_shencongwen': ('520 沈从文情书片段', '微博（工作室）', '本人朗读', '高'),
    'elle_wanan': ('ELLE007 晚安图书馆', 'ELLE / 微博', '本人原话', '高'),
    'elle_p1': ('ELLE007 晚安图书馆', 'ELLE / 微博', '本人原话', '高'),
    'elle_p2': ('ELLE007 晚安图书馆', 'ELLE / 微博', '本人原话', '高'),
    'elle_p3': ('ELLE007 晚安图书馆', 'ELLE / 微博', '本人原话', '高'),
    'elle_p4': ('ELLE007 晚安图书馆', 'ELLE / 微博', '本人原话', '高'),
    'elle_p5': ('ELLE007 晚安图书馆', 'ELLE / 微博', '本人原话', '高'),
    'elle_p6': ('ELLE007 晚安图书馆', 'ELLE / 微博', '本人原话', '高'),
    'elle_p7': ('ELLE007 晚安图书馆', 'ELLE / 微博', '本人原话', '高'),
}

# 话题关键词（用于主题标注；可扩展）
THEMES = {
    '雪与冬': ['雪', '冬', '寒', '冰'],
    '夜与睡': ['夜', '晚', '睡', '梦', '晚安'],
    '家与亲情': ['家', '父母', '爸爸', '妈妈', '孩子'],
    '爱情': ['爱', '喜欢', '想你', '恋人'],
    '故乡与旅行': ['故乡', '家乡', '旅行', '城市', '远方'],
    '音乐与歌唱': ['音乐', '歌', '唱', '旋律', '低音'],
    '诗与远方': ['诗', '散文', '书', '读'],
    '时间与年华': ['时间', '岁月', '老', '年', '过去'],
}


def num_from_name(name):
    m = re.match(r'^(\d{1,3})_', str(name))
    return int(m.group(1)) if m else None


def netease_dates():
    """网易云 DJ 电台逐集日期（来自 collect_netease_dj 的产物）。"""
    p = os.path.join(ROOT, 'data', 'radio_netease_dj_792978415.json')
    if not os.path.exists(p):
        return {}
    d = json.loads(io.open(p, encoding='utf-8').read())
    out = {}
    for x in d.get('programs') or []:
        if x.get('serialNum') is not None:
            out[int(x['serialNum'])] = x.get('createTime') or ''
    return out


# 系列级日期：**只填已核验的**（用户提供或平台 API 返回）。
# ⚠️ 纪律：不推算、不猜测。未知的留空，由 media 文件元数据或后续核验补。
SERIES_DATE = {
    'yytsg_bili': '2018-12-02',          # B站 API pubdate
    'xwntj_bili': '2022-07-10',          # B站 API pubdate
    'xmly_544193351': '2022-06-18',      # 用户提供 + 喜马拉雅 createTime=2022-06
    'xmly_283181641': '2020-04-14',      # 用户提供 + createTime=2020-04
    'xmly_623231068': '2023-04-03',      # 用户提供 + createTime=2023-04
    'weibo_kangyi_jiashu': '2020-03-08',  # 用户提供
    'weibo_520_shencongwen': '2020-05-20',  # 用户提供
}


def media_dates():
    """从已下载媒体的文件创建/修改时间兜底取日期（微博视频无公开 API 日期时用）。
    注意：这是**下载时间**的近似，仅当文件系统时间可信时才用；否则留空。"""
    out = {}
    for series in os.listdir(MEDIA) if os.path.isdir(MEDIA) else []:
        d = os.path.join(MEDIA, series)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.lower().endswith(('.mp4', '.m4a', '.aac', '.mp3')):
                out.setdefault(series, '')      # 不填具体值，只标记"有媒体"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()

    man = json.loads(io.open(MANIFEST, encoding='utf-8').read())
    by_id = {x['id']: x for x in man['items']}
    NE_DATES = netease_dates()

    items = []
    for series in sorted(os.listdir(TRANS)):
        sdir = os.path.join(TRANS, series)
        if not os.path.isdir(sdir) or series == 'fulltext':
            continue
        name, source, kind, conf = SERIES_META.get(
            series, (series, by_id.get(series, {}).get('platform', ''), '本人原话', '中'))
        for f in sorted(os.listdir(sdir)):
            if not f.endswith('.txt'):
                continue
            base = f[:-4]
            txt = io.open(os.path.join(sdir, f), encoding='utf-8').read().strip()
            segp = os.path.join(sdir, base + '.segments.json')
            seg = json.loads(io.open(segp, encoding='utf-8').read()) if os.path.exists(segp) else {}
            themes = [k for k, kws in THEMES.items() if any(x in txt for x in kws)]
            ep = num_from_name(f)
            date = (by_id.get(series, {}).get('verified') or {}).get('createTime', '')
            if not date and ep is not None:
                date = NE_DATES.get(ep, '') if series == 'netease_dj_792978415' else ''
            if not date:
                date = SERIES_DATE.get(series, '')
            items.append({
                'id': '%s__%s' % (series, re.sub(r'[^\w\u4e00-\u9fa5]+', '_', base)[:60]),
                'series': series,
                'series_name': name,
                'episode': ep,
                'title': base,
                'source': source,
                'kind': kind,
                'confidence': conf,
                'date': date,
                'duration_s': seg.get('duration_s'),
                'chars': len(txt),
                'themes': themes,
                'text': txt,
                'media_ref': seg.get('media', ''),
                'transcript_ref': 'transcripts/%s/%s' % (series, f),
                'source_url': by_id.get(series, {}).get('url', ''),
            })

    # 整卷全文
    os.makedirs(FULLTEXT, exist_ok=True)
    for series in sorted({x['series'] for x in items}):
        rows = [x for x in items if x['series'] == series]
        nm = SERIES_META.get(series, (series,))[0]
        nm = re.sub(r'[\\/:*?"<>|\s]+', '_', nm)[:40]
        body = '\n\n'.join('【%s】\n%s' % (x['title'], x['text']) for x in rows)
        io.open(os.path.join(FULLTEXT, '%s_%s.txt' % (series, nm)), 'w',
                encoding='utf-8').write(body)

    total_chars = sum(x['chars'] for x in items)
    total_dur = sum(x['duration_s'] or 0 for x in items)
    doc = {
        'schema': 'voice_corpus v1',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'note': ('王晰声音素材转写稿语料（电台/读诗/读信/晚安图书馆）：'
                 '每条含系列、出处、可引用级别、全文与主题标注。媒体原件仅本地留存。'),
        'source_library': LIB,
        'discipline': [
            '只收录已下载并完成转写的条目；未转写的不计。',
            '转载/饭制来源标 confidence 降级，正式引用优先官方渠道版本。',
            '主题标注为关键词规则命中，非人工判定——引用时需复核原文。',
        ],
        'counts': {
            'items': len(items),
            'series': len({x['series'] for x in items}),
            'chars': total_chars,
            'duration_minutes': round(total_dur / 60, 1),
        },
        'series_summary': [
            {'series': s, 'name': SERIES_META.get(s, (s,))[0],
             'items': len([x for x in items if x['series'] == s]),
             'chars': sum(x['chars'] for x in items if x['series'] == s),
             'duration_minutes': round(sum(x['duration_s'] or 0 for x in items if x['series'] == s) / 60, 1)}
            for s in sorted({x['series'] for x in items})],
        'items': items,
    }
    new = json.dumps(doc, ensure_ascii=False, indent=1)
    old = io.open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else ''
    if old == new:
        print('[OK] voice_corpus.json 已一致')
        return 0
    if a.check:
        print('[FAIL] voice_corpus.json 需更新')
        return 1
    io.open(OUT, 'w', encoding='utf-8').write(new)
    print('=' * 70)
    print('声音素材语料（voice_corpus）')
    print('=' * 70)
    print('  条目 %d ｜ 系列 %d ｜ 全文 %d 字 ｜ 总时长 %.1f 分钟'
          % (doc['counts']['items'], doc['counts']['series'],
             total_chars, doc['counts']['duration_minutes']))
    for s in doc['series_summary']:
        print('  %-24s %2d 条 %6d 字 %6.1f 分钟' % (s['name'][:24], s['items'],
                                                    s['chars'], s['duration_minutes']))
    print('\n[写]', OUT)
    print('[写]', FULLTEXT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
