#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地 Whisper 转写：把语料库里带视频/音频但无转写的条目转成文字。

用法：
  python -X utf8 project_b/corpus_transcribe.py --limit 2      # 试 2 条
  python -X utf8 project_b/corpus_transcribe.py                # 全部（后台跑）
模型：本地缓存 faster-whisper-large-v3-turbo（离线）
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import subprocess
import tempfile
from pathlib import Path

DB = Path(r"D:\wx409.github.io\data\corpus\corpus.db")
TRANS = Path(r"D:\wx409.github.io\data\corpus\transcripts")
FF = __import__("imageio_ffmpeg").get_ffmpeg_exe()


def safe(k: str) -> str:
    return re.sub(r"[^\w\-]+", "_", k)[:120]


def transcribe_one(model, media: str) -> str:
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "a.wav"
        r = subprocess.run([FF, "-v", "error", "-i", media, "-ac", "1", "-ar", "16000",
                            "-f", "wav", str(wav)], capture_output=True)
        if r.returncode != 0 or not wav.exists():
            return ""
        segs, _ = model.transcribe(str(wav), language="zh", vad_filter=True, beam_size=1)
        txt = "".join(s.text for s in segs).strip()
        if not txt:  # 唱段/纯音乐：VAD 会全滤掉，关掉重试
            segs, _ = model.transcribe(str(wav), language="zh", vad_filter=False, beam_size=5,
                                       initial_prompt="长亭外，古道边，芳草碧连天。")
            txt = "".join(s.text for s in segs).strip()
        return txt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default="large-v3-turbo")
    a = ap.parse_args()

    from faster_whisper import WhisperModel
    model = WhisperModel(a.model, device="cuda", compute_type="float16")

    con = sqlite3.connect(DB)
    q = ("select key, media from posts where media<>'' and (transcript is null or transcript='')")
    rows = con.execute(q).fetchall()
    rows = [r for r in rows if Path((r[1] or "").split("|")[0]).exists()]
    if a.limit:
        rows = rows[: a.limit]
    print(f"待转写 {len(rows)} 条")

    ok = 0
    TRANS.mkdir(parents=True, exist_ok=True)
    for i, (key, media) in enumerate(rows, 1):
        first = (media or "").split("|")[0]
        if not first or not Path(first).exists():
            continue
        txt = transcribe_one(model, first)
        if not txt:
            print(f"[{i}/{len(rows)}] 空 {key}")
            continue
        (TRANS / (safe(key) + ".txt")).write_text(txt, encoding="utf-8")
        con.execute("update posts set transcript=? where key=?", (txt, key))
        con.execute("update posts_fts set transcript=? where key=?", (txt, key))
        con.commit()
        ok += 1
        print(f"[{i}/{len(rows)}] OK {key} {len(txt)}字")
    print(f"\n完成 {ok} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
