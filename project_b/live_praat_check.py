#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""现场素材双引擎对照：在**同一段原始混音、同一 6 秒窗口**上同时跑 YIN 与 Praat。

说明：生产口径的 YIN 跑在 demucs 人声轨上；本脚本为了公平对照，两引擎都读原始混音，
因此结果只用于「引擎间一致性」，不替代生产读数。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import parselmouth
import soundfile as sf

sys.path.insert(0, str(Path(r'D:\wx409.github.io\project_b')))
from experiment_dual_engine import yin_frame  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
BASE = Path(r'E:\wx\论文素材_王晰作传\现场录音-小卡带')
SUMMARY = Path(r'E:\wx\论文素材_王晰作传\现场录音-小卡带_汇总.json')
OUT = Path(r'D:\wx409.github.io\data\research\live_praat_check.json')
SR, WIN, HOP, FRAME = 22050, 6.0, 512, 2048


def load_mono(p: Path):
    x, sr = sf.read(str(p), dtype='float32', always_2d=True)
    m = x.mean(axis=1)
    if sr != SR:
        idx = np.linspace(0, len(m) - 1, int(len(m) * SR / sr))
        m = np.interp(idx, np.arange(len(m)), m).astype('float32')
    return m


def main() -> None:
    d = json.loads(SUMMARY.read_text(encoding='utf-8'))
    rows = []
    for s in d['songs']:
        album, fn = s.get('album'), s.get('file')
        f = BASE / album / fn
        if not f.exists():
            continue
        lows = s.get('lowest_notes') or []
        if not lows:
            continue
        note = lows[0]
        t0 = max(0.0, note['t_start'] - 2.0)
        m = load_mono(f)
        seg = m[int(t0 * SR):int(t0 * SR) + int(WIN * SR)]
        if len(seg) < int(WIN * SR) * 0.8:
            continue
        # YIN
        ys, win = [], np.hanning(FRAME)
        for i in range(0, len(seg) - FRAME, HOP):
            fr = seg[i:i + FRAME] * win
            if np.sqrt(np.mean(fr ** 2)) < 0.005:
                continue
            v = yin_frame(fr, SR, 55.0, 1100.0)
            if v > 0:
                ys.append(v)
        # Praat
        snd = parselmouth.Sound(seg.astype('float64'), sampling_frequency=SR)
        pitch = snd.to_pitch(time_step=HOP / SR, pitch_floor=55.0, pitch_ceiling=1100.0)
        ps = [pitch.get_value_at_time(i * HOP / SR) for i in range(1, pitch.get_number_of_frames() + 1)]
        ps = [p for p in ps if p and p == p and p > 0]
        if not ys or not ps:
            rows.append({"song": s.get('title'), "album": album, "status": "no_data"})
            continue
        yin_low, praat_low = float(np.min(ys)), float(np.min(ps))
        cents = 1200 * np.log2(yin_low / praat_low)
        rows.append({
            "song": s.get('title'), "album": album, "t_s": round(t0, 1),
            "yin_low_hz": round(yin_low, 2), "praat_low_hz": round(praat_low, 2),
            "diff_cents": round(cents, 1),
            "yield_note": note.get('note'), "yield_hz": round(note['hz'], 2),
            "status": "ok",
        })
        print(f"{s.get('title')[:28]:28s} YIN {yin_low:6.1f} | Praat {praat_low:6.1f} | {cents:+6.1f} 音分")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": "live_praat_check/v1", "status": "exploratory",
                               "note": "两引擎均读原始混音同一窗口；仅说明引擎一致性",
                               "count": len(rows), "rows": rows}, ensure_ascii=False, indent=1),
                   encoding='utf-8')
    ok = [r for r in rows if r['status'] == 'ok']
    print(f'完成 {len(ok)} 首 → {OUT}')


if __name__ == '__main__':
    main()
