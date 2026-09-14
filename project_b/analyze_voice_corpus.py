# -*- coding: utf-8 -*-
"""声音素材语料的文本分析（第一性原理：回答别处答不了的问题）。

这批语料是「他的声音材料」——电台/读诗/读信/晚安图书馆 —— 与微博（他主动说什么）
不同，它回答：**他选择读什么、以什么语气说、面向谁**。

分析维度：
  1. 高频词（jieba）与主题分布 —— 他反复讲什么
  2. 情感倾向（正/负/中性词表命中）—— 夜间电台的情绪基调
  3. 系列对比 —— 音乐图书馆（读书信）vs 晚安图书馆 vs 低音时间
  4. 可引用金句抽取 —— 短、完整、有画面感的句子（进 quotes 候选）
  5. 人称与对话对象 —— "你/大家/我们" 的使用（他面向谁说话）

产出：data/voice_analysis.json
用法：python -X utf8 project_b\analyze_voice_corpus.py
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'voice_corpus.json')
OUT = os.path.join(ROOT, 'data', 'voice_analysis.json')

STOP = set('''的 了 是 我 你 他 她 它 们 这 那 就 都 也 在 有 和 与 而 但 不 没 很 又 还 要 会 能 可以 一个 什么 怎么 因为 所以 如果 就是 这样 那样 我们 你们 他们 自己 时候 现在 已经 一直 起来 出来 觉得 知道 说 说 到 对 从 被 把 给 让 用 於 于 之 其 此 该 些 个 一 二 三 四 五 六 七 八 九 十'''.split())


def jieba_words(text):
    try:
        import jieba
        jieba.setLogLevel(60)
        ws = [w for w in jieba.cut(text) if len(w) >= 2 and w not in STOP
              and not re.fullmatch(r'[\W\d_]+', w)]
        return ws
    except Exception:
        return [w for w in re.findall(r'[\u4e00-\u9fa5]{2,4}', text) if w not in STOP]


POS = ['爱', '温暖', '美好', '希望', '快乐', '幸福', '感谢', '祝福', '喜欢', '安心',
       '陪', '家', '春天', '阳光', '明亮', '勇敢', '珍贵']
NEG = ['孤独', '遗忘', '告别', '失去', '离开', '思念', '悲伤', '眼泪', '老去', '病',
       '战争', '牺牲', '寒冷', '害怕', '遗憾']


def main():
    doc = json.loads(io.open(SRC, encoding='utf-8').read())
    items = doc.get('items') or []
    alltext = '\n'.join(x['text'] for x in items)

    ws = jieba_words(alltext)
    top = Counter(ws).most_common(60)

    # 主题分布（沿用 voice_corpus 的规则标注，按字数加权）
    theme_chars = Counter()
    for x in items:
        for t in x.get('themes') or []:
            theme_chars[t] += x['chars']

    # 情感（词表命中计数，**不是**模型判定，只作倾向参考）
    sentiment = {
        'positive_hits': sum(alltext.count(w) for w in POS),
        'negative_hits': sum(alltext.count(w) for w in NEG),
    }
    sentiment['tone'] = ('偏暖' if sentiment['positive_hits'] > sentiment['negative_hits'] * 1.2
                         else ('偏冷' if sentiment['negative_hits'] > sentiment['positive_hits'] * 1.2
                               else '中性/复杂'))

    # 人称（他面向谁说话）
    person = {k: alltext.count(k) for k in ('我们', '你们', '大家', '朋友', '孩子',
                                            '父亲', '母亲', '爱人', '你', '我')}

    # 系列对比
    by_series = []
    for s in sorted({x['series'] for x in items}):
        rows = [x for x in items if x['series'] == s]
        txt = '\n'.join(r['text'] for r in rows)
        by_series.append({
            'series': s, 'name': rows[0]['series_name'], 'items': len(rows),
            'chars': sum(r['chars'] for r in rows),
            'minutes': round(sum(r['duration_s'] or 0 for r in rows) / 60, 1),
            'themes': sorted({t for r in rows for t in (r.get('themes') or [])}),
            'top_words': [w for w, _c in Counter(jieba_words(txt)).most_common(8)],
        })

    # 金句候选：完整句、18–55 字、含情绪/画面词、**排除研究口播套话**
    QUOTE_HINT = re.compile('|'.join(POS + NEG + ['雪', '夜', '光', '歌', '书', '路', '年']))
    BAD_PREFIX = ('今天我要', '所以', '不懂得', '那么', '接下来', '我们来看',
                  '本期', '今天和', '我是', '各位', '大家好', '那么这')
    BAD_MID = ('作家', '作品', '出版社', '文学', '节目', '今天要')
    quotes, seen = [], set()
    for x in items:
        for seg in re.split(r'[。！？\n]', x['text'] or ''):
            s = seg.strip().replace(' ', '')
            if not (18 <= len(s) <= 55):
                continue
            if s in seen or s.startswith(BAD_PREFIX):
                continue
            if any(b in s for b in BAD_MID):
                continue
            if not QUOTE_HINT.search(s):
                continue
            # 去掉 ASR 明显不通的（含连续非常用字或数字夹杂）
            if re.search(r'\d{3,}', s):
                continue
            seen.add(s)
            quotes.append({
                'text': s, 'series': x['series_name'], 'episode': x['title'],
                'date': x.get('date') or '', 'kind': x.get('kind'),
                # ⚠️ 口径关键：读诗/读信 = **他朗读的文本**（文学/歌词），
                # 不等于「他说的原话」。只有节目口播/自我介绍类才是本人原话。
                '语料性质': ('朗读文本（非本人原话）'
                          if any(k in x['series_name'] for k in ('图书馆', '低音时间', '想念雪', '千景', '从前慢'))
                          else '节目口播（含本人原话）'),
            })
    # 优先「本人原话」类与核心系列
    PREF = ('王晰的音乐图书馆', '王晰的低音时间', 'ELLE007')
    quotes.sort(key=lambda q: (0 if any(p in q['series'] for p in PREF) else 1, -len(q['text'])))
    quotes = quotes[:60]

    out = {
        'schema': 'voice_analysis v1',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'source': 'data/voice_corpus.json',
        'note': ('声音素材语料的文本分析：高频词/主题/情感倾向/人称/系列对比/金句候选。'
                 '情感为**词表命中**，非模型判定；金句为规则筛选，引用前须复核原文。'),
        'corpus': {'items': len(items), 'chars': len(alltext),
                   'minutes': round(sum(x.get('duration_s') or 0 for x in items) / 60, 1)},
        'top_words': [{'word': w, 'count': c} for w, c in top],
        'theme_chars': dict(theme_chars.most_common()),
        'sentiment': sentiment,
        'person_usage': person,
        'series_compare': by_series,
        'quote_candidates': quotes,
    }
    io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=1))
    print('=' * 70)
    print('声音素材文本分析')
    print('=' * 70)
    print('  语料 %d 条 / %d 字 / %.1f 分钟' % (len(items), len(alltext), out['corpus']['minutes']))
    print('  情感词命中: 正 %d / 负 %d → %s'
          % (sentiment['positive_hits'], sentiment['negative_hits'], sentiment['tone']))
    print('  高频词 Top20:', ' '.join('%s(%d)' % (w, c) for w, c in top[:20]))
    print('  主题(按字数):', ' / '.join('%s %d' % (k, v) for k, v in theme_chars.most_common(8)))
    print('  人称:', ' '.join('%s%d' % (k, v) for k, v in person.items() if v))
    print('  金句候选 %d 条' % len(quotes))
    for q in quotes[:6]:
        print('     ·', q['text'][:44], '（%s）' % q['series'][:14])
    print('\n[写]', OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
