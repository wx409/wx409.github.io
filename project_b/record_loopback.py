#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""声卡环回录制：把「立体声混音」录成 WAV，供声学管线分析。

为什么用环回而不是解密：
  QQ 音乐的 .mflac/.mgg 是加密容器，解密属于绕过技术措施。环回录制不触碰加密，
  与实际音频输出等价，性质与翻录实体 CD 相同（个人研究、结果只发数据不发音频）。

用法：
  python -X utf8 project_b/record_loopback.py --seconds 330
  python -X utf8 project_b/record_loopback.py --device "立体声混音 (Realtek(R) Audio)" --seconds 330
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_DEV = "立体声混音 (Realtek(R) Audio)"
OUTDIR = Path(r"E:\wx\论文素材_王晰作传\专辑\环回录制")


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default=DEFAULT_DEV)
    ap.add_argument("--seconds", type=int, default=330)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else OUTDIR / time.strftime("loop_%Y%m%d_%H%M%S.wav")

    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "warning", "-y",
           "-f", "dshow", "-i", f"audio={args.device}",
           "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le",
           "-t", str(args.seconds), str(out)]
    print("[REC] 开始录制：", args.device, flush=True)
    print("[REC] 输出：", out, flush=True)
    print("[REC] 时长上限：", args.seconds, "秒 —— 现在开始播放", flush=True)
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    dur = time.time() - t0
    if r.returncode != 0:
        print("[ERR] ffmpeg 退出码", r.returncode)
        print((r.stderr or "")[-1200:])
        sys.exit(r.returncode)
    size = out.stat().st_size if out.exists() else 0
    print(f"[REC] 完成：{out.name}｜{size/1e6:.1f} MB｜耗时 {dur:.1f}s", flush=True)


if __name__ == "__main__":
    main()
