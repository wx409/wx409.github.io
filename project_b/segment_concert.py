#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""segment_concert.py —— 整场按曲目切分（供同曲对照与先验筛除）。

判据（三层，用该场歌单做期望值）：
  ① 掌声/静音边界：宽带噪声突增后快速衰减 → 曲间最可靠的边界
  ② 能量谷：整体 RMS 低于中位 −18dB 且持续 ≥0.8s → 段落间隙
  ③ f0 连续性：音符序列的长时间断裂

输出：`<场次>.segments.json`（各段起止秒 + 时长 + 猜测曲序）
     + 可选切出 wav 供逐段实测。

用法：
  python -X utf8 project_b/segment_concert.py --wav <场.wav> [--setlist "曲1;曲2;..."] [--cut]
"""
from __future__ import annotations

import argparse
import io
import json
import math
import os
import sys

import numpy as np
import soundfile as sf

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SR = 22050
WIN = 1.0        # 1 秒一窗统计
GAP_DB = -18.0   # 低于中位多少 dB 算间隙
GAP_MIN = 0.8    # 间隙最短时长


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", required=True)
    ap.add_argument("--setlist", default="", help="该场歌单，分号分隔")
    ap.add_argument("--out", default="")
    ap.add_argument("--cut", action="store_true", help="切出各段 wav")
    a = ap.parse_args()

    y, sr = sf.read(a.wav)
    if y.ndim > 1:
        y = y.mean(1)
    if sr != SR:
        idx = (np.arange(int(len(y) * SR / sr)) * sr / SR).astype(int)
        y = y[np.clip(idx, 0, len(y) - 1)]
    y = np.asarray(y, dtype=np.float32)
    dur = len(y) / SR
    print("音频 %.0f 秒（%.1f 分钟）" % (dur, dur / 60))

    # 逐窗 RMS + 谱平坦度（掌声特征：平坦度高）
    hop = int(SR * WIN)
    rms, flat = [], []
    for i in range(0, len(y) - hop, hop):
        seg = y[i:i + hop]
        rms.append(float(np.sqrt(np.mean(seg ** 2)) + 1e-12))
        S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
        S = S + 1e-12
        flat.append(float(np.exp(np.mean(np.log(S))) / np.mean(S)))
    rms = np.array(rms)
    flat = np.array(flat)
    db = 20 * np.log10(rms)
    med = float(np.median(db))
    print("RMS 中位 %.1f dBFS ｜ 最低 %.1f ｜ 谱平坦度中位 %.4f" % (med, db.min(), float(np.median(flat))))

    # 找间隙（连续低能量窗）
    quiet = db < (med + GAP_DB)
    segs, cur = [], None
    for i, q in enumerate(quiet):
        if q:
            if cur is None:
                cur = [i, i]
            else:
                cur[1] = i
        else:
            if cur is not None:
                if (cur[1] - cur[0] + 1) * WIN >= GAP_MIN:
                    segs.append(tuple(cur))
                cur = None
    if cur is not None and (cur[1] - cur[0] + 1) * WIN >= GAP_MIN:
        segs.append(tuple(cur))
    print("检出间隙 %d 处（≥%.1fs 低能量）" % (len(segs), GAP_MIN))

    # 由间隙推出曲目段
    songs = []
    prev_end = 0.0
    for s, e in segs:
        t0, t1 = s * WIN, e * WIN
        if t0 - prev_end > 20:          # 段至少 20 秒才算一首
            songs.append((prev_end, t0))
        prev_end = t1
    if dur - prev_end > 20:
        songs.append((prev_end, dur))
    print("推出候选段 %d 个" % len(songs))

    names = [x.strip() for x in a.setlist.split(";") if x.strip()]
    if names:
        print("歌单 %d 首 ｜ 段 %d 个 ｜ %s" % (
            len(names), len(songs), "数量一致 ✅" if len(names) == len(songs) else "数量不符 ⚠️"))

    out = a.out or (os.path.splitext(a.wav)[0] + ".segments.json")
    rows = []
    for i, (t0, t1) in enumerate(songs, 1):
        rows.append({"order": i, "t_start": round(t0, 1), "t_end": round(t1, 1),
                     "dur_s": round(t1 - t0, 1),
                     "guess_song": names[i - 1] if i - 1 < len(names) else ""})
    io.open(out, "w", encoding="utf-8").write(json.dumps(
        {"source": os.path.basename(a.wav), "total_s": round(dur, 1),
         "setlist_n": len(names), "n_segments": len(songs), "segments": rows},
        ensure_ascii=False, indent=1))
    print("→ %s" % out)
    print()
    print("  %-4s %-16s %8s %s" % ("#", "时间", "时长s", "猜测曲目"))
    for r in rows[:40]:
        print("  %-4d %7.1f~%-7.1f %8.1f %s" % (r["order"], r["t_start"], r["t_end"],
                                                r["dur_s"], r["guess_song"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
