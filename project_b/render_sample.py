#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整样片渲染：真人片段 + 酒馆场景 + 鲸鱼娘 + 真实 F0 曲线 + 字幕。

结构（24 秒）
  0–4s   真人片段全屏（最低音那一刻）
  4–12s  酒馆场景：她站台后，曲线生长
  12–20s 酒馆场景 + 右上角真人画中画
  20–24s 收尾：她 + 落点句 + 署名

用法
  python -X utf8 project_b\\render_sample.py
"""
from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

BASE = Path(r"E:\wx\论文素材_王晰作传")
SCENE = BASE / "场景_酒馆_手绘v4.png"
CHAR = BASE / "_char_front_v3.png"
CLIP = sorted(BASE.glob("剪辑素材/BV1i4411d7MJ_*_merged.mp4"))[0]
F0 = BASE / "音域分析" / "专辑音频_分析" / "重游往昔" / "静止了的夜晚_f0.csv"
OUT = BASE / "样片_完整版_24s.mp4"
START = 197.5           # 原片起点（最低音 201.6）
DUR = 24
FPS = 25
ff = imageio_ffmpeg.get_ffmpeg_exe()

tmp = Path(tempfile.mkdtemp(prefix="sample_"))

# ── 曲线帧 ────────────────────────────────────────────────
W, H = 460, 150
pts = []
with open(F0, encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f):
        try:
            t, hz = float(r["time_s"]), float(r["f0_hz"])
        except Exception:
            continue
        if START <= t <= START + DUR and hz > 0:
            pts.append((t, hz))
lo, hi = min(h for _, h in pts), max(h for _, h in pts)
rng = max(hi - lo, 6.0)
n = DUR * FPS
for i in range(n):
    frac = (i + 1) / n
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cut = START + frac * DUR
    cur = [(t, h) for t, h in pts if t <= cut]
    line = [(int((t - START) / DUR * W), int(H - (h - lo) / rng * (H - 14) - 7)) for t, h in cur]
    if len(line) > 1:
        d.line(line, fill=(106, 208, 255, 255), width=3)
        d.ellipse([line[-1][0] - 5, line[-1][1] - 5, line[-1][0] + 5, line[-1][1] + 5],
                  fill=(180, 235, 255, 255))
    img.save(tmp / ("c_%04d.png" % i))

# ── 字幕 ──────────────────────────────────────────────────
srt = tmp / "s.srt"
srt.write_text("""1
00:00:00,300 --> 00:00:03,800
3:21 · A#1 58.2Hz

2
00:00:04,200 --> 00:00:11,800
他在这个音上站了 0.35 秒

3
00:00:12,200 --> 00:00:19,800
两千多个版本，七成以上开口就在那儿

4
00:00:20,200 --> 00:00:23,600
低下去的是音区，不是稳定度
""", encoding="utf-8")

# ── 滤镜图 ────────────────────────────────────────────────
filt = (
    # 场景 + 角色
    "[0:v]scale=1080:1920,fps=%d,split=3[bg1][bg2][bg3];"
    "[1:v]scale=629:860,format=rgba[ch];"
    "[bg1][ch]overlay=331:'610+5*sin(2*PI*t/3.4)':format=auto[b1];"
    "[bg2][ch]overlay=331:'610+5*sin(2*PI*t/3.4)':format=auto[b2];"
    "[bg3][ch]overlay=331:'610+5*sin(2*PI*t/3.4)':format=auto[b3];"
    # 曲线
    "[2:v]format=rgba[cur];"
    "[b1][cur]overlay=84:342:format=auto[s2];"
    "[b2][cur]overlay=84:342:format=auto[s3a];"
    # 画中画
    "[3:v]split=2[v3a][v3b];"
    "[v3a]trim=start=0:end=8,setpts=PTS-STARTPTS,scale=420:-1,setsar=1,fps=%d[pip];"
    "[s3a][pip]overlay=620:150:format=auto[s3];"
    # 真人全屏
    "[v3b]trim=start=0:end=4,setpts=PTS-STARTPTS,scale=-1:1920,crop=1080:1920:(iw-1080)/2:0,setsar=1,fps=%d[s1];"
    # 拼接
    "[s1][s2][s3][b3]concat=n=4:v=1:a=0,subtitles='%s':force_style='FontName=Microsoft YaHei,"
    "Fontsize=23,PrimaryColour=&H00D8EAF5,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=150',"
    "format=yuv420p[v]"
    % (FPS, FPS, FPS, str(srt).replace("\\", "/").replace(":", "\\:"))
)

cmd = [ff, "-y",
       "-loop", "1", "-t", str(DUR), "-i", str(SCENE),
       "-loop", "1", "-t", str(DUR), "-i", str(CHAR),
       "-framerate", str(FPS), "-t", str(DUR), "-i", str(tmp / "c_%04d.png"),
       "-ss", str(START), "-t", str(DUR), "-i", str(CLIP),
       "-filter_complex", filt, "-map", "[v]", "-map", "3:a",
       "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
       "-c:a", "aac", "-b:a", "160k", "-t", str(DUR), str(OUT)]
print("渲染完整样片…")
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
if r.returncode != 0:
    print((r.stderr or "")[-900:])
    raise SystemExit(4)
print("完成：", OUT, "%.1f MB" % (OUT.stat().st_size / 1024 / 1024))
