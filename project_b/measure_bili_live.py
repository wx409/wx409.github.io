#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""measure_bili_live.py —— 对 B站官方空间新下载的现场直拍做声学测量"""
from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
VID = Path(r"E:\wx\论文素材_王晰作传\B站\官方空间")
WORK = Path(r"E:\wx\论文素材_王晰作传\音域分析\B站官方空间_20261126")
OUT = ROOT / "data" / "bili_live_measurements_2026.json"
sys.path.insert(0, r"E:\wx\论文素材_王晰作传\音域分析")
alb = importlib.import_module("批量专辑音域")

TRACKS = [
    ("BV1Ab4y1g7Wj", "多听有益", "多听有益"),
    ("BV1yc411X7PQ", "甩啦甩啦", "甩啦甩啦"),
    ("BV1FN41137xb", "永不失联的爱", "永不失联的爱"),
    ("BV1fW4y1X7wX", "三首直拍", "小河"),
    ("BV1rX4y1s7Fa", "三巡深圳点歌", "静止了的夜晚"),
]


def ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    studio = {x.get("title"): x for x in json.loads((ROOT / "data" / "archive_vocal_albums.json").read_text(encoding="utf-8")).get("songs", [])}
    rows = []
    for bvid, tag, studio_title in TRACKS:
        src = next((p for p in VID.glob(bvid + "_*.mp4")), None)
        if not src:
            print("missing", bvid)
            continue
        wav = WORK / (bvid + ".wav")
        if not wav.exists():
            subprocess.run([ffmpeg(), "-y", "-i", str(src), "-vn", "-ac", "2", "-ar", "44100", str(wav)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("separate", bvid, flush=True)
        vocals = alb.separate_vocals(str(wav), str(WORK / bvid), gpu=True, force=False)
        print("analyze", bvid, flush=True)
        m = alb.analyze_vocals(vocals)
        st = studio.get(studio_title)
        rows.append({
            "bvid": bvid, "tag": tag, "source": src.name,
            "low_stable": m["low_stable"], "high_stable": m["high_stable"],
            "f0_min_hz": m.get("f0_min_hz"), "filter": m.get("filter"),
            "span_octaves": m["span_octaves"], "stability_cents": m["stability_cents_median"],
            "intonation_cents": m["intonation_cents_median"], "vibrato_hz": m["vibrato_rate_hz_median"],
            "note_count": m["note_count"], "duration_s": m["duration_s"],
            "studio": {"title": studio_title, "low": st.get("low"), "low_hz": st.get("low_hz"),
                       "span_octaves": st.get("span_octaves"), "stability_cents": st.get("stability_cents")} if st else None,
        })
    OUT.write_text(json.dumps({"generated_at": "2026-11-26", "method": "demucs htdemucs + YIN；稳定音门槛同专辑", "tracks": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("->", OUT)


if __name__ == "__main__":
    main()
