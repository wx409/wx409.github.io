#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""六轨分离复核：htdemucs_6s（bass 单独成轨）后，在 vocals 轨上重测低音。

对比对象：原 htdemucs 两轨结果（live_low_harmonic_stem.json）。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault('HF_HUB_OFFLINE', '1')
import numpy as np
import soundfile as sf
import torch
import torchcrepe
from demucs.api import Separator

sys.path.insert(0, r'D:\wx409.github.io\project_b')
from experiment_dual_engine import yin_frame  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
STAGE = Path(r'E:\wx\论文素材_王晰作传\_staging_现场')
STEM = Path(r'E:\wx\论文素材_王晰作传\_staging_现场_分离6s')
SUM = Path(r'E:\wx\论文素材_王晰作传\_staging_现场_汇总.json')
OUT = Path(r'D:\wx409.github.io\data\research\live_low_6s.json')
SR, WIN, HOP, FRAME = 22050, 6.0, 512, 2048


def main() -> None:
    songs = json.loads(SUM.read_text(encoding='utf-8'))['songs']
    targets = []
    for s in songs:
        low = s.get('low_stable') or {}
        hz = low.get('hz') or 0
        if 55.0 <= hz <= 65.5:
            targets.append((s, hz))
    seen, cases = set(), []
    for s, hz in targets:
        if s['title'] in seen:
            continue
        seen.add(s['title'])
        cases.append((s, hz))
    print('待复核曲目', len(cases), flush=True)

    sep = Separator(model='htdemucs_6s', device='cuda' if torch.cuda.is_available() else 'cpu', progress=False)
    rows = []
    for s, hz in cases:
        src = STAGE / s['album'] / s['file']
        if not src.exists():
            continue
        n0 = (s.get('lowest_notes') or [{}])[0]
        t = n0.get('t_start') or 0
        outdir = STEM / s['album'] / s['title']
        vocals = outdir / 'vocals.wav'
        outdir.mkdir(parents=True, exist_ok=True)
        if not vocals.exists():
            x, sr = sf.read(str(src), dtype='float32', always_2d=True)
            if sr != 44100:
                from math import gcd
                from scipy.signal import resample_poly
                g = gcd(int(sr), 44100)
                x = resample_poly(x, 44100 // g, int(sr) // g, axis=0).astype('float32')
                sr = 44100
            try:
                _, stems = sep.separate_tensor(torch.from_numpy(x.T.copy()), sr)
                v = stems['vocals'].cpu().numpy().T
                sf.write(str(vocals), v, sr, subtype='PCM_16')
            except Exception as e:
                print('分离失败', s['title'], repr(e)[:80], flush=True)
                continue
        v, vsr = sf.read(str(vocals), dtype='float32', always_2d=True)
        m = v.mean(axis=1)
        if vsr != SR:
            idx = np.linspace(0, len(m) - 1, int(len(m) * SR / vsr))
            m = np.interp(idx, np.arange(len(m)), m).astype('float32'); vsr = SR
        a = int(max(0, t - 0.3) * vsr)
        seg = m[a:a + int(1.5 * vsr)]
        # YIN
        ys = []
        w = np.hanning(FRAME)
        for i in range(0, len(seg) - FRAME, HOP):
            y = yin_frame(seg[i:i + FRAME] * w, vsr, 45.0, 1100.0)
            if y > 0:
                ys.append(y)
        yin_lo = float(np.min(ys)) if ys else None
        # CREPE
        if vsr != 16000:
            idx = np.linspace(0, len(m) - 1, int(len(m) * 16000 / vsr))
            m16 = np.interp(idx, np.arange(len(m)), m).astype('float32'); s16 = 16000
        else:
            m16, s16 = m, vsr
        aa = int(max(0, t - 0.3) * s16)
        f0, pd = torchcrepe.predict(torch.tensor(m16[aa:aa + int(1.5 * s16)]).unsqueeze(0), s16,
                                    hop_length=160, fmin=45.0, fmax=1100.0, model='full',
                                    batch_size=1024, device='cuda' if torch.cuda.is_available() else 'cpu',
                                    return_periodicity=True)
        f0 = f0.squeeze().cpu().numpy(); pd = pd.squeeze().cpu().numpy()
        ok = (pd > 0.5) & (f0 > 45)
        crepe_lo = float(f0[ok].min()) if ok.any() else None
        rows.append({"album": s['album'], "song": s['title'], "old_hz": round(hz, 1),
                     "yin6s_min": round(yin_lo, 1) if yin_lo else None,
                     "crepe6s_min": round(crepe_lo, 1) if crepe_lo else None,
                     "agree": bool(yin_lo and crepe_lo and abs(1200 * np.log2(yin_lo / crepe_lo)) < 100)})
        r = rows[-1]
        print(f"  {s['title'][:16]:16s} 旧 {r['old_hz']:5.1f}｜6s YIN {r['yin6s_min']}｜CREPE {r['crepe6s_min']}｜{'一致' if r['agree'] else '不一致'}", flush=True)
        OUT.write_text(json.dumps({"schema": "live_low_6s/v1", "rows": rows}, ensure_ascii=False, indent=1), encoding='utf-8')
    okn = sum(1 for r in rows if r['agree'])
    print(f'\n完成 {len(rows)}｜一致 {okn}')


if __name__ == '__main__':
    main()
