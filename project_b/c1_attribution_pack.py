#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C1 上海/杭州 人耳归属材料：定位 C2 目标段，切 6 秒片段 + 表单。"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding='utf-8')
BASE = Path(r'E:\wx\论文素材_王晰作传\音域分析')
OUT = Path(r'D:\wx409.github.io\data\research\C1_attribution')
OUT.mkdir(parents=True, exist_ok=True)

# 上海：已有现成片段
sh = Path(r'E:\wx\论文素材_王晰作传\音域分析\听辨样本\待复核_20260916\低_多听有益_C265.2Hz_t55.798_混音.wav')
if sh.exists():
    shutil.copy(sh, OUT / 'C1_上海_多听有益_t55.8_混音.wav')
    print('上海片段已复制:', sh.name)

# 杭州：从 f0.csv 找 65.2Hz 的最长连续段
hz = BASE / '场次音频/_核验素材_20260911_多听有益B1/四巡杭州2024_BV1ArKxe7E8H_BV1ArKxe7E8H'
f0csv = Path(str(hz) + '_f0.csv')
wav = Path(str(hz) + '.wav')
t_hit = None
if f0csv.exists():
    rows = []
    with open(f0csv, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            r = {k.lstrip('\ufeff'): v for k, v in r.items()}
            try:
                v = float(r.get('f0_hz') or 0)
                t = float(r.get('time_s') or 0)
            except Exception:
                continue
            if 64.6 <= v <= 65.8:
                rows.append(t)
    if rows:
        rows.sort()
        best, cur = [], [rows[0]]
        for a, b in zip(rows, rows[1:]):
            if b - a < 0.1:
                cur.append(b)
            else:
                best = max(best, cur, key=len); cur = [b]
        best = max(best, cur, key=len)
        t_hit = round(sum(best) / len(best), 2)
        print(f'杭州 65.2Hz 段: {best[0]:.1f}-{best[-1]:.1f}s（{len(best)} 帧），取中点 {t_hit}s')

if t_hit is not None and wav.exists():
    x, sr = sf.read(str(wav), dtype='float32', always_2d=True)
    m = x.mean(axis=1)
    a = max(0, int((t_hit - 3) * sr)); b = min(len(m), int((t_hit + 3) * sr))
    dest = OUT / f'C1_杭州_多听有益_t{t_hit}_混音.wav'
    sf.write(str(dest), m[a:b], sr)
    print('杭州片段已生成:', dest.name, round((b - a) / sr, 1), 's')

form = {
    "claim": "C1-duoting-c2-repro", "status": "pending", "publishable": False,
    "instructions": "听两段各 6 秒；判断目标段是否王晰本人；只填 是/不是/无法确认",
    "items": [
        {"id": "C1-shanghai", "file": "C1_上海_多听有益_t55.8_混音.wav",
         "source": "四巡上海生日 2024-04-06（BV1RK421h7ks 分P 多听有益）", "t_s": 55.8,
         "verdict": None, "reviewer": "", "date": "", "note": ""},
        {"id": "C1-hangzhou", "file": f'C1_杭州_多听有益_t{t_hit}_混音.wav' if t_hit else None,
         "source": "四巡杭州 2024（BV1ArKxe7E8H）", "t_s": t_hit,
         "verdict": None, "reviewer": "", "date": "", "note": ""},
    ],
}
(OUT / 'form.json').write_text(json.dumps(form, ensure_ascii=False, indent=1), encoding='utf-8')
print('材料目录:', OUT)
