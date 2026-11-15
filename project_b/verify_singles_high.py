#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单曲高音复核：对 49 首独唱的最高音候选做「原始混音谐波列」判定。

判据
  · 真基频：2f0 能量 ≥ 0.20×f0，4f0 ≥ 0.06，且 0.5f0 < 1.2×f0
  · 八度错误：0.5f0 ≥ 1.2×f0（真实基频低一个八度）
  · 谐波错误：2f0 < 0.20 且 4f0 < 0.06（只有奇次谐波）
输出：data/singles_high_verified.json + 控制台摘要
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import imageio_ffmpeg

FF = imageio_ffmpeg.get_ffmpeg_exe()
BASE = Path(r"E:\wx\论文素材_王晰作传\音域分析")
ANA = Path(r"E:\wx\论文素材_王晰作传\单曲音频_汇总.json")
CAT = Path(r"D:\wx409.github.io\data\singles_category.json")
OUT = Path(r"D:\wx409.github.io\data\singles_high_verified.json")


def audio_index():
    idx = {}
    for p in BASE.rglob("*.mp3"):
        idx.setdefault(p.stem.strip(), p)
    return idx


def spectrum(path, t0, dur=0.25, sr=22050):
    raw = subprocess.run([FF, "-v", "error", "-ss", str(max(0.0, t0 - dur / 2)), "-t", str(dur),
                          "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    if len(x) < 2048:
        return None, None
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    return np.fft.rfftfreq(len(x), 1 / sr), spec


def band(f, s, freq, w=6.0):
    m = (f >= freq - w) & (f <= freq + w)
    return float(s[m].max()) if m.any() else 0.0


def judge(path, t0, f0):
    f, s = spectrum(path, t0)
    if f is None:
        return None
    ref = max(band(f, s, f0), 1e-9)
    r = {k: band(f, s, f0 * k) / ref for k in (0.5, 1, 2, 3, 4)}
    if r[0.5] >= 1.2:
        return "octave_error", r
    if r[2] >= 0.20 and r[4] >= 0.06:
        return "ok", r
    return "harmonic_error", r


def main() -> int:
    ana = json.loads(ANA.read_text(encoding="utf-8"))["songs"]
    cat = {x["title"]: x for x in json.loads(CAT.read_text(encoding="utf-8"))["songs"]}
    idx = audio_index()
    rows, skipped = [], []
    for a in ana:
        t = a.get("title", "")
        c = cat.get(t)
        if c and (c.get("category") == "合唱" or "/" in str(c.get("singers") or "")):
            skipped.append({"title": t, "reason": "合唱（音高归属未定）"})
            continue
        if t == "无荒":
            skipped.append({"title": t, "reason": "按用户要求不测（分不清声部）"})
            continue
        p = idx.get(t.strip())
        if not p:
            skipped.append({"title": t, "reason": "缺音频"})
            continue
        cands = (a.get("highest_notes") or [])[:3]
        verdicts, best_ok = [], None
        for h in cands:
            v = judge(p, float(h.get("t_start") or 0), float(h.get("hz") or 0))
            if not v:
                continue
            st, r = v
            verdicts.append({"note": h.get("note"), "hz": h.get("hz"), "t": h.get("t_start"),
                             "status": st, "ratios": {str(k): round(x, 2) for k, x in r.items()}})
            if st == "ok" and (best_ok is None or h["hz"] > best_ok["hz"]):
                best_ok = {"note": h.get("note"), "hz": h.get("hz"), "t": h.get("t_start")}
        rows.append({
            "title": t,
            "low_stable": a.get("low_stable"),
            "high_candidates": verdicts,
            "verified_high": best_ok,
            "span_reported": a.get("span_octaves"),
            "span_verified": (round(np.log2(best_ok["hz"] / a["low_stable"]["hz"]), 2)
                              if best_ok else None),
        })

    OUT.write_text(json.dumps({"schema": "singles-high-verified/v1",
                               "note": "高音只保留通过原始混音谐波列者；无荒按用户要求不测",
                               "n": len(rows), "items": rows, "skipped": skipped},
                              ensure_ascii=False, indent=1), encoding="utf-8")

    ok_rows = [r for r in rows if r["verified_high"]]
    ok_rows.sort(key=lambda r: -(r["span_verified"] or 0))
    print(f"复核 {len(rows)} 首｜高音通过 {len(ok_rows)} 首｜跳过 {len(skipped)} 首")
    print("\n通过高音复核的 Top 8：")
    for r in ok_rows[:8]:
        print("  %-12s 低 %-4s %5.1fHz  高 %-4s %6.1fHz  跨度 %.2f（原报 %.2f）" % (
            r["title"][:12], r["low_stable"]["note"], r["low_stable"]["hz"],
            r["verified_high"]["note"], r["verified_high"]["hz"],
            r["span_verified"], r["span_reported"]))
    bad = [r for r in rows if not r["verified_high"]]
    print(f"\n高音全部未通过：{len(bad)} 首（前 6）")
    for r in bad[:6]:
        st = ",".join(v["status"] for v in r["high_candidates"][:2]) or "无候选"
        print("  %-12s → %s" % (r["title"][:12], st))
    print("\n→", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
