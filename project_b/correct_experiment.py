#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""更正 exp-20261025-01：录音室层混入非目标歌手（赵鹏）。

纪律：不改冻结的原始清单与逐帧文件；另存更正记录与重算结果。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
EXP = Path(r'D:\wx409.github.io\data\research\experiments\exp-20261025-01')

man = json.loads((EXP / 'segment_manifest.json').read_text(encoding='utf-8'))
invalid, flagged = [], []
for i in man['items']:
    ident = i['identity']
    if ident.startswith('赵鹏/'):
        invalid.append({"segment_id": i['segment_id'], "identity": ident,
                        "reason": "非目标歌手（赵鹏），不应进入王晰录音室层"})
    elif ident.startswith('龙源之声/'):
        flagged.append({"segment_id": i['segment_id'], "identity": ident,
                        "reason": "合辑来源、曲名不可识别，归属待核"})

corr = {"experiment_id": man['experiment_id'], "status": "correction",
        "invalid": invalid, "flagged": flagged,
        "note": "原始清单与逐帧文件保持不动；以下为更正与重算"}
(EXP / 'segment_manifest_corrections.json').write_text(
    json.dumps(corr, ensure_ascii=False, indent=1), encoding='utf-8')

# 重算比较（剔除 invalid）
cmp = json.loads((EXP / 'comparison.json').read_text(encoding='utf-8'))
bad = {x['segment_id'] for x in invalid}
rows = [r for r in cmp['rows'] if r['segment_id'] not in bad and r.get('comparable')]
def agg(layer):
    sub = [r for r in rows if r['layer'] == layer]
    if not sub:
        return {"segments": 0}
    return {"segments": len(sub),
            "agree_pct_median": round(float(np.median([r['agree_pct'] for r in sub])), 1),
            "octave_pct_median": round(float(np.median([r['octave_pct'] for r in sub])), 1),
            "nonctave_pct_median": round(float(np.median([r['nonoctave_pct'] for r in sub])), 1),
            "abs_cents_median": round(float(np.median([r['abs_cents_median'] for r in sub])), 1)}
out = {"experiment_id": man['experiment_id'], "status": "exploratory", "publishable": False,
       "excluded_segments": sorted(bad),
       "note": "剔除非目标歌手窗口后重算；仅描述本批有效窗口",
       "summary": {l: agg(l) for l in ('录音室人声轨', '现场混音')}}
(EXP / 'comparison_corrected.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('更正记录与重算已写入')
print(json.dumps(out['summary'], ensure_ascii=False, indent=1))
