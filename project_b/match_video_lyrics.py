#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""match_video_lyrics.py —— 用 ASR 转写 + 私有歌词做歌名匹配

输入：E:\\wx\\私有工具\\video_transcripts\\<id>.txt
     E:\\wx\\论文素材_王晰作传\\歌词_私有\\albums_lyrics.json
输出：更新 E:\\wx\\私有工具\\video_index.json 的 lyrics_song / lyrics_score
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
INDEX = Path(r"E:\wx\\私有工具\\video_index.json")
TRANS = Path(r"E:\wx\\私有工具\\video_transcripts")
LYRICS = Path(r"E:\wx\论文素材_王晰作传\歌词_私有\albums_lyrics.json")
CREDIT = re.compile(r"制作|编曲|和声|录音|混音|母带|吉他|贝斯|鼓|弦乐|词|曲|Producer|Arrangement|Vocal|Engineer|Studio")


def norm(s: str) -> str:
    return re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", s or "")


def ngrams(s: str, n=5):
    return {s[i:i + n] for i in range(len(s) - n + 1)}


def load_lyrics():
    d = json.loads(LYRICS.read_text(encoding="utf-8"))
    out = {}
    for al in d.get("albums") or []:
        for s in al.get("songs") or []:
            title = s.get("title") or ""
            lines = []
            for x in s.get("lyrics") or []:
                t = (x.get("text") or "").strip()
                if len(norm(t)) >= 8 and not CREDIT.search(t):
                    lines.append(norm(t))
            if title and lines:
                out[title] = set().union(*[ngrams(x) for x in lines])
    return out


def main():
    songs = load_lyrics()
    print("歌词曲目", len(songs))
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    done = 0
    for v in idx.get("videos") or []:
        tp = TRANS / ("%d.txt" % v["id"])
        if not tp.exists():
            continue
        text = norm(tp.read_text(encoding="utf-8", errors="ignore"))
        if len(text) < 20:
            continue
        tg = ngrams(text)
        best, score = "", 0.0
        for title, lg in songs.items():
            if not lg:
                continue
            inter = len(tg & lg)
            s = inter / (len(lg) ** 0.5)
            if s > score:
                best, score = title, s
        if score >= 0.35 and best:
            v["lyrics_song"] = best
            v["lyrics_score"] = round(score, 3)
            v["songs"] = sorted(set(v.get("songs") or []) | {best})
            done += 1
    INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding="utf-8")
    print("命中", done, "条 →", INDEX)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
