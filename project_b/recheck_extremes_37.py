#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""极值音复核（37 场小卡带）：每场取最低 3 个音，跑双引擎 + 谐波，按新门槛判定。"""
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
OUT = Path(r'D:\wx409.github.io\data\research\extreme_recheck.json')
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
    # 只看 37 场小卡带（album 形如 sNN_YYYYMMDD）
    shows = {}
    for s in songs:
        a = s['album']
        if not a.startswith('s') or '_' not in a:
            continue
        shows.setdefault(a, []).append(s)
    rows = []
    for album, arr in sorted(shows.items()):
        lows = []
        for s in arr:
            for n in (s.get('lowest_notes') or [])[:2]:
                lows.append((n['hz'], s, n))
        lows.sort(key=lambda x: x[0])
        for hz, s, n in lows[:3]:
            stem = SEP / album / s['title'] / 'htdemucs' / 'input_ascii' / 'vocals.wav'
            src = STAGE / album / s['file']
            if not stem.exists() or not src.exists():
                continue
            t = n.get('t_start')
            if t is None:
                continue
            v, vsr = sf.read(str(stem), dtype='float32', always_2d=True); vm = v.mean(axis=1)
            o, osr = sf.read(str(src), dtype='float32', always_2d=True); om = o.mean(axis=1)
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
            yin_med, crepe_med = float(np.median(ys)), float(np.median(f0[ok]))
            diff = 1200 * np.log2(yin_med / crepe_med)
            harm = peaks(os_, osr, hz)
            harm_ok = bool(harm[0] is not None and (harm[1] is None or harm[0] >= harm[1] - 10))
            pass_all = bool(abs(diff) <= 50 and harm_ok)
            rows.append({"show": album, "song": s['title'], "note": n['note'],
                         "claimed_hz": round(hz, 1), "diff_cents": round(diff, 1),
                         "harm": harm, "harm_ok": harm_ok, "pass": pass_all})
    OUT.write_text(json.dumps({"schema": "extreme_recheck/v1",
                               "rule": "|diff|<=50c 且 1f0 不弱于 2f0 超过 10dB", "rows": rows},
                              ensure_ascii=False, indent=1), encoding='utf-8')
    n = len(rows)
    ok = sum(1 for r in rows if r['pass'])
    print(f'场级极值窗口 {n}｜通过 {ok}（{ok/n*100:.0f}%）')
    bad = [r for r in rows if not r['pass']]
    for r in bad[:8]:
        print('  未通过', r['show'], r['song'][:14], r['note'], r['diff_cents'], r['harm'])


if __name__ == '__main__':
    main()
