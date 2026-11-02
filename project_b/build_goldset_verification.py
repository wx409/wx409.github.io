#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""金标集：真实素材上的双引擎一致性 + 极值音谐波复核。

对每个曲目的最低 3 个稳定音：
  · 在人声轨上同一窗口跑 YIN 与 CREPE，比中位差（±50 音分为一致）
  · 在原始音轨上查 1f0/2f0/3f0 峰值，判极值是否有基频支持
输出：data/research/goldset_verification.json
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

sys.path.insert(0, r'D:\wx409.github.io\project_b')
from experiment_dual_engine import yin_frame  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
SUM = Path(r'E:\wx\论文素材_王晰作传\_staging_现场_汇总.json')
STAGE = Path(r'E:\wx\论文素材_王晰作传\_staging_现场')
SEP = Path(r'E:\wx\论文素材_王晰作传\_staging_现场_分离')
OUT = Path(r'D:\wx409.github.io\data\research\goldset_verification.json')
ALBUMS = ['h5_bj_20231112', 'h5_sh_20251121_ok']
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
    rows = []
    for s in songs:
        if s['album'] not in ALBUMS:
            continue
        stem = SEP / s['album'] / s['title'] / 'htdemucs' / 'input_ascii' / 'vocals.wav'
        src = STAGE / s['album'] / s['file']
        if not stem.exists() or not src.exists():
            continue
        v, vsr = sf.read(str(stem), dtype='float32', always_2d=True)
        vm = v.mean(axis=1)
        orig, osr = sf.read(str(src), dtype='float32', always_2d=True)
        om = orig.mean(axis=1)
        for n in (s.get('lowest_notes') or [])[:3]:
            t = n.get('t_start')
            if t is None:
                continue
            a = max(0, t - (WIN - 0.25) / 2)
            vs = vm[int(a * vsr):int((a + WIN) * vsr)]
            os_ = om[int(a * osr):int((a + WIN) * osr)]
            if len(vs) < 2048 or len(os_) < 2048:
                continue
            # YIN
            ys = []
            for i in range(0, len(vs) - 2048, 512):
                y = yin_frame(vs[i:i + 2048] * np.hanning(2048), vsr, 45, 1100)
                if y > 0:
                    ys.append(y)
            # CREPE
            idx = np.linspace(0, len(vs) - 1, int(len(vs) * 16000 / vsr))
            v16 = np.interp(idx, np.arange(len(vs)), vs).astype('float32')
            f0, pd = torchcrepe.predict(torch.tensor(v16).unsqueeze(0), 16000, hop_length=160,
                                        fmin=45, fmax=1100, model='full', batch_size=1024,
                                        device='cuda' if torch.cuda.is_available() else 'cpu',
                                        return_periodicity=True)
            f0 = f0.squeeze().cpu().numpy(); pd = pd.squeeze().cpu().numpy()
            ok = (pd > 0.5) & (f0 > 45)
            crepe_med = float(np.median(f0[ok])) if ok.any() else None
            yin_med = float(np.median(ys)) if ys else None
            diff = (1200 * np.log2(yin_med / crepe_med)) if (yin_med and crepe_med) else None
            harm = peaks(os_, osr, n['hz'])
            rows.append({
                "song": s['title'], "album": s['album'], "note": n['note'], "claimed_hz": round(n['hz'], 1),
                "t": round(t, 1), "yin_med": round(yin_med, 1) if yin_med else None,
                "crepe_med": round(crepe_med, 1) if crepe_med else None,
                "diff_cents": round(diff, 1) if diff is not None else None,
                "agree_50c": bool(diff is not None and abs(diff) <= 50),
                "harm_1_2_3": harm,
                "harm_ok": bool(harm[0] is not None and (harm[1] is None or harm[0] >= harm[1] - 10)),
            })
    OUT.write_text(json.dumps({"schema": "goldset_verification/v1", "rows": rows}, ensure_ascii=False, indent=1),
                   encoding='utf-8')
    n = len(rows)
    agree = sum(1 for r in rows if r['agree_50c'])
    hok = sum(1 for r in rows if r['harm_ok'])
    diffs = [abs(r['diff_cents']) for r in rows if r['diff_cents'] is not None]
    print(f'窗口 {n}｜双引擎一致 {agree}（{agree/n*100:.0f}%）｜谐波通过 {hok}（{hok/n*100:.0f}%）')
    if diffs:
        print('偏差中位 %.1f 音分｜P90 %.1f' % (np.median(diffs), np.percentile(diffs, 90)))


if __name__ == '__main__':
    main()
