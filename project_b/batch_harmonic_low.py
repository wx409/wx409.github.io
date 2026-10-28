#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量谐波筛查：把 55–60Hz 的极低读数逐条放到原始音频上验。

判据：
  · 在 f0、2f0、3f0 处找峰（±3%）
  · f0 峰存在且能量不低于 2f0 峰 10dB → 通过
  · f0 缺失或明显弱于 2f0 → 判为次谐波（YIN 锁到 1/2 周期）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding='utf-8')
STAGE = Path(r'E:\wx\论文素材_王晰作传\_staging_现场')
SUM = Path(r'E:\wx\论文素材_王晰作传\_staging_现场_汇总.json')
OUT = Path(r'D:\wx409.github.io\data\research\live_low_harmonic_check.json')
SR = 44100


def peaks_at(m, sr, f0, ks=(1, 2, 3)):
    w = np.hanning(len(m))
    sp = np.abs(np.fft.rfft(m * w))
    f = np.fft.rfftfreq(len(m), 1 / sr)
    out = []
    for k in ks:
        tgt = f0 * k
        near = (f > tgt * 0.97) & (f < tgt * 1.03)
        if near.any():
            i = np.where(near)[0][np.argmax(sp[near])]
            out.append((k, float(f[i]), float(20 * np.log10(sp[i] + 1e-9))))
        else:
            out.append((k, None, None))
    return out


def main() -> None:
    songs = json.loads(SUM.read_text(encoding='utf-8'))['songs']
    seen_dates = set()
    rows = []
    for s in songs:
        low = s.get('low_stable') or {}
        hz = low.get('hz') or 0
        if not (55.0 <= hz <= 60.5):
            continue
        d = re.search(r'(\d{8})', s['album'])
        key = d.group(1) if d else s['album']
        if key in seen_dates:
            continue
        seen_dates.add(key)
        n0 = (s.get('lowest_notes') or [{}])[0]
        f = STAGE / s['album'] / s['file']
        if not f.exists() or n0.get('t_start') is None:
            rows.append({"song": s['title'], "album": s['album'], "hz": hz, "verdict": "无法复核"})
            continue
        x, sr = sf.read(str(f), start=int(max(0, n0['t_start'] - 0.1) * SR),
                        frames=int(0.35 * SR), dtype='float32', always_2d=True)
        m = x.mean(axis=1)
        pk = peaks_at(m, sr, hz)
        p1, p2 = pk[0][2], pk[1][2]
        if p1 is None:
            verdict = "次谐波（缺 1f0）"
        elif p2 is not None and p1 < p2 - 10:
            verdict = "次谐波（1f0 弱于 2f0 10dB 以上）"
        else:
            verdict = "通过"
        rows.append({"song": s['title'], "album": s['album'], "hz": round(hz, 1),
                     "t_s": round(n0['t_start'], 1), "p1_db": round(p1, 1) if p1 else None,
                     "p2_db": round(p2, 1) if p2 else None, "verdict": verdict})
    OUT.write_text(json.dumps({"schema": "live_low_harmonic_check/v1",
                               "rule": "1f0 存在且不低于 2f0 的 10dB 以上", "rows": rows},
                              ensure_ascii=False, indent=1), encoding='utf-8')
    for r in rows:
        print(f"  {r.get('song','')[:18]:18s} {r.get('hz')}Hz 1f0={r.get('p1_db')} 2f0={r.get('p2_db')} → {r['verdict']}")
    ok = [r for r in rows if r['verdict'] == '通过']
    print(f"\n共 {len(rows)} 条｜通过 {len(ok)}｜存疑/次谐波 {len(rows)-len(ok)}")


if __name__ == '__main__':
    main()
