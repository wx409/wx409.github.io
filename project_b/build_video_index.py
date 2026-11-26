#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_video_index.py —— 本地视频索引（巡演场次 / 歌曲 / 平台）

产物（私有，含绝对路径，不进 git、不上站）：
  E:\\wx\\私有工具\\video_index.json
  E:\\wx\\私有工具\\video_index_stats.md

用法：
  python -X utf8 project_b\\build_video_index.py
  python -X utf8 project_b\\build_video_index.py --limit 50   # 抽样调试
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
OUT = Path(r"E:\wx\私有工具\video_index.json")
STATS = Path(r"E:\wx\私有工具\video_index_stats.md")
EXTS = {".mp4", ".mkv", ".mov", ".flv", ".avi", ".webm", ".m4v"}
ROOTS = [
    (Path(r"E:\wx\私有工具\weibo_merged"), "微博", "合并稿"),
    (Path(r"E:\wx\私有工具\weibo_archive_studio"), "微博", "工作室"),
    (Path(r"E:\wx\私有工具\weibo_archive"), "微博", "本人"),
    (Path(r"E:\wx\私有工具\weibo_shaocheng_archive"), "微博", "少城"),
    (Path(r"E:\wx\论文素材_王晰作传\抖音"), "抖音", "官方"),
    (Path(r"E:\wx\论文素材_王晰作传\快手"), "快手", "官方"),
    (Path(r"E:\wx\私有工具\xhs_archive\官方账号\王晰"), "小红书", "官方"),
    (Path(r"E:\wx\六巡\20260823广州站\bilibili视频"), "B站", "六巡广州"),
    (Path(r"E:\wx\论文素材_王晰作传\B站\官方空间"), "B站", "官方空间"),
    (Path(r"E:\wx\声音素材库"), "声音节目", "节目/朗读"),
]


def load_songs():
    names = set()
    for p, key in [(ROOT / "data/archive_vocal_albums.json", "songs"), (ROOT / "data/songs_meta.json", "songs")]:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            seq = d.get(key) or []
            for x in (seq.values() if isinstance(seq, dict) else seq):
                t = x.get("title") if isinstance(x, dict) else x
                if t:
                    names.add(t)
        except Exception:
            pass
    try:
        sl = json.loads((ROOT / "data/setlists.json").read_text(encoding="utf-8")).get("setlists")
        seq = sl.values() if isinstance(sl, dict) else (sl or [])
        for show in seq:
            if isinstance(show, dict):
                for s in show.get("songs") or []:
                    if isinstance(s, str):
                        names.add(s)
    except Exception:
        pass
    return sorted({n for n in names if len(n) >= 2}, key=len, reverse=True)


def load_shows():
    out = []
    try:
        sl = json.loads((ROOT / "data/setlists.json").read_text(encoding="utf-8")).get("setlists")
        seq = sl.values() if isinstance(sl, dict) else (sl or [])
        for s in seq:
            if isinstance(s, dict) and s.get("date") and s.get("city"):
                out.append(s)
    except Exception:
        pass
    return out


SONGS = load_songs()
SHOWS = load_shows()
CITIES = sorted({s["city"] for s in SHOWS if s.get("city")}, key=len, reverse=True)


def ffprobe(path):
    try:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "format=duration:stream=width,height",
                            "-of", "json", str(path)], capture_output=True, text=True, timeout=20)
        d = json.loads(r.stdout or "{}")
        st = (d.get("streams") or [{}])[0]
        return round(float((d.get("format") or {}).get("duration") or 0), 1), st.get("width"), st.get("height")
    except Exception:
        return 0, None, None


def text_near(p: Path):
    chunks = [p.stem, p.parent.name]
    for f in list(p.parent.glob("*.txt"))[:3]:
        try:
            n = f.name.lower()
            if any(k in n for k in ("summary", "bilibili", "index", "all_")):
                continue
            if f.is_file() and f.stat().st_size < 20_000:
                chunks.append(f.read_text(encoding="utf-8", errors="ignore")[:2000])
        except Exception:
            pass
    return " ".join(chunks)


def parse_date(s):
    m = re.search(r"(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})", s)
    if m:
        try:
            return "%s-%s-%s" % (m.group(1), m.group(2), m.group(3))
        except Exception:
            return ""
    return ""


def detect_songs(text, title=""):
    hits = []
    for n in SONGS:
        if n in title:
            hits.append(n)
        elif ("《%s》" % n) in text:
            hits.append(n)
        elif len(n) >= 4 and n in text and any(c in text for c in ("唱", "歌", "现场", "Live", "翻唱", "演唱")):
            hits.append(n)
        if len(hits) >= 6:
            break
    return hits


def detect_show(date, text):
    for s in SHOWS:
        if date and str(s.get("date"))[:10] == date:
            if s.get("city") and s["city"] in text:
                return "%s %s" % (date, s["city"])
    for c in CITIES:
        if c in text:
            return ("%s %s" % (date, c)) if date else c
    return ""


def scan(item):
    p, platform, source = item
    dur, w, h = ffprobe(p)
    text = text_near(p)
    date = parse_date(p.name) or parse_date(p.parent.name) or parse_date(text)
    return {
        "path": str(p),
        "platform": platform,
        "source": source,
        "size_mb": round(p.stat().st_size / 1048576, 1),
        "duration_s": dur,
        "width": w,
        "height": h,
        "date": date,
        "city": next((c for c in CITIES if c in text), ""),
        "show": detect_show(date, text),
        "songs": detect_songs(text, p.stem),
        "title": p.stem[:120],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    files = []
    for root, platform, source in ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in EXTS:
                files.append((p, platform, source))
    files.sort(key=lambda x: str(x[0]))
    if a.limit:
        files = files[:a.limit]
    print("视频文件", len(files))
    vids = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, v in enumerate(ex.map(scan, files), 1):
            v["id"] = i
            vids.append(v)
            if i % 100 == 0:
                print("  ", i, flush=True)
    by_song, by_show, by_platform = {}, {}, {}
    for v in vids:
        by_platform.setdefault(v["platform"], []).append(v["id"])
        if v["show"]:
            by_show.setdefault(v["show"], []).append(v["id"])
        for s in v["songs"]:
            by_song.setdefault(s, []).append(v["id"])
    doc = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": len(vids),
        "total_gb": round(sum(v["size_mb"] for v in vids) / 1024, 2),
        "videos": vids,
        "by_song": {k: v for k, v in sorted(by_song.items(), key=lambda kv: -len(kv[1]))},
        "by_show": {k: v for k, v in sorted(by_show.items(), key=lambda kv: -len(kv[1]))},
        "by_platform": {k: len(v) for k, v in sorted(by_platform.items(), key=lambda kv: -len(kv[1]))},
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# 本地视频索引统计", "", "生成：%s" % doc["generated_at"], "",
             "合计 **%d** 个视频 / **%.2f GB**" % (doc["total"], doc["total_gb"]), "",
             "## 平台", ""]
    for k, v in doc["by_platform"].items():
        lines.append("- %s：%d" % (k, v))
    lines += ["", "## 歌曲（Top 30）", ""]
    for k, ids in list(doc["by_song"].items())[:30]:
        lines.append("- %s：%d 个视频" % (k, len(ids)))
    lines += ["", "## 场次（Top 20）", ""]
    for k, ids in list(doc["by_show"].items())[:20]:
        lines.append("- %s：%d" % (k, len(ids)))
    STATS.write_text("\n".join(lines), encoding="utf-8")
    print("写出", OUT, "|", STATS)


if __name__ == "__main__":
    raise SystemExit(main())
