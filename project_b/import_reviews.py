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

raw = sheet.read_bytes()
text = None
for enc in ('utf-8-sig', 'gbk', 'utf-8', 'cp936'):
    try:
        text = raw.decode(enc)
        print('表编码:', enc)
        break
    except Exception:
        continue
if text is None:
    text = raw.decode('utf-8', errors='replace')
    print('表编码: utf-8(替换)')
lines = text.splitlines()
header = next(csv.reader([lines[0]]))
def col(*keys):
    for i, h in enumerate(header):
        if any(k in h for k in keys):
            return i
    return None
C_ATT, C_F0 = col('归属'), col('F0')
C_REV, C_DATE = col('reviewer'), col('review_date')
C_REASON = col('理由')
rows = []
for ln in lines[1:]:
    if not ln.strip():
        continue
    cells = next(csv.reader([ln]))
    cells += [''] * (len(header) - len(cells))
    rows.append({'adjudication_id': cells[0].strip(), 'segment_id': cells[1].strip(),
                 'att': cells[C_ATT].strip() if C_ATT is not None else '',
                 'f0': cells[C_F0].strip() if C_F0 is not None else '',
                 'reason': cells[C_REASON].strip() if C_REASON is not None else '',
                 'reviewer': cells[C_REV].strip() if C_REV is not None else '',
                 'date': cells[C_DATE].strip() if C_DATE is not None else ''})
ok = pending = bad = 0
problems = []
for r in rows:
    aid = r['adjudication_id']
    att = r['att'].lower()
    f0 = r['f0']
    key_f0 = next((k for k in F0 if k.lower() == f0.lower()), None)
    key_att = next((k for k in ATT if k == att), None)
    if not att and not f0:
        pending += 1
        continue
    if (att and not key_att) or (f0 and not key_f0):
        problems.append(f'{aid}: 取值不合法 att={att!r} f0={f0!r}')
        bad += 1
        continue
    rev = r['reviewer']
    date = r['date']
    # 兼容"名字 + 日期"写在同一格
    import re as _re
    m = _re.search(r'(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})', rev)
    if m and not date:
        date = m.group(1).replace('/', '-').replace('.', '-')
        rev = (rev[:m.start()] + rev[m.end():]).strip(' ,;')
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
    if key_att:
        form['attribution'][ATT[key_att]] = True
        form['attribution']['status'] = 'done'
    if key_f0:
        form['f0_verdict'][F0[key_f0]] = True
        form['f0_verdict']['status'] = 'done'
    form['partial'] = not (key_att and key_f0)
    form['reason'] = r['reason']
    form['reviewer'] = rev
    form['review_date'] = date
    (ADJ / 'materials' / aid / 'form.json').write_text(
        json.dumps(form, ensure_ascii=False, indent=1), encoding='utf-8')
    ok += 1

print(f'回填 {ok}（其中部分填写 {sum(1 for _ in []) if False else 0}）｜仍 pending {pending}｜不合格 {bad}')
for p in problems[:10]:
    print(' ·', p)
