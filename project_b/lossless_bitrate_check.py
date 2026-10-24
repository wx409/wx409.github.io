#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无损 vs 320k：亮度指标（低/中频质心比、>1kHz 能量占比）的差异实测。

用途：站点「低音是亮的」结论建立在 320k 有损源上；本脚本用同一批曲目的
实体 CD 无损轨（专辑_分离）与 320k（分离_专辑）逐曲对比，量化 320k 带来的偏差，
从而给该结论一个可引用的误差界。

输出：data/lossless_bitrate_check.json（含逐曲两口径与差值统计）
用法：python -X utf8 project_b/lossless_bitrate_check.py [--write]
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ARCH = Path(r"E:\wx\论文素材_王晰作传")
LOSS_STEM = ARCH / "专辑_分离"
MP3_STEM = ARCH / "音域分析" / "分离_专辑"
OUT = ROOT / "data" / "lossless_bitrate_check.json"

# CD 轨号 → 曲名（已按时长与读数逐轨核对；09 轨为《想游泳的星》，仅实体版有）
MAP = {
    "6.X自选集": {"01": "偏偏", "02": "微醺23点08分", "03": "朝凤", "04": "是你",
                     "05": "猫模狗样", "06": "不需要结果", "07": "Crystal Store", "08": "小河"},
    "7.不说": {"01": "在路上", "02": "无尽的夜里", "03": "鹅毛信", "04": "勿扰",
                 "05": "住口", "06": "明白", "07": "雷美替胺", "08": "祝我们随遇而安"},
}


def find_stem(root: Path, album: str, key: str) -> Path | None:
    """在分离目录里按「专辑/键」定位 vocals.wav（键可为曲名或轨名前缀）。

    实体盘目录带序号前缀（6.X自选集），320k 侧目录不带（X自选集），两种都要试。
    """
    names = [album]
    if "." in album:
        names.append(album.split(".", 1)[1])
    for name in names:
        base = root / name
        if not base.exists():
            continue
        for d in base.iterdir():
            if d.is_dir() and (d.name.startswith(key) or key in d.name):
                for p in d.rglob("vocals.wav"):
                    return p
    return None


def brightness(path: Path) -> dict:
    import soundfile as sf
    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    x = x - x.mean()
    n, hop = 2048, 512
    if len(x) < n * 4:
        return {}
    win = np.hanning(n).astype(np.float32)
    frames = [(i, x[i:i + n] * win) for i in range(0, len(x) - n, hop)]
    rms = np.array([float(np.sqrt(np.mean(f[1] ** 2))) for f in frames])
    thr = np.median(rms) - 0.0
    keep = [f for f, r in zip(frames, rms) if r > thr * 0.25]
    if not keep:
        keep = frames
    spec = np.zeros(n // 2 + 1)
    for _, seg in keep:
        spec += np.abs(np.fft.rfft(seg)) ** 2
    spec /= max(1, len(keep))
    freqs = np.fft.rfftfreq(n, 1 / sr)
    tot = spec.sum()

    def centroid(lo, hi):
        m = (freqs >= lo) & (freqs < hi)
        e = spec[m]
        return float((freqs[m] * e).sum() / e.sum()) if e.sum() > 0 else 0.0

    return {
        "low_centroid_hz": round(centroid(50, 110), 2),
        "mid_centroid_hz": round(centroid(150, 350), 2),
        "ratio": round(centroid(50, 110) / max(1e-9, centroid(150, 350)), 3),
        "hi_share_1k": round(float(spec[freqs >= 1000].sum() / tot), 5) if tot else 0.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    rows, misses = [], []
    for album, tracks in MAP.items():
        for num, title in tracks.items():
            loss = find_stem(LOSS_STEM, album, num)
            mp3 = find_stem(MP3_STEM, album, title)
            if not loss or not mp3:
                misses.append({"album": album, "track": num, "song": title,
                               "loss": bool(loss), "mp3": bool(mp3)})
                continue
            a, b = brightness(loss), brightness(mp3)
            if not a or not b:
                continue
            rows.append({"album": album, "song": title, "lossless": a, "mp3_320k": b,
                         "d_ratio": round(a["ratio"] - b["ratio"], 4),
                         "d_hi_share_1k": round(a["hi_share_1k"] - b["hi_share_1k"], 5)})

    def med(key):
        v = [r[key] for r in rows if r.get(key) is not None]
        return round(st.median(v), 4) if v else None

    doc = {
        "schema": "lossless-bitrate-check/v1",
        "what": "同一曲目 实体CD无损 vs QQ音乐320k：人声轨亮度指标的差异（界定 320k 对「低音是亮的」结论的影响）",
        "matched": len(rows), "missed": misses,
        "median": {
            "lossless_ratio": med("lossless_ratio"),
            "mp3_ratio": med("mp3_ratio"),
            "d_ratio": med("d_ratio"),
            "d_hi_share_1k": med("d_hi_share_1k"),
            "ratio_abs_max": max((abs(r["d_ratio"]) for r in rows), default=None),
        },
        "rows": rows,
    }
    # 补两个口径的中位到 rows 外（便于直接引用）
    doc["median"]["lossless_ratio"] = round(st.median([r["lossless"]["ratio"] for r in rows]), 4) if rows else None
    doc["median"]["mp3_ratio"] = round(st.median([r["mp3_320k"]["ratio"] for r in rows]), 4) if rows else None

    print(json.dumps(doc["median"], ensure_ascii=False))
    for r in rows:
        print(f"  {r['album']}/{r['song']}: ratio 无损 {r['lossless']['ratio']:.3f} vs 320k "
              f"{r['mp3_320k']['ratio']:.3f} (Δ{r['d_ratio']:+.4f}) | >1k 无损 {r['lossless']['hi_share_1k']:.4f} "
              f"vs {r['mp3_320k']['hi_share_1k']:.4f} (Δ{r['d_hi_share_1k']:+.4f})")
    if misses:
        print("缺失:", json.dumps(misses, ensure_ascii=False))
    if args.write:
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        print("->", OUT)


if __name__ == "__main__":
    main()
