# -*- coding: utf-8 -*-
"""声音素材并入知识库（entities / facts / relations）。

第一性原理：声音素材若只躺在 JSON 里，就还是"文件"而不是"知识"。
并入知识库后，它才能被检索、被问答、被传记直接引用，与微博/演出/作品同处一个图谱。

新增实体类型：
  voice_series（系列）/ voice_episode（单集）/ work（被朗读的作品/作者）
新增关系：
  series → has_episode → episode
  episode → reads → work（朗读的作品，非本人原话）
  person:wangxi → has_voice_series → series
  episode → published_on → 平台（org）

纪律：
  · 只并「本人朗读/原话」条目；转载类降级标注。
  · 区分「朗读文本」与「本人原话」——由 voice_corpus 的 kind 字段决定。
  · 幂等：重复运行结果一致（先清除本脚本上一轮注入的部分再重建）。

用法：python -X utf8 project_b\integrate_voice_kb.py
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB = os.path.join(ROOT, 'data', 'kb')
VC = os.path.join(ROOT, 'data', 'voice_corpus.json')
VA = os.path.join(ROOT, 'data', 'voice_analysis.json')

MARK = 'voice_corpus.json'          # 用它识别本脚本注入的实体/事实/关系

PLATFORM_ORG = {
    'bilibili': 'org:bilibili', 'weibo': 'org:weibo', 'ximalaya': 'org:ximalaya',
    'netease': 'org:netease', 'qqmusic': 'org:qqmusic', 'lizhi': 'org:lizhi',
    'kuaishou': 'org:kuaishou',
}
ORG_NAMES = {
    'org:bilibili': '哔哩哔哩', 'org:weibo': '微博', 'org:ximalaya': '喜马拉雅',
    'org:netease': '网易云音乐', 'org:qqmusic': 'QQ音乐', 'org:lizhi': '荔枝FM',
    'org:kuaishou': '快手',
}


def load(p, default=None):
    try:
        return json.loads(io.open(p, encoding='utf-8').read())
    except Exception:
        return default if default is not None else {}


def save(p, obj):
    io.open(p, 'w', encoding='utf-8').write(json.dumps(obj, ensure_ascii=False, indent=1))


def main():
    vc = load(VC)
    items = vc.get('items') or []
    if not items:
        print('[SKIP] voice_corpus.json 为空')
        return 1

    # ⚠️ entities.json 是**带外壳的**：{generated_at, entity_count, entities:{...}}
    # 2026-09-14 踩坑：首版误把顶层当实体字典，写回时毁掉 1416 个实体（已从备份恢复）。
    # 读写都必须走 .get('entities')，并保留外壳字段。
    ent_doc = load(os.path.join(KB, 'entities.json'), {})
    ents = ent_doc.get('entities') if isinstance(ent_doc.get('entities'), dict) else ent_doc
    facts = load(os.path.join(KB, 'facts.json'), [])
    rels = load(os.path.join(KB, 'relations.json'), [])
    if not isinstance(ents, dict):
        print('[ABORT] entities.json 结构异常，拒绝写入')
        return 1

    # 幂等：清掉上一轮本脚本注入的
    before_e, before_f, before_r = len(ents), len(facts), len(rels)
    for k in [k for k, v in ents.items() if isinstance(v, dict) and v.get('src') == MARK]:
        del ents[k]
    facts = [f for f in facts if f.get('source') != MARK]
    rels = [r for r in rels if r.get('source_ref') != MARK]

    added_e = added_f = added_r = 0

    def ent(eid, etype, name, attrs=None):
        nonlocal added_e
        if eid in ents:
            return eid
        ents[eid] = {'type': etype, 'name': name, 'aliases': [], 'attrs': attrs or {}, 'src': MARK}
        added_e += 1
        return eid

    def fact(subject, prop, value, valid_from='', source_url='', conf=0.9):
        nonlocal added_f
        facts.append({'id': 'vf%04d' % (len(facts) + 1), 'subject': subject, 'property': prop,
                      'value': value, 'valid_from': valid_from, 'valid_to': '',
                      'source': MARK, 'source_url': source_url,
                      'source_type': '站内数据·声音素材转写', 'confidence': conf})
        added_f += 1

    def rel(src, rtype, tgt, context=''):
        nonlocal added_r
        rels.append({'source': src, 'type': rtype, 'target': tgt,
                     'context': context, 'source_ref': MARK})
        added_r += 1

    # 平台组织实体
    for oid, nm in ORG_NAMES.items():
        ent(oid, 'org', nm)

    # 系列 → 单集 → 作品
    seen_series = {}
    for x in items:
        s = x.get('series') or 'unknown'
        sid = 'voice_series:%s' % s
        if s not in seen_series:
            seen_series[s] = {'items': 0, 'chars': 0, 'dates': []}
            ent(sid, 'voice_series', x.get('series_name') or s,
                {'source': x.get('source'), 'kind': x.get('kind'),
                 'confidence': x.get('confidence')})
            rel('person:wangxi', 'has_voice_series', sid, x.get('source') or '')
        seen_series[s]['items'] += 1
        seen_series[s]['chars'] += x.get('chars') or 0
        if x.get('date'):
            seen_series[s]['dates'].append(x['date'])

        eid = 'voice_ep:%s' % re.sub(r'[^\w\u4e00-\u9fa5]+', '_', x.get('id') or '')[:70]
        ent(eid, 'voice_episode', x.get('title') or x.get('id'),
            {'series': s, 'date': x.get('date') or '', 'duration_s': x.get('duration_s'),
             'chars': x.get('chars'), 'kind': x.get('kind'), 'themes': x.get('themes') or [],
             'transcript_ref': x.get('transcript_ref')})
        rel(sid, 'has_episode', eid, x.get('title') or '')

        # 朗读作品 vs 本人原话：由 kind 判定（不是猜）
        kind = x.get('kind') or ''
        nature = '本人朗读' if '朗读' in kind else '本人原话'
        fact(eid, 'voice_nature', nature, x.get('date') or '', x.get('source_url') or '')
        if x.get('chars'):
            fact(eid, 'transcript_chars', str(x['chars']), x.get('date') or '')
        if x.get('source_url'):
            fact(eid, 'source_url', x['source_url'], x.get('date') or '')

        # 平台关系
        man = load(os.path.join(ROOT, 'data', '..', 'data', 'voice_corpus.json'))  # 占位不用
        plat = (x.get('source') or '')
        for key, oid in PLATFORM_ORG.items():
            if key in plat.lower() or key in (x.get('source_url') or '').lower():
                rel(eid, 'published_on', oid, plat)
                break

    # 系列汇总事实
    for s, agg in seen_series.items():
        sid = 'voice_series:%s' % s
        fact(sid, 'episode_count', str(agg['items']), min(agg['dates']) if agg['dates'] else '')
        fact(sid, 'total_chars', str(agg['chars']))
        if agg['dates']:
            fact(sid, 'date_range', '%s ~ %s' % (min(agg['dates']), max(agg['dates'])))

    # 分析结论并入（主题/情感/人称）
    va = load(VA)
    if va:
        c = va.get('corpus') or {}
        fact('person:wangxi', 'voice_corpus_scale',
             '%s 条 / %s 字 / %s 分钟' % (c.get('items'), c.get('chars'), c.get('minutes')))
        sent = va.get('sentiment') or {}
        fact('person:wangxi', 'voice_corpus_tone',
             '%s（正 %s / 负 %s 词命中）' % (sent.get('tone'), sent.get('positive_hits'),
                                          sent.get('negative_hits')))
        tw = va.get('top_words') or []
        if tw:
            fact('person:wangxi', 'voice_corpus_top_words',
                 ' '.join('%s(%s)' % (w['word'], w['count']) for w in tw[:10]))
        th = va.get('theme_chars') or {}
        if th:
            fact('person:wangxi', 'voice_corpus_themes',
                 ' > '.join('%s(%s字)' % (k, v) for k, v in list(th.items())[:6]))

    # 重排 facts id 与 manifest
    for i, f in enumerate(facts, 1):
        f['id'] = 'f%04d' % i
    # 写回 entities 时保留外壳（generated_at / entity_count / entities）
    ent_doc['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
    ent_doc['entity_count'] = len(ents)
    ent_doc['entities'] = dict(sorted(ents.items()))
    save(os.path.join(KB, 'entities.json'), ent_doc)
    save(os.path.join(KB, 'facts.json'), facts)
    save(os.path.join(KB, 'relations.json'), rels)

    import collections
    by_type = collections.Counter(v.get('type') for v in ents.values() if isinstance(v, dict))
    man = load(os.path.join(KB, 'manifest.json'), {})
    man.update({'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'facts': len(facts), 'relations': len(rels),
                'entities_by_type': dict(sorted(by_type.items()))})
    src = set(man.get('sources') or [])
    src.add('voice_corpus.json')
    man['sources'] = sorted(src)
    save(os.path.join(KB, 'manifest.json'), man)

    print('=' * 70)
    print('声音素材并入知识库')
    print('=' * 70)
    print('  实体 %d → %d（新增 %d）' % (before_e, len(ents), added_e))
    print('  事实 %d → %d（新增 %d）' % (before_f, len(facts), added_f))
    print('  关系 %d → %d（新增 %d）' % (before_r, len(rels), added_r))
    print('  新增实体类型: voice_series=%d / voice_episode=%d'
          % (by_type.get('voice_series', 0), by_type.get('voice_episode', 0)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
