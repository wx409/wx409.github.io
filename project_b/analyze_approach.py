#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""② 极值音的「到达方式」：他是怎么唱到最低音的？

数据：E:\\wx\\论文素材_王晰作传\\音域分析\\分析结果\\*_f0.csv（16 个逐帧文件，含《多听有益》5 个版本）
做法
  · 取每个文件里持续 ≥0.15s 的最低音段（稳定音口径）
  · 看它前 2 秒的轨迹，判定进入方式：
      jump   前 0.4s 内下跳 ≥3 半音
      slide  前 0.4–2s 内连续下行 ≥3 半音（滑音/级进）
      direct 前 2s 一直在最低音附近（±2 半音）
  · 记持续时长、进入耗时、颤音是否介入（±20 音分、周期≈200ms 的振荡）

输出：data/approach_analysis.json
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(r"E:\wx\论文素材_王晰作传\音域分析\分析结果")
OUT = ROOT / "data" / "approach_analysis.json"


def hz_to_midi(h):
    import math
    return 69 + 12 * math.log2(h / 440.0) if h > 0 else None


def load(path):
    t, f = [], []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                ts = float(row["time_s"]); hz = float(row["f0_hz"])
                v = int(float(row.get("voiced_pyin") or 0))
            except (KeyError, ValueError):
                continue
            if v and hz > 0:
                t.append(ts); f.append(hz)
    return t, f


def segments(t, f, min_dur=0.15):
    """把相邻帧合成音符段（容差 1.5 半音），返回 [(t0,t1,midi_med,hz_med)]。"""
    segs, i, n = [], 0, len(t)
    while i < n:
        j = i
        base = hz_to_midi(f[i])
        while j + 1 < n and abs(hz_to_midi(f[j + 1]) - base) <= 1.5:
            j += 1; base = statistics.median([hz_to_midi(x) for x in f[i:j + 1]])
        if t[j] - t[i] >= min_dur:
            segs.append((t[i], t[j], statistics.median([hz_to_midi(x) for x in f[i:j + 1]]),
                         statistics.median(f[i:j + 1])))
        i = j + 1
    return segs


def analyse(path):
    t, f = load(path)
    if len(t) < 100:
        return None
    segs = segments(t, f)
    if not segs:
        return None
    low = min(segs, key=lambda s: s[2])
    t0 = low[0]
    # 前 2 秒轨迹
    pre = [(tt, hz_to_midi(ff)) for tt, ff in zip(t, f) if t0 - 2.0 <= tt < t0]
    kind, drop = "无前段", 0.0
    if pre:
        m_last = pre[-1][1]
        m_first = pre[0][1]
        drop = m_first - m_last                      # 正数=下行
        fast = [p for p in pre if p[0] >= t0 - 0.4]
        if abs(m_last - low[2]) <= 2:
            kind = "direct"
        elif fast and (fast[0][1] - m_last) >= 3:
            kind = "jump"
        elif drop >= 3:
            kind = "slide"
        else:
            kind = "direct"
    # 颤音：段内音高围绕中位的波动
    in_seg = [hz_to_midi(x) for tt, x in zip(t, f) if low[0] <= tt <= low[1]]
    vib = (max(in_seg) - min(in_seg)) * 100 if len(in_seg) > 3 else 0.0
    return {
        "file": path.name,
        "low_midi": round(low[2], 2),
        "low_hz": round(low[3], 1),
        "sustain_s": round(low[1] - low[0], 2),
        "approach": kind,
        "approach_drop_semitones": round(drop, 2),
        "in_note_range_cents": round(vib, 0),
        "pre_2s_semitones": round(drop, 2),
    }


def main() -> int:
    files = sorted(SRC.glob("*_f0.csv"))
    rows = []
    for p in files:
        try:
            r = analyse(p)
        except Exception as e:
            r = {"file": p.name, "error": str(e)[:80]}
        if r:
            rows.append(r)
    ok = [r for r in rows if "approach" in r]
    from collections import Counter
    c = Counter(r["approach"] for r in ok)
    print("逐帧文件 %d｜可用 %d｜进入方式分布：%s" % (len(files), len(ok), dict(c)))
    for r in sorted(ok, key=lambda x: x["low_hz"])[:8]:
        print("  %-26s 最低 %6.1fHz(%5.2f) 持续 %4.2fs 进入=%-6s 下沉 %4.1f 半音 段内摆幅 %4.0f 音分"
              % (r["file"][:26], r["low_hz"], r["low_midi"], r["sustain_s"],
                 r["approach"], r["approach_drop_semitones"], r["in_note_range_cents"]))
    OUT.write_text(json.dumps({
        "schema": "approach/v1",
        "note": "样本仅 16 个逐帧文件（多听有益 5 版 / 向着太阳 2 版 等），作示范不作统计结论",
        "n_files": len(ok), "distribution": dict(c), "rows": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
