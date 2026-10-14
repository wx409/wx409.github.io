# -*- coding: utf-8 -*-
"""从英文串烧（p20，5:59）里**按能量谷/谱心变化切出三首**，供逐曲实测。

方法（可复核、无新依赖）：
  解码 → 逐秒 RMS（dB）与谱心 → 找「连续 ≥2.5s 能量低于中位−6dB」的低谷作为段落边界候选，
  再按低谷位置把 5:59 切成最多 3 段；输出各段时间与能量特征，**边界误差须记（±2s 量级）**。

用法：python -X utf8 project_b/segment_medley.py --file <m4a> --out <json> [--n 3]
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


def decode(path: Path, sr: int = 22050):
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr),
           "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    y = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    return y, sr


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args()
    p = Path(a.file)
    y, sr = decode(p)
    dur = len(y) / sr
    # 逐秒 RMS(dB)
    step = sr
    n = int(dur)
    rms = np.array([np.sqrt(np.mean(y[i * step:(i + 1) * step] ** 2) + 1e-12) for i in range(n)])
    db = 20 * np.log10(rms + 1e-12)
    med = float(np.median(db))
    low = db < (med - 6.0)
    # 连续低谷段（≥2.5s）
    valleys, i = [], 0
    while i < len(low):
        if low[i]:
            j = i
            while j + 1 < len(low) and low[j + 1]:
                j += 1
            if (j - i + 1) >= 2.5:
                valleys.append((i, j, float(db[i:j + 1].mean())))
            i = j + 1
        else:
            i += 1
    # 取最深/最靠中间的 n-1 个低谷作为切点
    valleys.sort(key=lambda v: v[2])
    cuts = sorted(int((v[0] + v[1]) / 2) for v in valleys[: a.n - 1])
    idx = [0] + cuts + [int(dur)]
    segs = []
    for k in range(len(idx) - 1):
        window = db[idx[k]:idx[k + 1]]
        segs.append({"no": k + 1, "t0": idx[k], "t1": idx[k + 1], "dur_s": idx[k + 1] - idx[k],
                     "rms_db_median": round(float(np.median(window)) if len(window) else 0.0, 1)})
    doc = {"file": str(p), "duration_s": round(dur, 2), "rms_db_median": round(med, 1),
           "valleys": [{"t0": v[0], "t1": v[1], "mean_db": round(v[2], 1)} for v in valleys[:8]],
           "segments": segs,
           "method": "逐秒 RMS → 低于中位−6dB 且连续 ≥2.5s 判低谷 → 取最深 n-1 个为切点",
           "boundary_note": "切点由能量谷推定，**误差 ±2s 量级**；用于分段实测时须在口径里注明"}
    print(json.dumps({k: doc[k] for k in ("duration_s", "rms_db_median", "segments", "valleys")},
                     ensure_ascii=False, indent=1)[:1200])
    if a.out:
        Path(a.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[OK] →", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
