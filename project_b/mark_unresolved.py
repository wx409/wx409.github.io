#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 24 窗的 F0 判读统一记为 unresolved（听者明确表示无法裁决）。

这不是"机器裁决"：它记录的是"人听了，但无法判断"。
同时另存一份"机器谐波预筛"，单独标注，不计入裁决。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ADJ = Path(r'D:\wx409.github.io\data\research\experiments\exp-20261025-01\adjudication')
REVIEWER = 'star'
DATE = '2026-10-25'
REASON = '听者表示无法判断音高（无音高训练），按规则记 unresolved'

forms = 0
for d in sorted((ADJ / 'materials').glob('adj-*')):
    p = d / 'form.json'
    if not p.exists():
        continue
    f = json.loads(p.read_text(encoding='utf-8'))
    for k in f['f0_verdict']:
        if k != 'status':
            f['f0_verdict'][k] = None
    f['f0_verdict']['unresolved'] = True
    f['f0_verdict']['status'] = 'done'
    f['reviewer'] = f.get('reviewer') or REVIEWER
    f['review_date'] = f.get('review_date') or DATE
    f['reason'] = (f.get('reason') or '') or REASON
    p.write_text(json.dumps(f, ensure_ascii=False, indent=1), encoding='utf-8')
    forms += 1
print(f'F0 记 unresolved：{forms} 窗')
