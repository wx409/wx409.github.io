#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""经 VB-Cable 录制：切默认输出 → 从 CABLE Output 录 → 恢复默认输出。

为什么不用「立体声混音」：那台机器的 Realtek 端点挂了 Nahimic 的 APO，60Hz 被高通掉 54dB；
VB-Cable 是独立虚拟声卡，链路上没有 APO，实测 60Hz/1200Hz 幅度比 -0.1dB。

用法：
  python -X utf8 project_b/record_cable.py --seconds 300
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PS1 = ROOT / "tools" / "set_default_audio.ps1"
OUTDIR = Path(r"E:\wx\论文素材_王晰作传\专辑\环回录制")
CABLE_PLAY = "CABLE Input"
SPEAKER = "扬声器"
CAPTURE = "CABLE Output (VB-Audio Virtual Cable)"


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def set_default(name: str) -> bool:
    r = subprocess.run(["pwsh", "-NoProfile", "-File", str(PS1), "-Set", name],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(("[默认输出] " + (r.stdout or "").strip()), flush=True)
    return r.returncode == 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=300)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = Path(args.out) if args.out else OUTDIR / time.strftime("cable_%Y%m%d_%H%M%S.wav")

    if not set_default(CABLE_PLAY):
        print("[ERR] 切换默认输出失败", flush=True)
        sys.exit(1)
    print("[REC] 默认输出已切到 CABLE Input（此时扬声器无声，属正常）", flush=True)
    print("[REC] 开始录制：", CAPTURE, "->", out, flush=True)

    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "warning", "-y",
           "-f", "dshow", "-i", f"audio={CAPTURE}",
           "-ac", "2", "-ar", "48000", "-c:a", "pcm_s24le",
           "-t", str(args.seconds), str(out)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print("[ERR] ffmpeg:", (r.stderr or "")[-800:], flush=True)
    finally:
        set_default(SPEAKER)
        print("[默认输出] 已恢复为扬声器", flush=True)

    size = out.stat().st_size if out.exists() else 0
    print(f"[REC] 完成：{out.name}｜{size/1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
