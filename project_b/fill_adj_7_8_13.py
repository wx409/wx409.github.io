#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回填 adj-07 / adj-08 / adj-13 的听辨结论（听者 star，2026-10-25）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ADJ = Path(r'D:\wx409.github.io\data\research\experiments\exp-20261025-01\adjudication')
FIX = {
    'adj-07': ('target_singer', 'candidate_A_more_reasonable', '两个候选 110/215，听者确认他在唱低音 → 取 110'),
    'adj-08': ('target_singer', 'candidate_A_more_reasonable', '两个候选 287/75，听者确认他在唱高音 → 取 287'),
    'adj-13': ('unclear', 'unresolved', '听者确认在唱高音但分不清是否本人 → 归属存疑，F0 不判'),
}
for aid, (att, f0, reason) in FIX.items():
    p = ADJ / 'materials' / aid / 'form.json'
    f = json.loads(p.read_text(encoding='utf-8'))
    for k in f['attribution']:
        if k != 'status':
            f['attribution'][k] = None
    for k in f['f0_verdict']:
        if k != 'status':
            f['f0_verdict'][k] = None
    f['attribution'][att] = True
    f['attribution']['status'] = 'done'
    f['f0_verdict'][f0] = True
    f['f0_verdict']['status'] = 'done'
    f['reviewer'] = 'star'
    f['review_date'] = '2026-10-25'
    f['reason'] = reason
    p.write_text(json.dumps(f, ensure_ascii=False, indent=1), encoding='utf-8')
    print('回填', aid, att, f0)
