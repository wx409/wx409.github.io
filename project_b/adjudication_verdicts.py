#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""裁决汇总：解开 A/B 映射，按层与类别出分子/分母（仅这 24 窗）。

诚实声明：听者参考了 listening_cheatsheet.md（机器预筛提示），
因此本轮裁决不宜视为完全独立的人耳基准；该声明写入结果。
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ADJ = Path(r'D:\wx409.github.io\data\research\experiments\exp-20261025-01\adjudication')

man = json.loads((ADJ / 'adjudication_manifest.json').read_text(encoding='utf-8'))['items']
mapping = json.loads((ADJ / 'candidate_mapping.private.json').read_text(encoding='utf-8'))

rows = []
for r in man:
    aid = r['adjudication_id']
    f = json.loads((ADJ / 'materials' / aid / 'form.json').read_text(encoding='utf-8'))
    att = next((k for k, v in f['attribution'].items() if v is True), None)
    f0 = next((k for k, v in f['f0_verdict'].items() if v is True), None)
    m = mapping[aid]
    winner = None
    if f0 == 'candidate_A_more_reasonable':
        winner = m['candidate_A']
    elif f0 == 'candidate_B_more_reasonable':
        winner = m['candidate_B']
    rows.append({"adjudication_id": aid, "layer": r['layer'], "category": r['category'],
                 "attribution": att, "f0_verdict": f0, "yin_or_praat": winner})

def tallies(sub):
    c = Counter(x['f0_verdict'] for x in sub)
    return {
        "n": len(sub),
        "yin_more_reasonable": sum(1 for x in sub if x['yin_or_praat'] == 'YIN'),
        "praat_more_reasonable": sum(1 for x in sub if x['yin_or_praat'] == 'Praat'),
        "both_reasonable": c.get('both_reasonable_small_difference', 0),
        "both_unreliable": c.get('both_unreliable', 0),
        "unresolved": c.get('unresolved', 0),
        "attribution_target": sum(1 for x in sub if x['attribution'] == 'target_singer'),
        "attribution_other_or_unclear": sum(1 for x in sub if x['attribution'] != 'target_singer'),
    }

out = {
    "status": "exploratory", "publishable": False,
    "windows": len(rows),
    "caveat": ("听者参考了 listening_cheatsheet.md（机器预筛提示）；"
               "本轮裁决不宜视为完全独立的人耳基准，需独立听者复核后再升级证据等级。"),
    "overall": tallies(rows),
    "by_layer": {l: tallies([x for x in rows if x['layer'] == l])
                 for l in ('录音室人声轨', '现场混音')},
    "by_category": {c: tallies([x for x in rows if x['category'] == c])
                    for c in dict.fromkeys(x['category'] for x in rows)},
    "agree_windows": {
        "n": sum(1 for x in rows if x['category'] in ('agree_high', 'agree_mid', 'agree_low')),
        "both_reasonable": sum(1 for x in rows if x['category'].startswith('agree')
                               and x['f0_verdict'] == 'both_reasonable_small_difference'),
        "suspicious": sum(1 for x in rows if x['category'].startswith('agree')
                          and x['f0_verdict'] in ('both_unreliable', 'unresolved')),
    },
    "rows": rows,
}
(ADJ / 'adjudication_verdicts.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(out['overall'], ensure_ascii=False))
print(json.dumps(out['by_layer'], ensure_ascii=False))
print('agree:', out['agree_windows'])
