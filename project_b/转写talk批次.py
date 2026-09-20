# -*- coding: utf-8 -*-
"""talk 批量转写（faster-whisper 本地缓存模型，GPU float16）。输入 wav/mp4 文件或目录，输出 txt + segments.json。

用法:
  python -X utf8 project_b\\转写talk批次.py --dir <目录> --out <输出目录>
  python -X utf8 project_b\\转写talk批次.py --files a.wav b.MP4 --out <输出目录>

mp4 自动用 ffmpeg 抽 16k 单声道 wav 到临时目录再转写；已有同名 .txt 则跳过（幂等）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

MEDIA = (".wav", ".mp3", ".m4a", ".aac", ".mp4", ".flac")
LOCAL_MODEL = r"E:\work\代码\录音转写\models\faster-whisper-large-v3-turbo"
MODEL = LOCAL_MODEL if os.path.isdir(LOCAL_MODEL) else "mobiuslabsgmbh/faster-whisper-large-v3-turbo"


def as_wav(exe: str, f: Path, tmp: Path) -> Path:
    if f.suffix.lower() in (".wav", ".flac"):
        return f
    out = tmp / (f.stem + ".wav")
    subprocess.run([exe, "-v", "error", "-y", "-i", str(f), "-ac", "1", "-ar", "16000", str(out)], check=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    ap.add_argument("--files", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    srcs: list[Path] = [Path(p) for p in a.files]
    if a.dir:
        srcs += sorted(p for p in Path(a.dir).rglob("*") if p.suffix.lower() in MEDIA)
    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    todo = [p for p in srcs if not (out_dir / (p.stem + ".txt")).exists()]
    print(f"待转写 {len(todo)} / 共 {len(srcs)}")
    if not todo:
        return 0

    from faster_whisper import WhisperModel

    print("加载模型:", MODEL)
    try:
        model = WhisperModel(MODEL, device="cuda", compute_type="float16")
    except Exception:
        model = WhisperModel(MODEL, device="cpu", compute_type="int8")

    import imageio_ffmpeg

    exe = imageio_ffmpeg.get_ffmpeg_exe()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for p in todo:
            w = as_wav(exe, p, tmp)
            segs, info = model.transcribe(str(w), language="zh", vad_filter=True, beam_size=5)
            segs = list(segs)
            text = "".join(s.text for s in segs).strip()
            (out_dir / (p.stem + ".txt")).write_text(text, encoding="utf-8")
            (out_dir / (p.stem + ".segments.json")).write_text(
                json.dumps(
                    [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text} for s in segs],
                    ensure_ascii=False, indent=1,
                ),
                encoding="utf-8",
            )
            print(f"  ✓ {p.name} → {len(text)} 字")
    return 0


if __name__ == "__main__":
    sys.exit(main())
