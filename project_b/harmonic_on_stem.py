#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在**分离人声轨**上复核 55–65Hz 低音读数（混音缺基频，必须在人声轨上判）。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.stdout.reconfigure(encoding='utf-8')
SEP = Path(r'E:\wx\论文素材_王晰作传\_staging_现场_分离')
SUM = Path(r'E:\wx\论文素材_王晰作传\_staging_现场_汇总.json')
OUT = Path(r'D:\wx409.github.io\data\research\live_low_harmonic_stem.json')
SR = 44100


def peaks(m, sr, f0, ks=(1, 2, 3)):
    w = np.hanning(len(m)); sp = np.abs(np.fft.rfft(m * w))
    f = np.fft.rfftfreq(len(m), 1 / sr); out = []
    for k in ks:
        t = f0 * k; near = (f > t * 0.97) & (f < t * 1.03)
        if near.any():
            i = np.where(near)[0][np.argmax(sp[near])]
            out.append(round(float(20 * np.log10(sp[i] + 1e-9)), 1))
        else:
            out.append(None)
    return out


def main() -> None:
    songs = json.loads(SUM.read_text(encoding='utf-8'))['songs']
    seen, rows = set(), []
    for s in songs:
        low = s.get('low_stable') or {}
        hz = low.get('hz') or 0
        if not (55.0 <= hz <= 65.5):
            continue
        d = re.search(r'(\d{8})', s['album'])
        key = (d.group(1) if d else s['album'], s['title'])
        if key in seen:
            continue
        seen.add(key)
        stem = SEP / s['album'] / s['title'] / 'htdemucs' / 'input_ascii' / 'vocals.wav'
        n0 = (s.get('lowest_notes') or [{}])[0]
        if not stem.exists() or n0.get('t_start') is None:
            continue
        x, sr = sf.read(str(stem), start=int(max(0, n0['t_start'] - 0.1) * SR),
                        frames=int(0.35 * SR), dtype='float32', always_2d=True)
        m = x.mean(axis=1)
        p1, p2, p3 = peaks(m, sr, hz)
        if p1 is None:
            verdict = '次谐波（缺 1f0）'
        elif p2 is not None and p1 < p2 - 10:
            verdict = '次谐波（1f0 弱于 2f0 10dB+）'
        else:
            verdict = '通过'
        rows.append({"album": s['album'], "song": s['title'], "hz": round(hz, 1),
                     "p1": p1, "p2": p2, "p3": p3, "verdict": verdict})
    OUT.write_text(json.dumps({"schema": "live_low_harmonic_stem/v1", "rows": rows},
                              ensure_ascii=False, indent=1), encoding='utf-8')
    for r in rows:
        print(f"  {r['song'][:16]:16s} {r['hz']:6.1f}Hz 1f0={r['p1']} 2f0={r['p2']} → {r['verdict']}")
    print(f"\n共 {len(rows)}｜通过 {sum(1 for r in rows if r['verdict']=='通过')}")


if __name__ == '__main__':
    main()
