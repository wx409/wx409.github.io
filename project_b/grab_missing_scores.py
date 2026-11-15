#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""补齐两条缺失谱子：一言千年（微博）+ 无荒（B站视频）。"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"E:\wx\私有工具\weibo_proxy")
import weibo_proxy as wp

OUT = Path(r"E:\wx\论文素材_王晰作传\曲谱_网友扒谱")


def bid_to_mid(bid: str) -> str:
    """微博 base62 短 id → 数字 mid。"""
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    n = 0
    for ch in bid:
        n = n * 62 + alphabet.index(ch)
    return str(n)


def grab_weibo(bid: str, name: str) -> int:
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    for mid in (bid_to_mid(bid), bid):
        try:
            m = wp._fetch_detail(mid)
        except Exception as e:
            print("  取详情异常", str(e)[:60]); m = None
        if m:
            pics = wp._extract_pics(m)
            print(f"  {name}: 命中 mid={mid}，图片 {len(pics)} 张")
            n = 0
            for i, u in enumerate(pics, 1):
                try:
                    wp._download(u, d / ("%02d.jpg" % i)); n += 1
                except Exception as e:
                    print("   图失败", i, str(e)[:40])
            return n
    return 0


def main() -> int:
    n1 = grab_weibo("JAQwtcL8V", "一言千年")
    print("一言千年 图片:", n1)

    # 无荒：B站视频（谱面视频），先下到本地备查
    d = OUT / "无荒"
    d.mkdir(parents=True, exist_ok=True)
    import imageio_ffmpeg, shutil, tempfile
    fb = Path(tempfile.gettempdir()) / "ffbin"; fb.mkdir(exist_ok=True)
    alias = fb / "ffmpeg.exe"
    if not alias.exists():
        shutil.copy2(imageio_ffmpeg.get_ffmpeg_exe(), alias)
    r = subprocess.run(["yt-dlp", "--ffmpeg-location", str(fb), "-f", "bv*[height<=720]+ba/b",
                        "-o", str(d / "无荒_%(id)s.%(ext)s"),
                        "https://www.bilibili.com/video/BV1ow4m1Y7nK"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = r.returncode == 0
    print("无荒 B站下载:", "OK" if ok else (r.stderr or "")[-120:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
