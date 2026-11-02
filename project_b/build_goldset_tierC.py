#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""金标集扩样（C 档：B 站转码素材）：20 首，验证来源质量是否影响一致性。"""
from __future__ import annotations

import json
import os
import random
import sys
from pathlib import Path

os.environ.setdefault('HF_HUB_OFFLINE', '1')
import numpy as np
import soundfile as sf
import torch
import torchcrepe

sys.path.insert(0, r'D:\wx409.github.io\project_b')
from experiment_dual_engine import yin_frame  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
SUM = Path(r'E:\wx\论文素材_王晰作传\_staging_现场_汇总.json')
STAGE = Path(r'E:\wx\论文素材_王晰作传\_staging_现场')
SEP = Path(r'E:\wx\论文素材_王晰作传\_staging_现场_分离')
OUT = Path(r'D:\wx409.github.io\data\research\goldset_tierC.json')
WIN = 1.4


def peaks(m, sr, f0):
    sp = np.abs(np.fft.rfft(m * np.hanning(len(m))))
    f = np.fft.rfftfreq(len(m), 1 / sr)
    out = []
    for k in (1, 2, 3):
        t = f0 * k
        near = (f > t * 0.97) & (f < t * 1.03)
        out.append(round(float(20 * np.log10(sp[near].max() + 1e-9)), 1) if near.any() else None)
    return out


def main() -> None:
    songs = json.loads(SUM.read_text(encoding='utf-8'))['songs']
    pool = [s for s in songs if s['album'].startswith('s') and s.get('lowest_notes')]
    random.seed(20261031)
    random.shuffle(pool)
    rows = []
    for s in pool:
        if len({r['song'] for r in rows}) >= 20:
            break
        if any(r['song'] == s['title'] for r in rows):
            continue
        stem = SEP / s['album'] / s['title'] / 'htdemucs' / 'input_ascii' / 'vocals.wav'
        src = STAGE / s['album'] / s['file']
        if not stem.exists() or not src.exists():
            continue
        v, vsr = sf.read(str(stem), dtype='float32', always_2d=True); vm = v.mean(axis=1)
        o, osr = sf.read(str(src), dtype='float32', always_2d=True); om = o.mean(axis=1)
        for n in s['lowest_notes'][:3]:
            t = n.get('t_start')
            if t is None:
                continue
            a0 = max(0, t - (WIN - 0.25) / 2)
            vs = vm[int(a0 * vsr):int((a0 + WIN) * vsr)]
            os_ = om[int(a0 * osr):int((a0 + WIN) * osr)]
            if len(vs) < 2048 or len(os_) < 2048:
                continue
            ys = [yin_frame(vs[i:i + 2048] * np.hanning(2048), vsr, 45, 1100)
                  for i in range(0, len(vs) - 2048, 512)]
            ys = [y for y in ys if y > 0]
            idx = np.linspace(0, len(vs) - 1, int(len(vs) * 16000 / vsr))
            v16 = np.interp(idx, np.arange(len(vs)), vs).astype('float32')
            f0, pd = torchcrepe.predict(torch.tensor(v16).unsqueeze(0), 16000, hop_length=160,
                                        fmin=45, fmax=1100, model='full', batch_size=1024,
                                        device='cuda' if torch.cuda.is_available() else 'cpu',
                                        return_periodicity=True)
            f0 = f0.squeeze().cpu().numpy(); pd = pd.squeeze().cpu().numpy()
            ok = (pd > 0.5) & (f0 > 45)
            if not ok.any() or not ys:
                continue
            diff = 1200 * np.log2(np.median(ys) / np.median(f0[ok]))
            harm = peaks(os_, osr, n['hz'])
            harm_ok = bool(harm[0] is not None and (harm[1] is None or harm[0] >= harm[1] - 10))
            rows.append({"song": s['title'], "album": s['album'], "note": n['note'],
                         "claimed_hz": round(n['hz'], 1), "diff_cents": round(diff, 1),
                         "harm_ok": harm_ok, "pass": bool(abs(diff) <= 50 and harm_ok)})
    OUT.write_text(json.dumps({"schema": "goldset_tierC/v1", "rows": rows}, ensure_ascii=False, indent=1),
                   encoding='utf-8')
    n = len(rows)
    print(f'C 档窗口 {n}｜一致 {sum(1 for r in rows if abs(r["diff_cents"])<=50)}｜'
          f'谐波通过 {sum(1 for r in rows if r["harm_ok"])}｜全通过 {sum(1 for r in rows if r["pass"])}')


if __name__ == '__main__':
    main()
