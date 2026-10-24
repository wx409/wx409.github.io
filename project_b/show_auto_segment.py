# -*- coding: utf-8 -*-
"""show_auto_segment.py —— 整场音频「自动粗切」（档 1）

方法：0.5s 窗 RMS → 局部能量谷底（低于中位 −6dB）+ 静音检测（−45dB）→
      取 N−1 个最深且相互间隔 ≥60s 的切点 → 按歌单顺序对齐（顺序约束）；
      置信度 = 谷底深度（dB）与持续时长归一化（0–1）。
输出：data/show_segments_auto/<show>.json；每段 auto=true、boundary_error≈±5s、level=自动切分·待核。
预算：每晚 2 场（脚本单次只跑 1 场；排队由外层控制）。
用法：python -X utf8 project_b\\show_auto_segment.py --show <id> --audio <wav/m4a> --setlist <date>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
OUTDIR = D / "show_segments_auto"


def decode(p: Path, sr=16000) -> np.ndarray:
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    raw = subprocess.run([ff, "-v", "error", "-i", str(p), "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--setlist", required=True, help="日期，如 2026-10-10")
    a = ap.parse_args()
    y = decode(Path(a.audio))
    sr = 16000
    dur = len(y) / sr
    win, hop = int(0.5 * sr), int(0.25 * sr)
    rms = np.array([np.sqrt((y[i:i + win] ** 2).mean() + 1e-12)
                    for i in range(0, max(1, len(y) - win), hop)])
    db = 20 * np.log10(rms + 1e-12)
    med = float(np.median(db))
    t = np.arange(len(db)) * hop / sr
    # 谷底：低于中位−6dB，持续 ≥0.75s
    low = db < med - 6
    valleys, i = [], 0
    while i < len(low):
        if low[i]:
            j = i
            while j + 1 < len(low) and low[j + 1]:
                j += 1
            if (j - i + 1) * 0.25 >= 0.75:
                valleys.append({"t": float(t[(i + j) // 2]),
                                "depth": float(med - db[i:j + 1].min()),
                                "len": float((j - i + 1) * 0.25)})
            i = j + 1
        else:
            i += 1
    # 歌单
    sf = D / "show_setlists" / f"{a.setlist}_北京.json"
    songs = []
    if sf.exists():
        sd = json.loads(sf.read_text(encoding="utf-8"))
        songs = [s for seg in (sd.get("segment_list") or []) for s in (seg.get("songs") or [])]
    if not songs:
        sl = json.loads((D / "setlists.json").read_text(encoding="utf-8")).get("setlists") or {}
        v = sl.get(a.setlist) or {}
        songs = [x.get("title") if isinstance(x, dict) else x for x in (v.get("songs") or [])]
    songs = [s for s in songs if s]
    n = len(songs)
    need = max(0, n - 1)
    # 选切点：深度优先，间隔 ≥60s，避开首尾 30s
    valleys.sort(key=lambda v: -v["depth"])
    chosen, used = [], []
    for v in valleys:
        if len(chosen) >= need:
            break
        if v["t"] < 30 or v["t"] > dur - 30:
            continue
        if any(abs(v["t"] - u) < 60 for u in used):
            continue
        chosen.append(v)
        used.append(v["t"])
    chosen.sort(key=lambda v: v["t"])
    cuts = [0.0] + [v["t"] for v in chosen] + [dur]
    segs = []
    for k in range(n):
        if k + 1 < len(cuts):
            s0, s1 = cuts[k], cuts[k + 1]
        else:
            s0, s1 = cuts[-2], dur
        conf = 0.0
        for v in chosen:
            if abs(v["t"] - s1) < 1.0:
                conf = round(min(1.0, v["depth"] / 18.0 * 0.7 + min(v["len"], 3) / 3 * 0.3), 2)
        segs.append({"song": songs[k], "start": round(s0, 1), "end": round(s1, 1),
                     "dur": round(s1 - s0, 1), "confidence": conf,
                     "auto": True, "level": "自动切分·待核", "boundary_error_s": 5})
    doc = {"show": a.show, "audio": str(a.audio), "duration_s": round(dur, 1),
           "n_songs": n, "n_cuts_found": len(chosen), "median_db": round(med, 1),
           "method": "0.5s RMS 谷底（<中位−6dB，≥0.75s）+ 间隔≥60s + 歌单顺序对齐",
           "note": "全部 auto=true、boundary_error≈±5s、等级＝自动切分·待核，不进能力汇总",
           "segments": segs}
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / f"{a.show}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                                           encoding="utf-8")
    print(f"[ok] {a.show}｜时长 {dur:.0f}s｜歌单 {n} 首｜找到切点 {len(chosen)}/{need}｜"
          f"平均置信度 {np.mean([s['confidence'] for s in segs]):.2f}")
    for s in segs[:4]:
        print(f"   {s['song']} {s['start']}-{s['end']}s conf {s['confidence']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
