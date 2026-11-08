#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""样片 v2：单画布 · 画中画带蒙版 · 角色有衣服/有反应 · 精确切到低音。

与 v1 的区别（都是你指出的）
  1. 不再是「先真人后讲」的分段拼接，而是**一个画布持续 24 秒**：
     背景 + 立绘 + 画中画（带圆角羽化蒙版）+ 曲线 + 波形 + 字幕，同时存在
  2. 立绘**加了衣服**（围裙 + 深蓝马甲），用 PIL 直接叠在透明立绘上
  3. 角色**有反应**：音频包络驱动——张嘴幅度 + 身体轻微起伏 + 眨眼
  4. **精确切到低音**：原片起点 = 最低音时间 - 0.25 秒，让那一记落在第 3 秒附近
"""
from __future__ import annotations

import csv
import math
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE = Path(r"E:\wx\论文素材_王晰作传")
SCENE = BASE / "场景_酒馆_手绘v4.png"
CHAR_SRC = BASE / "_char_front_v3.png"
CLIP = sorted(BASE.glob("剪辑素材/BV1i4411d7MJ_*_merged.mp4"))[0]
F0 = BASE / "音域分析" / "专辑音频_分析" / "重游往昔" / "静止了的夜晚_f0.csv"
OUT = BASE / "样片_v2_24s.mp4"
FPS = 25
DUR = 24
LOW_T = 201.6
START = LOW_T - 3.0        # 让低音落在第 3 秒

ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="s2_"))


# ── 1. 给立绘穿衣服 ────────────────────────────────────────
def dress() -> Path:
    ch = Image.open(CHAR_SRC).convert("RGBA")
    w, h = ch.size
    # 围裙：从胸口到膝上的一片白色，带两条肩带
    ap = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ap)
    top, bot = int(h * 0.52), int(h * 0.86)
    d.polygon([(int(w * .40), top), (int(w * .60), top),
               (int(w * .66), bot), (int(w * .34), bot)], fill=(247, 250, 252, 235))
    # 肩带
    d.line([(int(w * .42), int(h * .44)), (int(w * .43), top)], fill=(247, 250, 252, 235), width=9)
    d.line([(int(w * .58), int(h * .44)), (int(w * .57), top)], fill=(247, 250, 252, 235), width=9)
    # 深蓝马甲：两侧竖条
    d.polygon([(int(w * .34), int(h * .50)), (int(w * .40), int(h * .50)),
               (int(w * .40), int(h * .82)), (int(w * .33), int(h * .82))], fill=(38, 62, 104, 225))
    d.polygon([(int(w * .66), int(h * .50)), (int(w * .60), int(h * .50)),
               (int(w * .60), int(h * .82)), (int(w * .67), int(h * .82))], fill=(38, 62, 104, 225))
    # 腰带
    d.rectangle([int(w * .38), int(h * .53), int(w * .62), int(h * .555)], fill=(30, 48, 82, 230))
    # 小鲸尾刺绣
    cx, cy = int(w * .5), int(h * .70)
    d.polygon([(cx, cy - 10), (cx + 14, cy + 6), (cx, cy + 2), (cx - 14, cy + 6)],
              fill=(74, 134, 192, 210))
    ch2 = Image.alpha_composite(ch, ap.filter(ImageFilter.GaussianBlur(0.6)))
    p = tmp / "char_dressed.png"
    ch2.save(p)
    print("[dress] 立绘加衣：", p.name)
    return p


# ── 2. 音频包络 ────────────────────────────────────────────
def envelope() -> np.ndarray:
    wav = tmp / "a.wav"
    subprocess.run([ff, "-y", "-ss", str(START), "-t", str(DUR), "-i", str(CLIP),
                    "-ac", "1", "-ar", "8000", str(wav)], capture_output=True)
    raw = subprocess.run([ff, "-i", str(wav), "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    hop = int(8000 / FPS)
    n = DUR * FPS
    env = np.array([float(np.abs(a[i * hop:(i + 1) * hop]).mean()) if len(a) else 0.0
                    for i in range(n)])
    env = env / (env.max() or 1)
    print("[env] 包络帧:", len(env), "峰值:", round(float(env.max()), 3))
    return env


# ── 3. 嘴部 + 眨眼帧 ───────────────────────────────────────
def mouth_frames(char: Image.Image, env: np.ndarray) -> list[Path]:
    w, h = char.size
    cx, cy = int(w * 0.50), int(h * 0.465)
    files = []
    for i, v in enumerate(env):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        op = 0.25 + 0.75 * float(v)
        rw, rh = int(9 + 9 * v), int(5 + 13 * v)
        d.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=(120, 45, 60, int(230 * op)))
        # 眨眼：每 3.4 秒闭 0.12 秒
        t = i / FPS
        if abs((t % 3.4)) < 0.12:
            for ex in (int(w * 0.40), int(w * 0.60)):
                d.rounded_rectangle([ex - 22, int(h * 0.385), ex + 22, int(h * 0.395)],
                                    radius=4, fill=(255, 236, 220, 255))
        p = tmp / ("m_%04d.png" % i)
        img.save(p)
        files.append(p)
    return files


# ── 4. 曲线帧 ──────────────────────────────────────────────
def curve_frames() -> list[Path]:
    W, H = 440, 140
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
        line = [(int((t - START) / DUR * W), int(H - (h - lo) / rng * (H - 12) - 6))
                for t, h in pts if t <= cut]
        if len(line) > 1:
            d.line(line, fill=(106, 208, 255, 255), width=3)
            d.ellipse([line[-1][0] - 5, line[-1][1] - 5, line[-1][0] + 5, line[-1][1] + 5],
                      fill=(190, 240, 255, 255))
        img.save(tmp / ("c_%04d.png" % i))
    print("[curve] 帧数:", n, "Hz:", round(lo, 1), "-", round(hi, 1))
    return [tmp / ("c_%04d.png" % i) for i in range(n)]


# ── 5. 画中画蒙版 ─────────────────────────────────────────
def pip_mask(size=(420, 236), radius=26) -> Path:
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    m = m.filter(ImageFilter.GaussianBlur(6))
    p = tmp / "pipmask.png"
    m.save(p)
    return p


def main() -> int:
    char_path = dress()
    env = envelope()
    char = Image.open(char_path)
    mouth_frames(char, env)
    curve_frames()
    mask = pip_mask()

    srt = tmp / "s.srt"
    srt.write_text("""1
00:00:00,200 --> 00:00:04,000
先听这一句

2
00:00:03,400 --> 00:00:08,500
3:21 · A#1 58.2Hz

3
00:00:08,600 --> 00:00:15,000
他在这个音上站了 0.35 秒

4
00:00:15,200 --> 00:00:22,000
两千多个版本，七成以上开口就在那儿

5
00:00:22,200 --> 00:00:23,800
低下去的是音区，不是稳定度
""", encoding="utf-8")

    # 画中画 420x236，右上角；含蒙版
    filt = (
        "[0:v]scale=1080:1920,fps=%d[bg];"
        "[1:v]format=rgba,scale=629:860[ch];"
        "[2:v]format=rgba[mth];"
        "[ch][mth]overlay=0:0:format=auto[c1];"
        "[bg][c1]overlay=331:'610+4*sin(2*PI*t/3.2)':format=auto[v1];"
        "[3:v]format=rgba[cur];"
        "[v1][cur]overlay=84:342:format=auto[v2];"
        # 画中画：裁 16:9 → 420x236，加圆角蒙版
        "[4:v]trim=start=0:end=%d,setpts=PTS-STARTPTS,scale=420:236:force_original_aspect_ratio=increase,crop=420:236,fps=%d[p0];"
        "[p0][5:v]alphamerge[p1];"
        "[v2][p1]overlay=620:150:format=auto[v3];"
        "[4:a]showwaves=s=1080x120:mode=p2p:colors=0x6ad0ff@0.85:rate=%d[w];"
        "[v3][w]overlay=x=0:y=1700:format=auto[v4];"
        "[v4]subtitles='%s':force_style='FontName=Microsoft YaHei,Fontsize=18,"
        "PrimaryColour=&H00D8EAF5,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=280',"
        "format=yuv420p[v]"
        % (FPS, DUR, FPS, FPS, str(srt).replace("\\", "/").replace(":", "\\:"))
    )

    cmd = [ff, "-y",
           "-loop", "1", "-t", str(DUR), "-i", str(SCENE),
           "-framerate", str(FPS), "-t", str(DUR), "-i", str(tmp / "char_dressed.png"),
           "-framerate", str(FPS), "-t", str(DUR), "-i", str(tmp / "m_%04d.png"),
           "-framerate", str(FPS), "-t", str(DUR), "-i", str(tmp / "c_%04d.png"),
           "-ss", str(START), "-t", str(DUR), "-i", str(CLIP),
           "-loop", "1", "-t", str(DUR), "-i", str(mask),
           "-filter_complex", filt, "-map", "[v]", "-map", "4:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-t", str(DUR), str(OUT)]
    print("渲染 v2 …")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print((r.stderr or "")[-900:])
        return 4
    print("完成：", OUT, "%.1f MB" % (OUT.stat().st_size / 1024 / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
