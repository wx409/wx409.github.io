#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""measure_mic_pull.py —— 「拉麦」检测（音量变了，发声状态没变）。

原理（用户 2026-09-17 提出，是一项独立技能维度）：
  拉麦 = 唱强音/高音时把话筒拉远，用来控音量、避爆音、做远近层次。
  声学特征：**同一持续音内 RMS 显著下降，而 f0 与谐波结构保持稳定。**
  与"弱唱"的区别：弱唱 = RMS↓ **且** 谐波能量↓；拉麦 = RMS↓ **但** 谐波结构不变。

判据（在音符内部逐帧）：
  取一个持续音（≥0.4s），计算其内部的：
    · RMS 轨迹（dB）
    · 谐波能量占比 hratio（1–10 次谐波能量 / 总能量）→ 代表"发声用力程度"
  若某帧相对该音符前段：RMS 下降 ≥4dB 而 hratio 变化 ≤3dB
    → 计一次「拉麦事件」

输出：每首的 拉麦次数 / 时长占比 / 幅度中位 / 与音高的关系。

用法：
  python -X utf8 project_b/measure_mic_pull.py --wav <某.wav> [--f0 <对应_f0.csv>]
  python -X utf8 project_b/measure_mic_pull.py --root <分析目录>   # 批量
"""
from __future__ import annotations

import argparse
import csv
import glob
import io
import json
import math
import os
import statistics as st
import sys

import numpy as np
import soundfile as sf

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SR = 22050
N = 2048
RMS_DROP_DB = 4.0      # RMS 下降阈值
HRATIO_TOL_DB = 3.0    # 谐波占比允许的变化（超过则视为"真的弱唱"）
MIN_NOTE = 0.4         # 音符最短时长
RECOVER_DB = 2.0       # ★ 判据 B：拉麦必有来回 —— RMS 降到最低后须回升 ≥2dB


def load(p):
    y, sr = sf.read(p)
    if y.ndim > 1:
        y = y.mean(1)
    if sr != SR:
        idx = (np.arange(int(len(y) * SR / sr)) * sr / SR).astype(int)
        y = y[np.clip(idx, 0, len(y) - 1)]
    return np.asarray(y, dtype=np.float32)


def frame_feat(y, t, f0):
    i = int(t * SR)
    if i < 0 or i + N > len(y):
        return None
    seg = y[i:i + N]
    if float(np.sqrt(np.mean(seg ** 2))) < 1e-6:
        return None
    S = np.abs(np.fft.rfft(seg * np.hanning(N)))
    fr = np.fft.rfftfreq(N, 1 / SR)
    e = S ** 2
    tot = float(e.sum()) + 1e-12
    rms = 20 * math.log10(float(np.sqrt(np.mean(seg ** 2))) + 1e-12)
    harm = 0.0
    for n in range(1, 11):
        f = f0 * n
        m = np.abs(fr - f) <= max(8.0, f * 0.02)
        if m.any():
            harm += float(e[m].max())
    hratio = 10 * math.log10(max(1e-12, harm) / max(1e-12, tot - harm))
    return rms, hratio


def analyse(wav, f0csv):
    y = load(wav)
    if not os.path.exists(f0csv):
        return None
    rr = list(csv.DictReader(io.open(f0csv, encoding="utf-8", errors="replace")))
    if not rr:
        return None
    cols = list(rr[0].keys())
    tc = cols[0]
    fc = next((c for c in cols if "f0" in c.lower() or "hz" in c.lower()), cols[1])
    P = []
    for x in rr:
        try:
            t, v = float(x[tc]), float(x[fc])
        except Exception:
            continue
        if v and v > 0:
            P.append((t, v))
    # 切音符
    notes, cur = [], None
    for t, v in P:
        if cur is None:
            cur = [t, t, [v]]
        elif abs(12 * math.log2(v / cur[2][-1])) < 0.6:
            cur[1] = t; cur[2].append(v)
        else:
            notes.append(cur); cur = [t, t, [v]]
    if cur:
        notes.append(cur)
    notes = [(a, b, float(st.median(c))) for a, b, c in notes if b - a >= MIN_NOTE]

    events = []
    for a, b, f0 in notes:
        fr_list = []
        t = a
        while t <= b:
            r = frame_feat(y, t, f0)
            if r:
                fr_list.append((t, r[0], r[1]))
            t += 0.05
        if len(fr_list) < 6:
            continue
        head = fr_list[:max(3, len(fr_list) // 4)]
        base_rms = st.median([x[1] for x in head])
        base_h = st.median([x[2] for x in head])
        # ★ 判据 B：找 RMS 谷底，再确认其后有回升（拉远→推近）
        d_series = [x[1] - base_rms for x in fr_list]
        i_min = int(np.argmin(d_series))
        drop = d_series[i_min]
        if drop <= -RMS_DROP_DB:
            after = d_series[i_min:]
            recov = (max(after) - drop) if after else 0.0
            inside = abs(fr_list[i_min][2] - base_h) <= HRATIO_TOL_DB
            if recov >= RECOVER_DB and inside:
                events.append({"t": round(fr_list[i_min][0], 2), "note_hz": round(f0, 1),
                               "rms_drop_db": round(drop, 1),
                               "recover_db": round(recov, 1),
                               "hratio_delta_db": round(fr_list[i_min][2] - base_h, 1)})
    dur = P[-1][0] - P[0][0] if P else 0
    return {"note_count": len(notes), "duration_s": round(dur, 1),
            "pull_events": len(events), "events": events[:60],
            "pull_rate_per_min": round(len(events) / (dur / 60), 2) if dur > 0 else 0,
            "median_drop_db": round(st.median([e["rms_drop_db"] for e in events]), 1) if events else None,
            "median_note_hz": round(st.median([e["note_hz"] for e in events]), 1) if events else None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", default="")
    ap.add_argument("--f0", default="")
    ap.add_argument("--root", default="")
    a = ap.parse_args()
    res = []
    if a.wav:
        f0 = a.f0 or (os.path.splitext(a.wav)[0] + "_f0.csv")
        r = analyse(a.wav, f0)
        if r:
            res.append((os.path.basename(a.wav), r))
    elif a.root:
        for d in sorted(glob.glob(os.path.join(a.root, "*"))):
            if not os.path.isdir(d):
                continue
            f = glob.glob(os.path.join(d, "*_f0.csv"))
            if not f:
                continue
            cand = glob.glob(os.path.join(d, "*.wav"))
            if not cand:
                sib = a.root.replace("_分析", "")
                cand = glob.glob(os.path.join(sib, os.path.basename(d), "*.wav"))
            if not cand:
                cand = glob.glob(os.path.join(
                    r"E:\wx\论文素材_王晰作传\音域分析\专辑音频",
                    "*", os.path.basename(d) + ".mp3"))
            if cand and f:
                r = analyse(cand[0], f[0])
                if r:
                    res.append((os.path.basename(d), r))
    print("=" * 104)
    print("「拉麦」检测（RMS↓ 而谐波结构不变 = 拉麦；两者同降 = 弱唱）")
    print("=" * 104)
    print("  %-40s %6s %9s %9s %9s" % ("素材", "音符", "拉麦次", "次/分", "幅度dB"))
    for name, r in res:
        print("  %-40s %6d %9d %9.2f %9s" % (name[:40], r["note_count"], r["pull_events"],
                                              r["pull_rate_per_min"], r["median_drop_db"] or "—"))
    if res:
        rates = [r["pull_rate_per_min"] for _, r in res if r["pull_events"]]
        if rates:
            print()
            print("  【中位】拉麦 %.2f 次/分钟（%d/%d 素材检出）"
                  % (st.median(rates), len(rates), len(res)))
    out = r"D:\wx409.github.io\temp\_mic_pull.json"
    io.open(out, "w", encoding="utf-8").write(json.dumps(
        [{"name": n, **r} for n, r in res], ensure_ascii=False, indent=1))
    print("  → %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
