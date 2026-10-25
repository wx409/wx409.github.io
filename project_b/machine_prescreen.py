#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""机器谐波预筛（非裁决）：只看候选 A/B 的 1、2、3 次谐波是否有峰。

用途：把 24 窗缩小到"值得请受训听者看"的少数几窗，减少人工负担。
注意：这不是裁决，不计入 f0_verdict；裁决仍以人耳为准。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ADJ = Path(r'D:\wx409.github.io\data\research\experiments\exp-20261025-01\adjudication')


def fundamentals(sup):
    if not sup:
        return set()
    return {s['harmonic'] for s in sup if s.get('peak_hz')}


rows = []
for d in sorted((ADJ / 'materials').glob('adj-*')):
    h = json.loads((d / 'harmonics.json').read_text(encoding='utf-8'))
    a, b = fundamentals(h.get('support_A')), fundamentals(h.get('support_B'))
    a_ok, b_ok = {1, 2, 3} <= a, {1, 2, 3} <= b
    if a_ok and b_ok:
        cls = 'both_complete'
    elif a_ok and not b_ok:
        cls = 'A_complete_B_missing'
    elif b_ok and not a_ok:
        cls = 'B_complete_A_missing'
    else:
        cls = 'both_missing'
    rows.append({"adjudication_id": d.name, "A_harmonics": sorted(a), "B_harmonics": sorted(b),
                 "class": cls, "needs_trained_listener": cls in ('B_complete_A_missing',
                                                                 'A_complete_B_missing',
                                                                 'both_missing')})
out = {"status": "machine_prescreen", "publishable": False,
       "note": "非裁决：仅依据 1/2/3 次谐波是否齐全；不计入 f0_verdict",
       "counts": {k: sum(1 for r in rows if r['class'] == k)
                  for k in ('both_complete', 'A_complete_B_missing', 'B_complete_A_missing', 'both_missing')},
       "rows": rows}
(ADJ / 'machine_prescreen.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print(out['counts'])
print('建议受训听者优先看:', [r['adjudication_id'] for r in rows if r['needs_trained_listener']][:12])
