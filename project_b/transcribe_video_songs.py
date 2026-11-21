#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""transcribe_video_songs.py —— 微博视频转写 + 歌名匹配（提升视频索引精度）

读/写：E:\\wx\\私有工具\\video_index.json
转写：E:\\wx\\私有工具\\video_transcripts\\<id>.txt
用法：
  python -X utf8 project_b\\transcribe_video_songs.py --limit 5
  python -X utf8 project_b\\transcribe_video_songs.py --resume        # 续跑未转写
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
INDEX = Path(r"E:\wx\私有工具\video_index.json")
TRANS = Path(r"E:\wx\私有工具\video_transcripts")
MODEL = "large-v3-turbo"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    d = json.loads(INDEX.read_text(encoding="utf-8"))
    vids = [v for v in d["videos"] if v.get("platform") == "微博"]
    if a.resume:
        vids = [v for v in vids if not v.get("transcript_path")]
    if a.limit:
        vids = vids[:a.limit]
    if not vids:
        print("没有待转写视频")
        return 0
    TRANS.mkdir(parents=True, exist_ok=True)
    from faster_whisper import WhisperModel
    model = WhisperModel(MODEL, device="cuda", compute_type="float16")
    sys.path.insert(0, str(ROOT / "project_b"))
    from build_video_index import detect_songs

    done = 0
    for i, v in enumerate(vids, 1):
        src = v["path"]
        if not os.path.exists(src):
            continue
        wav = os.path.join(tempfile.gettempdir(), "vt_%s.wav" % v["id"])
        try:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src,
                            "-ac", "1", "-ar", "16000", wav], check=True, timeout=120)
            segs, _ = model.transcribe(wav, language="zh", vad_filter=False, beam_size=1)
            text = "".join(s.text.strip() for s in segs)
        except Exception as e:
            print("[%d/%d] FAIL %s %s" % (i, len(vids), v["id"], str(e)[:60]))
            continue
        tp = TRANS / ("%d.txt" % v["id"])
        tp.write_text(text, encoding="utf-8")
        v["transcript_path"] = str(tp)
        v["songs"] = sorted(set(v.get("songs") or []) | set(detect_songs(text, v.get("title", ""))))
        done += 1
        if done % 10 == 0:
            INDEX.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[%d/%d] ok %s chars=%d songs=%s" % (i, len(vids), v["id"], len(text), v["songs"]), flush=True)
    # 重建反查
    by_song = {}
    for v in d["videos"]:
        for s in v.get("songs") or []:
            by_song.setdefault(s, []).append(v["id"])
    d["by_song"] = {k: v for k, v in sorted(by_song.items(), key=lambda kv: -len(kv[1]))}
    d["transcribed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    INDEX.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("完成", done, "条 →", INDEX)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
