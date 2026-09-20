# -*- coding: utf-8 -*-
"""整场纵向分析（把只在备忘里的「拱形结构 / 音区不漂移」推广到巡演各场）。

输入：已落盘的逐帧 F0（`音域分析\\场次音频\\*_分析\\<段落>\\<段落>_f0.csv`），不重跑分离。
输出：data/archive_show_arc.json + 控制台简表。

每场：按段落顺序拼时间轴 → 全整除 5 个等长 bin → 每 bin 的音区中位与低/中/高占比。
指标：drift = 末 bin − 首 bin（半音）；arch = 高区占比最大的 bin（拱形位置）。

用法: python -X utf8 project_b\\整场纵向分析.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频")
OUT = Path(__file__).resolve().parent.parent / "data" / "archive_show_arc.json"
SKIP = ("赵鹏对照", "杨洪基", "俄罗斯决赛_电视版", "相亲相爱一家人", "过山车两首", "风格两首", "滚滚长江")
# 多场次拼装/跨年聚合，单场弧线无意义；单曲或片段不足以构成一场
AGG = ("十年现场语料", "分P逐曲", "六巡含歌", "一巡现场", "新源现场", "wav_分析")
SHOW_MIN, SHOW_MAX = 30.0, 250.0
LOW, HIGH = 48, 60  # C3 / C4
BINS = 5


def seg_key(p: Path):
    m = re.match(r"(\d+)", p.stem)
    return (0, int(m.group(1)), p.stem) if m else (1, 0, p.stem)


def show_arc(csvs: list[Path]) -> dict:
    frames = []
    off = 0.0
    for c in csvs:
        d = pd.read_csv(c, usecols=["time_s", "midi"])
        d = d[d["midi"].notna()]
        if d.empty:
            continue
        frames.append(pd.DataFrame({"t": d["time_s"].to_numpy() + off, "midi": d["midi"].to_numpy()}))
        off += float(d["time_s"].max()) + 0.023
    if not frames:
        return {}
    df = pd.concat(frames, ignore_index=True)
    total = float(df["t"].max())
    idx = np.clip((df["t"] / max(total, 1e-9) * BINS).astype(int), 0, BINS - 1)
    bins = []
    for b in range(BINS):
        m = df["midi"].to_numpy()[idx == b]
        if len(m) < 50:
            bins.append(None)
            continue
        bins.append({
            "bin": b + 1,
            "n": int(len(m)),
            "midi_median": round(float(np.median(m)), 2),
            "low_share": round(float((m < LOW).mean()), 4),
            "high_share": round(float((m >= HIGH).mean()), 4),
        })
    filled = [b for b in bins if b]
    if len(filled) < 3:
        return {}
    drift = round(filled[-1]["midi_median"] - filled[0]["midi_median"], 2)
    arch = max(filled, key=lambda b: b["high_share"])["bin"]
    return {
        "segments": len(csvs),
        "minutes": round(total / 60, 1),
        "notes": int(len(df)),
        "bins": bins,
        "drift_semitones": drift,
        "high_share_peak_bin": arch,
        "low_share_range": round(max(b["low_share"] for b in filled) - min(b["low_share"] for b in filled), 4),
    }


def main() -> int:
    rows = []
    for adir in sorted(SRC.glob("*_分析")):
        batch = adir.name[:-3]
        if any(s in batch for s in SKIP):
            continue
        csvs = sorted([p for p in adir.rglob("*_f0.csv")], key=seg_key)
        if not csvs:
            continue
        arc = show_arc(csvs)
        if not arc or batch in AGG or not (SHOW_MIN <= arc["minutes"] <= SHOW_MAX):
            continue
        rows.append({"show": batch, **arc})

    rows.sort(key=lambda r: -r["minutes"])
    drifts = [abs(r["drift_semitones"]) for r in rows]
    summary = {
        "shows": len(rows),
        "shows_within_1_semitone": int(sum(d <= 1 for d in drifts)),
        "drift_median": round(float(np.median(drifts)), 2) if drifts else None,
        "high_peak_in_last_two_bins": int(sum(r["high_share_peak_bin"] >= BINS - 1 for r in rows)),
    }
    OUT.write_text(
        json.dumps({"generated_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "bins": BINS,
                    "region": {"low_lt": LOW, "high_ge": HIGH}, "summary": summary, "shows": rows},
                   ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"{'场次':<26}{'分钟':>6}{'drift':>7}{'高区峰bin':>9}{'低区摆动':>9}")
    for r in rows:
        print(f"{r['show']:<26}{r['minutes']:>6}{r['drift_semitones']:>7}{r['high_share_peak_bin']:>9}{r['low_share_range']:>9}")
    print("汇总:", json.dumps(summary, ensure_ascii=False))
    print("→", OUT)
    assert summary["shows"] == len(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
