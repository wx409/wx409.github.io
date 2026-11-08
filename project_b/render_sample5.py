#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""样片 v5：用《想游泳的星》的 5.7 秒长音做主体。

为什么换素材
  原来用《静止了的夜晚》的 0.35 秒低音——观众看不出"厉害"。
  《想游泳的星》在 3:57.9–4:03.6 有一口气 **5.70 秒**（A3≈220Hz），
  这是"看得见、听得懂"的证据，适合当第一条。

结构（约 30 秒，不用钩子形式）
  0–3s    标题卡：曲目 / 场次 / 日期
  3–13s   听：原音 10 秒（含 5.7 秒长音），画面配"秒数计时器"随声音累加
  13–18s  停：大肥鱼解说（TTS），演唱完全静音，不叠音
  18–28s  再听：同一段完整再放
  28–30s  收尾：一句落点
"""
from __future__ import annotations

import asyncio
import csv
import math
import statistics
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = Path(r"E:\wx\论文素材_王晰作传")
SCENE = BASE / "_bg_bar_v6.png"
CHAR_SRC = BASE / "_char_front_v3.png"
WAV = BASE / "_staging_现场" / "s36_20240406" / "12 想游泳的星.wav"
F0 = BASE / "音域分析" / "分析结果" / "想游泳的星_f0.csv"
OUT = BASE / "样片_v5_长音.mp4"
FPS = 25
A0 = 233.7          # 3:53.7，一口气 14.8 秒的起点
SEG = 15.0
FONT = r"C:\Windows\Fonts\msyhbd.ttc"
VOICE = "zh-CN-YunjianNeural"    # 更低沉一点的男声
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="s5_"))

TALK = ["这一口气，十四点八秒。", "中间没有换气。单音也稳了七秒多。"]


def fnt(sz):
    return ImageFont.truetype(FONT, sz)


async def _tts(paths):
    for t, p in zip(TALK, paths):
        await edge_tts.Communicate(t, VOICE, rate="+0%").save(str(p))


def voice() -> tuple[float, Path]:
    paths = [tmp / ("v%d.mp3" % i) for i in range(len(TALK))]
    asyncio.run(_tts(paths))
    wav = tmp / "talk.wav"
    subprocess.run([ff, "-y", "-i", str(paths[0]), "-i", str(paths[1]),
                    "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", "-ar", "44100",
                    str(wav)], capture_output=True)
    r = subprocess.run([ff, "-i", str(wav)], capture_output=True, text=True, errors="replace")
    d = 0.0
    for l in (r.stderr or "").splitlines():
        if "Duration" in l:
            hh, mm, ss = l.split("Duration:")[1].split(",")[0].strip().split(":")
            d = int(hh) * 3600 + int(mm) * 60 + float(ss)
    print("[tts] 解说 %.2fs: %s" % (d, " / ".join(TALK)))
    return d, wav


def dress() -> Path:
    ch = Image.open(CHAR_SRC).convert("RGBA")
    w, h = ch.size
    ap = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ap)
    top, bot = int(h * 0.615), int(h * 0.90)
    d.polygon([(int(w * .41), top), (int(w * .59), top),
               (int(w * .64), bot), (int(w * .36), bot)], fill=(247, 250, 252, 232))
    d.line([(int(w * .43), int(h * .50)), (int(w * .43), top)], fill=(247, 250, 252, 232), width=8)
    d.line([(int(w * .57), int(h * .50)), (int(w * .57), top)], fill=(247, 250, 252, 232), width=8)
    d.polygon([(int(w * .35), int(h * .60)), (int(w * .41), int(h * .60)),
               (int(w * .41), int(h * .86)), (int(w * .34), int(h * .86))], fill=(38, 62, 104, 220))
    d.polygon([(int(w * .65), int(h * .60)), (int(w * .59), int(h * .60)),
               (int(w * .59), int(h * .86)), (int(w * .66), int(h * .86))], fill=(38, 62, 104, 220))
    p = tmp / "char_dressed.png"
    Image.alpha_composite(ch, ap.filter(ImageFilter.GaussianBlur(0.6))).save(p)
    return p


def frames(char_path: Path, talk_wav: Path, total: float, talk0: float, talkdur: float) -> None:
    n = int(total * FPS)
    raw = subprocess.run([ff, "-i", str(talk_wav), "-f", "f32le", "-ac", "1", "-ar", "8000", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    hop = int(8000 / FPS)
    env = np.array([float(np.abs(a[i * hop:(i + 1) * hop]).mean()) if len(a) else 0.0
                    for i in range(int(talkdur * FPS) + 1)])
    env = np.nan_to_num(env, nan=0.0)
    env = env / (env.max() or 1)
    ch = Image.open(char_path).convert("RGBA")
    w, h = ch.size
    cx, cy = int(w * 0.50), int(h * 0.437)
    for i in range(n):
        t = i / FPS
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        if talk0 <= t <= talk0 + talkdur:
            k = int((t - talk0) * FPS)
            v = float(env[k]) if k < len(env) else 0
            rw, rh = int(7 + 8 * v), int(3 + 10 * v)
            d.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=(120, 45, 60, int(80 + 150 * v)))
        img.save(tmp / ("m_%04d.png" % i))

        # 秒数计时器（在长音段 3–13s 与 18–28s 各跑一次）
        ov = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        do = ImageDraw.Draw(ov)
        for base in (3.0, 18.0):
            if base <= t <= base + SEG:
                sec = min(14.80, max(0.0, t - base - 0.2))
                txt = "%.1f 秒" % sec
                do.rounded_rectangle([80, 1500, 1000, 1620], radius=18, fill=(9, 13, 17, 170))
                do.text((110, 1518), txt, font=fnt(58), fill=(150, 225, 255))
                bw = int(560 * min(1.0, sec / 14.80))
                do.rounded_rectangle([360, 1560, 920, 1592], radius=16, fill=(30, 40, 52, 220))
                do.rounded_rectangle([360, 1560, 360 + bw, 1592], radius=16, fill=(106, 208, 255, 240))
        ov.save(tmp / ("t_%04d.png" % i))


def main() -> int:
    char = dress()
    talkdur, talk_wav = voice()
    TALK0 = 13.0
    R0 = TALK0 + talkdur + 0.6
    total = R0 + SEG + 2.0
    print("[timeline] 总长 %.1fs（听 3-13｜说 13-%.1f｜再听 %.1f-%.1f）" % (total, TALK0 + talkdur, R0, R0 + SEG))
    frames(Path(char), talk_wav, total, TALK0, talkdur)

    audio = tmp / "mix.m4a"
    subprocess.run([ff, "-y",
                    "-ss", str(A0), "-t", str(SEG), "-i", str(WAV),
                    "-i", str(talk_wav),
                    "-ss", str(A0), "-t", str(SEG), "-i", str(WAV),
                    "-filter_complex",
                    "[0:a]aformat=sample_rates=44100:channel_layouts=stereo[a0];"
                    "[1:a]adelay=%d|%d,volume=1.6[a1];"
                    "[2:a]adelay=%d|%d[a2];"
                    "[a0][a1][a2]amix=inputs=3:normalize=0:duration=longest[m]"
                    % (int((SEG + 0.5) * 1000), int((SEG + 0.5) * 1000),
                       int((R0) * 1000), int((R0) * 1000)),
                    "-map", "[m]", "-t", str(total), str(audio)], capture_output=True)

    ass = tmp / "s.ass"

    def ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%d:%02d:%05.2f" % (h, m, s)
    body = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: D,Microsoft YaHei,44,&H00D8EAF5,&H00000000,&H00000000,-1,1,4,0,2,60,60,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    for a, b, t in [(0.2, 2.9, "《想游泳的星》· 四巡上海 2024-04-06"),
                    (3.0, 17.9, "听这一口气"),
                    (TALK0, TALK0 + talkdur, "5.7 秒，中间没有换气"),
                    (R0, R0 + SEG, "同一段，再听一遍"),
                    (R0 + SEG + 0.2, total - 0.2, "低音稳，是因为气不断")]:
        body += "Dialogue: 0,%s,%s,D,,0,0,0,,%s\n" % (ts(a), ts(b), t)
    ass.write_text(body, encoding="utf-8")

    m = Image.new("L", (420, 236), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, 419, 235], radius=26, fill=255)
    m.filter(ImageFilter.GaussianBlur(6)).save(tmp / "mask.png")

    filt = (
        "[0:v]scale=1080:1920,fps=%d[bg];"
        "[1:v]format=rgba[c0];[2:v]format=rgba[mth];[c0][mth]overlay=0:0[c1];"
        "[bg][c1]overlay=331:'610+4*sin(2*PI*t/3.2)':format=auto[v1];"
        "[3:v]format=rgba[tm];[v1][tm]overlay=0:0:format=auto[v2];"
        "[v2]ass='%s',format=yuv420p[v]"
        % (FPS, str(ass).replace("\\", "/").replace(":", "\\:"))
    )
    cmd = [ff, "-y",
           "-loop", "1", "-t", str(total), "-i", str(SCENE),
           "-loop", "1", "-t", str(total), "-i", str(char),
           "-framerate", str(FPS), "-t", str(total), "-i", str(tmp / "m_%04d.png"),
           "-framerate", str(FPS), "-t", str(total), "-i", str(tmp / "t_%04d.png"),
           "-i", str(audio),
           "-filter_complex", filt, "-map", "[v]", "-map", "4:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-t", str(total), str(OUT)]
    print("[render] 合成…")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print((r.stderr or "")[-900:]); return 4
    print("[done]", OUT, "%.1f MB" % (OUT.stat().st_size / 1024 / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
