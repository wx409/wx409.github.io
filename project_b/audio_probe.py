#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""素材体检：任意音频/视频文件 → 能否用于低频（B1/C2）判定的判据。

为什么需要它：
  同一段演出，采集路径不同，低频可能差了 50 dB（直接录 vs 系统音效污染 vs 手机现场录）。
  拿到素材先测 40–80Hz 能量占比，再决定能拿它做什么结论，避免把“缺低频的文件”当成“他没唱低”。

判据（基于已实测的三个锚点：母带环回 21.6% / 320k 23.6% / 被音效污染 0.00%）：
  ≥15%     低频完整      → 可做 B1/C2 判定（仍须过谐波列）
  5%–15%   低频被衰减    → 只做中高音、稳定性、长音
  <5%      低频被砍      → 只做中高音，禁止用于低音结论

用法：
  python -X utf8 project_b/audio_probe.py "D:\\path\\live.mp4"
  python -X utf8 project_b/audio_probe.py "a.wav" --json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

AUDIO_EXT = {'.wav', '.flac', '.mp3', '.m4a', '.aac', '.ogg', '.opus', '.wma', '.aiff'}
BANDS = {'40-80': (40, 80), '80-200': (80, 200), '200-500': (200, 500),
         '500-1k': (500, 1000), '1-4k': (1000, 4000)}


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def to_wav(src: Path) -> tuple[Path, bool]:
    """非 wav 一律先转 48k 立体声 wav（视频自动取音轨）。返回 (路径, 是否临时文件)。"""
    if src.suffix.lower() == '.wav':
        return src, False
    tmp = Path(tempfile.gettempdir()) / (src.stem[:40].replace(' ', '_') + '_probe.wav')
    r = subprocess.run([ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-y',
                        '-i', str(src), '-vn', '-ac', '2', '-ar', '48000',
                        '-c:a', 'pcm_s16le', str(tmp)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError((r.stderr or '')[-500:])
    return tmp, True


def probe(path: Path) -> dict:
    import soundfile as sf
    x, sr = sf.read(str(path), dtype='float32', always_2d=True)
    m = x.mean(axis=1)
    dur = len(m) / sr
    peak = float(np.max(np.abs(m))) if len(m) else 0.0
    rms = float(np.sqrt(np.mean(m ** 2))) if len(m) else 0.0

    n, hop = 4096, 2048
    win = np.hanning(n)
    spec = np.zeros(n // 2 + 1)
    cnt = 0
    for i in range(0, max(0, len(m) - n), hop):
        seg = m[i:i+n] * win
        if np.sqrt(np.mean(seg ** 2)) < 0.002:
            continue
        spec += np.abs(np.fft.rfft(seg)) ** 2
        cnt += 1
    spec /= max(1, cnt)
    f = np.fft.rfftfreq(n, 1 / sr)
    tot = float(spec.sum()) or 1.0
    shares = {k: round(float(spec[(f >= a) & (f < b)].sum() / tot) * 100, 2) for k, (a, b) in BANDS.items()}

    # 1f0 候选：低频段里最强的三个峰
    lo = (f > 45) & (f < 120)
    idx = np.argsort(spec[lo])[-3:][::-1]
    peaks = [round(float(f[lo][j]), 1) for j in idx]

    low = shares['40-80']
    if low >= 15:
        verdict = 'full'          # 低频完整
        advice = '可用于 B1/C2 判定（仍须过原始混音谐波列）'
    elif low >= 5:
        verdict = 'attenuated'    # 低频衰减
        advice = '低频被衰减：只做中高音 / 稳定性 / 长音'
    else:
        verdict = 'no-low'        # 低频被砍
        advice = '低频已被砍掉：禁止用于低音结论，只做中高音'

    return {
        'file': str(path), 'sr': sr, 'duration_s': round(dur, 1),
        'peak_dbfs': round(20 * np.log10(max(peak, 1e-9)), 1),
        'rms_dbfs': round(20 * np.log10(max(rms, 1e-9)), 1),
        'band_share_pct': shares,
        'low_band_peaks_hz': peaks,
        'frames_used': cnt,
        'verdict': verdict, 'advice': advice,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    src = Path(args.path)
    if not src.exists():
        print('[ERR] 文件不存在:', src)
        sys.exit(1)
    tmp, is_tmp = to_wav(src)
    try:
        info = probe(tmp)
    finally:
        if is_tmp and tmp.exists():
            tmp.unlink(missing_ok=True)

    if args.json:
        print(json.dumps(info, ensure_ascii=False, indent=1))
        return
    print(f"文件: {src.name}")
    print(f"参数: {info['sr']} Hz｜{info['duration_s']} s｜峰值 {info['peak_dbfs']} dBFS｜RMS {info['rms_dbfs']} dBFS")
    print("频段占比: " + '  '.join(f'{k}:{v}%' for k, v in info['band_share_pct'].items()))
    print("低频段最强峰: " + ', '.join(f'{h} Hz' for h in info['low_band_peaks_hz']))
    tag = {'full': '✅', 'attenuated': '⚠️', 'no-low': '❌'}[info['verdict']]
    print(f"{tag} 判定: {info['advice']}")


if __name__ == '__main__':
    main()
