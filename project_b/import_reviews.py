#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 review_sheet.csv 的裁决回填到每窗 form.json，然后可跑 summary。

用法：python -X utf8 project_b/import_reviews.py
规则：
  · 归属列：target / not_target / accompaniment / unclear
  · F0 列：A / B / both_ok / both_bad / unresolved
  · 两列都空的窗口保持 pending
  · 填了裁决但缺 reviewer 或 date → 拒绝（不代填）
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ADJ = Path(r'D:\wx409.github.io\data\research\experiments\exp-20261025-01\adjudication')

ATT = {'target': 'target_singer', 'not_target': 'not_target_singer',
       'accompaniment': 'accompaniment_or_other_voice', 'unclear': 'unclear'}
F0 = {'A': 'candidate_A_more_reasonable', 'B': 'candidate_B_more_reasonable',
      'both_ok': 'both_reasonable_small_difference', 'both_bad': 'both_unreliable',
      'unresolved': 'unresolved'}

sheet = ADJ / 'review_sheet.csv'
if not sheet.exists():
    print('缺少 review_sheet.csv'); sys.exit(1)

rows = list(csv.DictReader(sheet.read_text(encoding='utf-8-sig').splitlines()))
ok = pending = bad = 0
problems = []
for r in rows:
    aid = r['adjudication_id'].strip()
    att = (r.get('归属(填 target/not_target/accompaniment/unclear)') or '').strip().lower()
    f0 = (r.get('F0判读(填 A/B/both_ok/both_bad/unresolved)') or '').strip()
    key_f0 = next((k for k in F0 if k.lower() == f0.lower()), None)
    key_att = next((k for k in ATT if k == att), None)
    if not att and not f0:
        pending += 1
        continue
    if not key_att or not key_f0:
        problems.append(f'{aid}: 取值不合法 att={att!r} f0={f0!r}')
        bad += 1
        continue
    rev = (r.get('reviewer(必填)') or '').strip()
    date = (r.get('review_date(必填)') or '').strip()
    if not rev or not date:
        problems.append(f'{aid}: 缺 reviewer 或 review_date，拒绝回填')
        bad += 1
        continue
    form = json.loads((ADJ / 'materials' / aid / 'form.json').read_text(encoding='utf-8'))
    for k in form['attribution']:
        if k != 'status':
            form['attribution'][k] = None
    for k in form['f0_verdict']:
        if k != 'status':
            form['f0_verdict'][k] = None
    form['attribution'][ATT[key_att]] = True
    form['attribution']['status'] = 'done'
    form['f0_verdict'][F0[key_f0]] = True
    form['f0_verdict']['status'] = 'done'
    form['reason'] = (r.get('理由(可空)') or '').strip()
    form['reviewer'] = rev
    form['review_date'] = date
    (ADJ / 'materials' / aid / 'form.json').write_text(
        json.dumps(form, ensure_ascii=False, indent=1), encoding='utf-8')
    ok += 1

print(f'回填 {ok}｜仍 pending {pending}｜不合格 {bad}')
for p in problems[:10]:
    print(' ·', p)
