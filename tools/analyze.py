#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/analyze.py —— 自动化分析管线第 2 步：音频 → 标准化 JSON。

流程与本站既有实测**完全同一管线**（这样才能与主口径并表）：
  音频 → demucs htdemucs 人声分离（进程内 API）→ 自研 numpy YIN 逐帧 F0
       → 音符切分 → 稳健过滤 → 短时 RMS 动态包络 → 标准化 JSON

本机约束（血泪教训，勿改）：
  · numba/llvmlite.dll 与 sphn 的 .pyd 被「应用程序控制策略」阻止 → 不走 librosa.pyin、不走 `python -m demucs`；
    解法：注入 sphn 桩 + `demucs.api.Separator`（见 音域分析/批量专辑音域.py）。
  · HF_HUB_OFFLINE=1 用本地缓存模型，断网可跑。

用法：
  python tools/analyze.py <audio.wav> [--out tmp/analysis] [--json <路径>]
  python tools/analyze.py --queue            # 分析 tmp/ 中队列条目已下载的音频
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 复用生产脚本的测量内核（单一事实源：不在此重写 YIN/切分算法）
METRICS_DIR = r"E:\wx\论文素材_王晰作传\音域分析"

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

SR, HOP, FRAME = 22050, 512, 2048
FMIN, FMAX = 55.0, 1100.0
MIN_NOTE_MS, NOTE_TOL = 80, 0.6


def _install_sphn_stub():
    if "sphn" not in sys.modules:
        import types
        m = types.ModuleType("sphn")

        def _fail(*a, **k):
            raise RuntimeError("sphn stub（本机 .pyd 被策略阻止）")

        m.read = _fail
        m.write = _fail
        sys.modules["sphn"] = m


def _ascii_copy(src: str, workdir: str) -> str:
    """CJK 路径消毒：demucs/ffmpeg 子进程对非 ASCII 路径会失败。"""
    try:
        src.encode("ascii")
        return src
    except UnicodeEncodeError:
        pass
    import imageio_ffmpeg
    os.makedirs(workdir, exist_ok=True)
    out = os.path.join(workdir, "input_ascii.wav")
    if not os.path.exists(out):
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        import subprocess
        subprocess.run([ff, "-y", "-i", src, "-ac", "2", "-ar", "44100",
                        "-c:a", "pcm_s16le", out], check=True, capture_output=True)
    return out


def separate(src: str, stems_dir: str, gpu: bool = True) -> str:
    import numpy as np
    src = _ascii_copy(src, stems_dir)
    out = os.path.join(stems_dir, "htdemucs",
                       os.path.splitext(os.path.basename(src))[0], "vocals.wav")
    if os.path.exists(out):
        return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    import soundfile as sf
    import torch
    _install_sphn_stub()
    from demucs.api import Separator
    y, sr = sf.read(src, dtype="float32", always_2d=True)
    if y.shape[1] == 1:                      # demucs htdemucs 需要双声道输入
        y = np.repeat(y, 2, axis=1)
    if sr != 44100:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(int(sr), 44100)
        y = resample_poly(y, 44100 // g, int(sr) // g, axis=0).astype("float32")
        sr = 44100
    device = "cuda" if (gpu and torch.cuda.is_available()) else "cpu"
    sep = Separator(model="htdemucs", device=device, progress=False)
    _, parts = sep.separate_tensor(torch.from_numpy(y.T.copy()), sr)
    vocals = parts["vocals"].cpu().numpy().T
    sf.write(out, vocals, sr, subtype="PCM_16")
    del sep
    if device == "cuda":
        torch.cuda.empty_cache()
    return out


def analyze(vocals_path: str) -> dict:
    sys.path.insert(0, METRICS_DIR)
    import numpy as np
    from vocal_metrics import load_audio, segment_notes, spectral_features, yin_f0, midi_to_name

    y, sr = load_audio(vocals_path, SR)
    if y.size < sr * 3:
        raise SystemExit("音频过短（<3s），不具测量意义")
    pitch = yin_f0(y, sr, FMIN, FMAX, FRAME, HOP)
    f0, voiced = pitch["f0"], pitch["voiced"]
    sf = spectral_features(y, sr, FRAME, HOP)
    n = len(f0)
    for k in ("rms_db", "hnr_db", "centroid"):
        v = sf[k]
        sf[k] = v[:n] if len(v) >= n else np.pad(v, (0, n - len(v)), constant_values=np.nan)

    notes = segment_notes(f0, voiced, HOP, sr, MIN_NOTE_MS, NOTE_TOL)
    if not notes:
        raise SystemExit("未切出有效音符")
    for nt in notes:
        s, e = nt["start_idx"], nt["end_idx"] + 1
        nt["rms_db"] = round(float(np.nanmedian(sf["rms_db"][s:e])), 1)
        nt["hnr_db"] = round(float(np.nanmedian(sf["hnr_db"][s:e])), 1)
        nt["centroid"] = round(float(np.nanmedian(sf["centroid"][s:e])), 0)

    midis = np.array([x["midi"] for x in notes])
    durs = np.array([x["dur"] for x in notes])
    rms_notes = np.array([x["rms_db"] for x in notes])
    hnr_notes = np.array([x["hnr_db"] for x in notes])

    # 稳健过滤（与主口径一致：时长 ≥0.15s、HNR ≥5dB、强度 ≥中位−25dB）
    rms_floor = float(np.median(rms_notes)) - 25.0
    keep = (durs >= 0.15) & (hnr_notes >= 5.0) & (rms_notes >= rms_floor)
    kept = [n_ for n_, k in zip(notes, keep) if k]
    if not kept:
        raise SystemExit("稳健过滤后无有效音符")

    kept.sort(key=lambda x: x["midi"])
    lo = kept[0]
    hi = kept[-1]
    rms_kept = np.array([x["rms_db"] for x in kept])
    # 音级聚合（低音区动态范围用），只统计已过门槛的音级
    levels = {}
    for x in kept:
        levels.setdefault(x["note"], []).append(x["rms_db"])

    def pct(xs, q):
        xs = sorted(xs)
        if not xs:
            return None
        if len(xs) == 1:
            return round(xs[0], 1)
        k = (len(xs) - 1) * q
        a, b = int(k), min(int(k) + 1, len(xs) - 1)
        return round(xs[a] + (xs[b] - xs[a]) * (k - a), 1)

    low_levels = []
    for note, vals in levels.items():
        if len(vals) < 1:
            continue
        pp, mf = pct(vals, 0.05), pct(vals, 0.95)
        low_levels.append({"note": note, "n": len(vals), "pp_dbfs": pp, "mf_dbfs": mf,
                           "range_db": (round(mf - pp, 1) if pp is not None and mf is not None else None),
                           "status": "measured" if len(vals) >= 3 else "insufficient_sample"})
    low_levels.sort(key=lambda x: x["n"])

    return {
        "schema": "analysis_result v1",
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pipeline": ("demucs htdemucs 人声分离（进程内 API + sphn 桩）→ 自研 numpy YIN 逐帧 F0"
                     "（fmin 55 / fmax 1100 / frame 2048 / hop 512 / sr 22050）→ 音符切分"
                     "（稳定段 ≥80ms、抖动 <0.6 半音）→ 稳健过滤（时长 ≥0.15s、HNR ≥5dB、强度 ≥中位−25dB）"),
        "duration_s": round(len(y) / sr, 2),
        "note_count": len(notes),
        "kept_count": len(kept),
        "lowest_stable": {"note": lo["note"], "hz": round(440.0 * 2 ** ((lo["midi"] - 69) / 12), 1),
                          "dur_s": round(lo["dur"], 3), "hnr_db": lo["hnr_db"],
                          "t_s": round(lo["t_start"], 2)},
        "highest_stable": {"note": hi["note"], "hz": round(440.0 * 2 ** ((hi["midi"] - 69) / 12), 1),
                           "dur_s": round(hi["dur"], 3), "hnr_db": hi["hnr_db"],
                           "t_s": round(hi["t_start"], 2)},
        "span_octaves": round((hi["midi"] - lo["midi"]) / 12, 2),
        "rms_db": {"p5": pct(list(rms_kept), 0.05), "median": round(float(np.median(rms_kept)), 1),
                   "p95": pct(list(rms_kept), 0.95)},
        "low_levels": low_levels,
        "caliber_note": ("稳定音口径；触达音与低音带读数在本管线的其他层单独处理，"
                         "未复核读数不得进入能力结论。"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="音频 → 标准化分析 JSON（同站内主口径管线）")
    ap.add_argument("audio", nargs="?")
    ap.add_argument("--out", default=os.path.join(ROOT, "tmp", "analysis"))
    ap.add_argument("--json", default=None, help="结果 JSON 输出路径")
    args = ap.parse_args()
    if not args.audio:
        ap.error("需要 <audio.wav>")
    stems = os.path.join(args.out, "stems")
    v = separate(args.audio, stems)
    res = analyze(v)
    res["source_audio"] = os.path.basename(args.audio)
    out = args.json or os.path.join(args.out, os.path.splitext(os.path.basename(args.audio))[0] + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))
    print("[OK] 最低稳定音 %s %.1fHz（%.3fs, HNR %.1f）｜跨度 %.2f 八度"
          % (res["lowest_stable"]["note"], res["lowest_stable"]["hz"],
             res["lowest_stable"]["dur_s"], res["lowest_stable"]["hnr_db"], res["span_octaves"]))
    print("[写]", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
