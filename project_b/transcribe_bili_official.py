#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""transcribe_bili_official.py —— 转写 B站官方空间已下载视频（本地 faster-whisper）"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(r"E:\wx\论文素材_王晰作传\B站\官方空间")
OUT = Path(r"E:\wx\私有工具\video_transcripts\bili_official")
MODEL = "large-v3-turbo"


def main():
    from faster_whisper import WhisperModel
    OUT.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(MODEL, device="cuda", compute_type="float16")
    for f in sorted(ROOT.glob("*.mp4")):
        stem = f.stem
        txt = OUT / (stem + ".txt")
        js = OUT / (stem + ".json")
        if txt.exists() and txt.stat().st_size > 200:
            print("skip", f.name, flush=True)
            continue
        print("ASR", f.name, flush=True)
        segs, info = model.transcribe(str(f), language="zh", vad_filter=False, beam_size=5)
        lines, rows = [], []
        for s in segs:
            lines.append("[%02d:%02d] %s" % (int(s.start) // 60, int(s.start) % 60, s.text.strip()))
            rows.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
        txt.write_text("\n".join(lines), encoding="utf-8")
        js.write_text(json.dumps({"file": f.name, "model": MODEL, "duration": info.duration, "segments": rows},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
        print("done", f.name, len(rows), flush=True)


if __name__ == "__main__":
    main()
