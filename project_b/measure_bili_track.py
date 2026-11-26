#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""measure_bili_track.py —— 对单条 B站官方空间视频做声学测量（可被每日 ingest 调用）"""
from __future__ import annotations

import argparse
import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
VID = Path(r"E:\wx\论文素材_王晰作传\B站\官方空间")
WORK = Path(r"E:\wx\论文素材_王晰作传\音域分析\B站每日")
OUT = Path(r"E:\wx\私有工具\bili_measure")
sys.path.insert(0, r"E:\wx\论文素材_王晰作传\音域分析")
alb = importlib.import_module("批量专辑音域")


def ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bvid", required=True)
    a = ap.parse_args()
    src = next((p for p in VID.glob(a.bvid + "_*.mp4")), None)
    if not src:
        raise SystemExit("not found: " + a.bvid)
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    wav = WORK / (a.bvid + ".wav")
    if not wav.exists():
        subprocess.run([ffmpeg(), "-y", "-i", str(src), "-vn", "-ac", "2", "-ar", "44100", str(wav)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    vocals = alb.separate_vocals(str(wav), str(WORK / a.bvid), gpu=True, force=False)
    m = alb.analyze_vocals(vocals)
    m["bvid"] = a.bvid
    m["source"] = src.name
    (OUT / (a.bvid + ".json")).write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"bvid": a.bvid, "low": m["low_stable"], "span": m["span_octaves"],
                      "stability": m["stability_cents_median"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
