#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_style_metrics.py —— 生成 data/archive_style.json（演唱风格量化指标）。

为什么做成生成器（与前缀纪律一致）：
  "打两份工/过山车"与"低的要高唱/低音亮度"这两个风格特征，
  是 2026-09-16 由用户听感提出、再经实测验证的**可测行为**。
  临时脚本算过就丢 → 必须固化为生成器，随数据自动更新、可复现、可挑战。

两个指标（口径写死，引用前必看）：
  ① 极端交替（"打两份工"）：相邻音符音高差 ≥12 半音且间隔 ≤0.5s 的处数 ÷ 时长（次/分钟）
     —— 用户定义：「高音后马上接低音、低音后马上升高」，**不是全曲跨度**
  ② 低音亮度（"低的要高唱"）：低音区（f0 50–110Hz）与中音区（150–350Hz）
     的**频谱质心中位之比**。常态男低音应 ≪1（低音暗）；他接近 1。
     —— 在**原始混音**上测（对照试验证明比分离轨更保守、且排除 demucs artifact）

产出：D:\\wx409.github.io\\data\\archive_style.json
用法：python -X utf8 project_b/build_style_metrics.py
"""
from __future__ import annotations

import csv
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AN = r"E:\wx\论文素材_王晰作传\音域分析"
F0_ROOT = os.path.join(AN, "分析结果_专辑")
AUDIO_ROOT = os.path.join(AN, "专辑音频")
OUT = os.path.join(ROOT, "data", "archive_style.json")

SR, N = 22050, 2048
LO_BAND = (50, 110)      # 低音区
MID_BAND = (150, 350)    # 中音区
ALT_SEMI = 12.0          # 极端交替的音高差门槛（一个八度）
ALT_GAP = 0.5            # 极端交替的时间间隔门槛（秒）


def load_csv(f):
    rr = list(csv.DictReader(io.open(f, encoding="utf-8", errors="replace")))
    if not rr:
        return []
    cols = list(rr[0].keys())
    tc = cols[0]
    fc = next((c for c in cols if "f0" in c.lower() or "hz" in c.lower()), cols[1])
    out = []
    for x in rr:
        try:
            t, v = float(x[tc]), float(x[fc])
        except Exception:
            continue
        if v and v > 0:
            out.append((t, v))
    return out


def notes_of(frames, min_dur=0.10):
    """音高轨迹 → 音符序列（连续帧音高变化 <0.6 半音视为同一音）。"""
    out, cur = [], None
    for t, v in frames:
        if cur is None:
            cur = [t, t, [v]]
        elif abs(12 * math.log2(v / cur[2][-1])) < 0.6:
            cur[1] = t
            cur[2].append(v)
        else:
            out.append(cur)
            cur = [t, t, [v]]
    if cur:
        out.append(cur)
    return [(a, b, float(np.median(c))) for a, b, c in out if b - a >= min_dur]


def alt_rate(notes, duration_s):
    """极端交替次数 ÷ 分钟。"""
    n = 0
    for i in range(len(notes) - 1):
        a1, b1, h1 = notes[i]
        a2, b2, h2 = notes[i + 1]
        if abs(12 * math.log2(h2 / h1)) >= ALT_SEMI and (a2 - b1) <= ALT_GAP:
            n += 1
    return n, (n / (duration_s / 60.0) if duration_s > 0 else 0.0)


def brightness(mix_path, frames):
    """低音区/中音区 频谱质心比（原始混音口径）。"""
    if not os.path.exists(mix_path):
        return None
    y, sr = sf.read(mix_path)
    if y.ndim > 1:
        y = y.mean(1)
    if sr != SR:
        idx = (np.arange(int(len(y) * SR / sr)) * sr / SR).astype(int)
        y = y[np.clip(idx, 0, len(y) - 1)]
    y = np.asarray(y, dtype=np.float32)
    lo, mid = [], []
    for t, v in frames:
        band = "lo" if LO_BAND[0] <= v <= LO_BAND[1] else ("mid" if MID_BAND[0] <= v <= MID_BAND[1] else None)
        if not band:
            continue
        i = int(t * SR)
        if i + N > len(y) or i < 0:
            continue
        seg = y[i:i + N]
        if np.sqrt(np.mean(seg ** 2)) < 1e-5:
            continue
        S = np.abs(np.fft.rfft(seg * np.hanning(N)))
        fr = np.fft.rfftfreq(N, 1 / SR)
        e = S ** 2
        tot = e.sum() + 1e-12
        c = float((fr * e).sum() / tot)
        if c < v * 0.8:            # 合理性检查：质心不得低于基频
            continue
        (lo if band == "lo" else mid).append(c)
    if len(lo) < 3 or len(mid) < 3:
        return None
    lc, mc = float(st.median(lo)), float(st.median(mid))
    return {"lo_centroid": round(lc, 1), "mid_centroid": round(mc, 1),
            "ratio": round(lc / mc, 3), "lo_n": len(lo), "mid_n": len(mid)}


def main() -> int:
    songs = []
    for f in sorted(os.listdir(F0_ROOT)):
        d = os.path.join(F0_ROOT, f)
        if not os.path.isdir(d):
            continue
        for csvf in sorted(os.listdir(d)):
            if not csvf.endswith("_f0.csv"):
                continue
            title = csvf[:-len("_f0.csv")]
            frames = load_csv(os.path.join(d, csvf))
            if len(frames) < 50:
                continue
            dur = frames[-1][0] - frames[0][0]
            notes = notes_of(frames)
            cnt, rate = alt_rate(notes, dur)
            br = brightness(os.path.join(AUDIO_ROOT, f, title + ".mp3"), frames)
            songs.append({"title": title, "album": f, "duration_s": round(dur, 1),
                          "n_notes": len(notes), "alt_count": cnt,
                          "alt_rate_per_min": round(rate, 2),
                          "brightness": br})

    rates = [s["alt_rate_per_min"] for s in songs]
    ratios = [s["brightness"]["ratio"] for s in songs if s["brightness"]]
    payload = {
        "schema": "style-metrics/v1",
        "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
        "what": "演唱风格量化指标（由用户听感提出、经实测验证的两个可测行为）",
        "why": "把『打两份工/过山车』与『低的要高唱/低音亮度』从听感变成可复现、可挑战的数字",
        "discipline": [
            "① 极端交替：用户定义『高音后马上接低音、低音后马上升高』，**不是全曲跨度**",
            "② 低音亮度：在**原始混音**上测（对照试验证明比分离轨更保守，且排除 demucs artifact）",
            "③ 常态参照：男低音唱 95Hz 时能量压在基频，低音区质心应显著低于中音区（比值 ≪1）",
            "④ 极端交替指标**只能用于从百余首里挑候选**，最终判定须人耳（用户的 3 个否决样本指标也高）",
            "⑤ 质心测量含『质心不得低于基频』的合理性检查，防时间轴错位静默产出垃圾",
        ],
        "params": {"alt_semi": ALT_SEMI, "alt_gap_s": ALT_GAP,
                   "lo_band": LO_BAND, "mid_band": MID_BAND},
        "counts": {"songs": len(songs),
                   "with_brightness": len([s for s in songs if s["brightness"]])},
        "summary": {
            "alt_rate_median": round(st.median(rates), 2) if rates else None,
            "alt_rate_max": round(max(rates), 2) if rates else None,
            "brightness_ratio_median": round(st.median(ratios), 3) if ratios else None,
            "brightness_ratio_max": round(max(ratios), 3) if ratios else None,
        },
        "top_alt": sorted([s for s in songs if s["n_notes"] >= 30],
                          key=lambda x: -x["alt_rate_per_min"])[:12],
        "top_bright": sorted([s for s in songs if s["brightness"]],
                             key=lambda x: -x["brightness"]["ratio"])[:12],
        "songs": sorted(songs, key=lambda x: x["title"]),
    }
    io.open(OUT, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=1))
    print("[OK] %s" % OUT)
    print("     曲目 %d ｜ 有亮度数据 %d" % (len(songs), payload["counts"]["with_brightness"]))
    print("     极端交替 中位 %.2f / 最高 %.2f 次/分钟"
          % (payload["summary"]["alt_rate_median"], payload["summary"]["alt_rate_max"]))
    print("     低音亮度比 中位 %.3f / 最高 %.3f"
          % (payload["summary"]["brightness_ratio_median"],
             payload["summary"]["brightness_ratio_max"]))
    print()
    print("     「打两份工」前 5：")
    for s in payload["top_alt"][:5]:
        print("        %-18s %.2f 次/分钟（%d 次）" % (s["title"][:18], s["alt_rate_per_min"], s["alt_count"]))
    print("     「低音最亮」前 5：")
    for s in payload["top_bright"][:5]:
        print("        %-18s 比 %.3f（低 %.0fHz / 中 %.0fHz）"
              % (s["title"][:18], s["brightness"]["ratio"],
                 s["brightness"]["lo_centroid"], s["brightness"]["mid_centroid"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
