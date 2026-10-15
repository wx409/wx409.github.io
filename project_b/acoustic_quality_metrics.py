# -*- coding: utf-8 -*-
"""三指标质量档位判断：对**已分离人声轨**算 噪声底 / HNR / 动态范围，并按门槛给档位。

门槛（沿用本项目既定纪律）：升格需 **Δ噪声底 ≤ −3 dB** 或 **ΔHNR ≥ +3 dB**；
无依据则**维持触达/样本级**（不评优劣、不作能力依据）。

算法（自研、无新依赖）：
  · 分帧（50ms / hop 25ms）→ 谱 → **HNR**：自相关峰值/（1−峰值）在 dB 域的近似
    （HNR = 10·log10(r/(1−r))，r＝归一化自相关峰值）；取有声帧中位
  · **噪声底**：取能量最低 10% 帧的 RMS 中位（dBFS）
  · **动态范围**：有声帧 RMS 的 P95 − P5（dB）

用法：python -X utf8 project_b/acoustic_quality_metrics.py --wav <人声轨 wav> [--label 名称] [--json out]
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


def decode(path: Path, sr: int = 22050) -> tuple[np.ndarray, int]:
    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    raw = subprocess.run([ff, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0, sr


def framing(y: np.ndarray, frame: int, hop: int) -> np.ndarray:
    n = 1 + max(0, (len(y) - frame) // hop)
    idx = np.arange(frame)[None, :] + hop * np.arange(n)[:, None]
    return y[idx]


def hnr_db(frame: np.ndarray, sr: int) -> float:
    """自相关法 HNR（dB）。"""
    f = frame - frame.mean()
    e = float(np.dot(f, f))
    if e <= 1e-9:
        return float("nan")
    ac = np.correlate(f, f, mode="full")[len(f) - 1:]
    ac /= (ac[0] + 1e-12)
    lo, hi = int(sr / 500), int(sr / 60)          # 60–500 Hz 基频搜索
    if hi >= len(ac):
        hi = len(ac) - 1
    if hi <= lo:
        return float("nan")
    r = float(np.max(ac[lo:hi]))
    r = min(max(r, 1e-6), 1 - 1e-6)
    return 10 * np.log10(r / (1 - r))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    y, sr = decode(Path(a.wav))
    frame, hop = int(0.05 * sr), int(0.025 * sr)
    fr = framing(y, frame, hop)
    rms = np.sqrt((fr ** 2).mean(axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-12)
    thr = np.percentile(db, 60)                    # 有声判据：能量前 40%
    voiced = db >= thr
    hnrs = np.array([hnr_db(fr[i], sr) for i in range(len(fr)) if voiced[i]])
    hnrs = hnrs[np.isfinite(hnrs)]
    out = {
        "label": a.label or Path(a.wav).stem,
        "wav": str(a.wav), "duration_s": round(len(y) / sr, 1),
        "noise_floor_dbfs": round(float(np.median(np.sort(db)[:max(1, len(db) // 10)])), 2),
        "hnr_db_median": round(float(np.median(hnrs)), 2) if len(hnrs) else None,
        "dynamic_range_db_p95_p5": round(float(np.percentile(db[voiced], 95) -
                                              np.percentile(db[voiced], 5)), 2) if voiced.any() else None,
        "voiced_frames": int(voiced.sum()), "frame_ms": 50, "hop_ms": 25,
        "method": "自研：分帧 50ms/hop25ms → 自相关 HNR（60–500Hz）中位；噪声底＝最低 10% 帧 RMS 中位；"
                  "动态范围＝有声帧 P95−P5",
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
