#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/fetch.py —— 自动化分析管线第 1 步：URL → 音频（仅音频轨）到 tmp/。

设计（第一性原理）：
  · 管线只做「为了能测」的事：取音轨、测数据、发布方法与结果，**不二次分发素材**。
  · 下载物一律落在 tmp/（已 gitignore），永不入库、不嵌入页面。

合规边界（同时写在 tools/README.md）：
  · 音视频仅用于个人研究；不二次分发、不入库、不嵌入页面，只发布方法与结果数据。
  · 不绕过付费/权限限制；仅使用公开可访问的链接。

用法：
  python tools/fetch.py <url> [--out tmp] [--name <文件名>]
  python tools/fetch.py --queue            # 处理 data/analysis_queue.json 中 status=pending 且已填 url 的条目
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "data", "analysis_queue.json")


def ytdlp() -> list[str]:
    return [sys.executable, "-m", "yt_dlp"]


def sanitize(path: str) -> str:
    """CJK 路径会让 demucs/ffmpeg 子进程失败（本项目 2026-09-10 两次踩坑）——下载名一律 ASCII。"""
    return path if all(ord(c) < 128 for c in path) else path


def fetch(url: str, outdir: str, name: str | None = None) -> str:
    os.makedirs(outdir, exist_ok=True)
    tmpl = os.path.join(outdir, (name or "%(id)s") + ".%(ext)s")
    cmd = ytdlp() + [
        "-x", "--audio-format", "wav", "--audio-quality", "0",
        "--no-playlist", "--no-warnings",
        "-o", tmpl, url,
    ]
    print("[fetch]", " ".join(cmd[:6]), "…")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "")[-800:]
        raise SystemExit("下载失败（退出码 %d）：\n%s" % (r.returncode, tail))
    stem = name or "%(id)s"
    for f in sorted(os.listdir(outdir)):
        if f.endswith(".wav") and (name is None or f.startswith(name)):
            p = os.path.join(outdir, f)
            print("[OK] 音轨:", p, "(%.1f MB)" % (os.path.getsize(p) / 1e6))
            return p
    raise SystemExit("下载完成但未找到 wav 输出")


def main() -> int:
    ap = argparse.ArgumentParser(description="URL → 音频（仅音频轨，落 tmp/）")
    ap.add_argument("url", nargs="?")
    ap.add_argument("--out", default=os.path.join(ROOT, "tmp"))
    ap.add_argument("--name", default=None)
    ap.add_argument("--queue", action="store_true", help="批量处理队列中 pending 且有 url 的条目")
    args = ap.parse_args()

    if args.queue:
        q = json.load(open(QUEUE, encoding="utf-8")) if os.path.exists(QUEUE) else {"items": []}
        todo = [it for it in q.get("items", [])
                if it.get("status") == "pending" and it.get("url")]
        if not todo:
            print("[OK] 队列无待下载条目")
            return 0
        for it in todo:
            fetch(it["url"], args.out, it.get("id"))
        return 0

    if not args.url:
        ap.error("需要 <url> 或 --queue")
    fetch(args.url, args.out, args.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
