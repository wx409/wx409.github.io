#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""样片 v4：钩子结构 —— 先听 → 停住让大肥鱼说 → 再完整放一遍。

结构（约 30 秒）
  0–4s    只听：原片最低音那一下（字幕：先听这一句）
  4–13s   停住：画面定格在她的酒馆，TTS 配音（大肥鱼开口说），嘴型跟着配音包络
  13–24s  再放：完整段落，标尺 + 0.35 秒保持条 + F0 曲线
  24–30s  收尾：落点句 + 署名

音频：原片片段 + 静音段里的 TTS，用 ffmpeg 拼接与混音。
"""
from __future__ import annotations

import asyncio
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = Path(r"E:\wx\论文素材_王晰作传")
SCENE = BASE / "_bg_bar_v6.png"
CHAR_SRC = BASE / "_char_front_v3.png"
CLIP = sorted(BASE.glob("剪辑素材/BV1i4411d7MJ_*_merged.mp4"))[0]
F0 = BASE / "音域分析" / "专辑音频_分析" / "重游往昔" / "静止了的夜晚_f0.csv"
OUT = BASE / "样片_v4_钩子结构.mp4"
FPS = 25
LOW_T = 201.6
FONT = r"C:\Windows\Fonts\msyhbd.ttc"
VOICE = "zh-CN-YunxiNeural"      # 男声，偏温
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="s4_"))

LINES = [
    ("hook", "先听这一句。", 0.0),
    ("talk", "厉害吧。这个音，比男低音的及格线，还低一个半音。", 0.0),
    ("talk2", "而且他在这个音上，停了零点三五秒。不是扫一下就过。", 0.0),
]


def fnt(sz):
    return ImageFont.truetype(FONT, sz)


async def _all_tts(paths):
    for (_, text, _), p in zip(LINES, paths):
        c = edge_tts.Communicate(text, VOICE, rate="+0%")
        await c.save(str(p))


def make_voice() -> list[float]:
    """一次事件循环里生成全部配音，避免 proactor 关闭报错。"""
    paths = [tmp / ("v%d.mp3" % i) for i in range(len(LINES))]
    asyncio.run(_all_tts(paths))
    durs = []
    for i, p in enumerate(paths):
        r = subprocess.run([ff, "-i", str(p)], capture_output=True, text=True, errors="replace")
        d = 0.0
        for l in (r.stderr or "").splitlines():
            if "Duration" in l:
                hh, mm, ss = l.split("Duration:")[1].split(",")[0].strip().split(":")
                d = int(hh) * 3600 + int(mm) * 60 + float(ss)
                break
        durs.append(d)
        print("  TTS%d %.2fs: %s" % (i, d, LINES[i][1]))
    return durs


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


def mouth_frames(char_path: Path, voice_wav: Path, n: int) -> None:
    """按配音包络做嘴型（只在说话段用）。"""
    raw = subprocess.run([ff, "-i", str(voice_wav), "-f", "f32le", "-ac", "1", "-ar", "8000", "-"],
                         capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    hop = int(8000 / FPS)
    env = np.array([float(np.abs(a[i * hop:(i + 1) * hop]).mean()) if len(a) else 0.0 for i in range(n)])
    env = np.nan_to_num(env, nan=0.0, posinf=0.0, neginf=0.0)
    mx = float(env.max())
    env = env / mx if mx > 0 else np.zeros(n)
    ch = Image.open(char_path).convert("RGBA")
    w, h = ch.size
    cx, cy = int(w * 0.50), int(h * 0.437)
    for i in range(n):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        v = float(env[i]) if i < len(env) else 0
        rw, rh = int(7 + 8 * v), int(3 + 10 * v)
        d.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=(120, 45, 60, int(80 + 150 * v)))
        img.save(tmp / ("m_%04d.png" % i))


def main() -> int:
    char = dress()
    print("[tts] 生成配音…")
    durs = make_voice()
    hook, t1, t2 = durs

    # 时间轴
    A0 = 0.0                      # 先听
    A1 = 4.0
    B0 = A1
    B1 = A1 + t1 + 0.5            # 说第一句
    C0 = B1
    C1 = C0 + t2 + 0.5            # 说第二句
    D0 = C1
    D1 = D0 + 10.0                # 再放
    E0 = D1
    E1 = E0 + 4.0                 # 收尾
    total = E1
    n = int(total * FPS)
    print("[timeline] 总长 %.1fs（A %.1f | B %.1f | C %.1f | D %.1f | E %.1f）" % (total, A1, t1, t2, 10, 4))

    # 说话段嘴型：把两段配音拼起来
    voice_all = tmp / "voice.wav"
    subprocess.run([ff, "-y", "-i", str(tmp / "v1.mp3"), "-i", str(tmp / "v2.mp3"),
                    "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", "-ar", "8000", "-ac", "1",
                    str(voice_all)], capture_output=True)
    mouth_frames(Path(char), voice_all, int((t1 + t2 + 1) * FPS))

    # 字幕（ASS）
    def ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%d:%02d:%05.2f" % (h, m, s)
    cues = [(A0 + 0.2, A1 - 0.2, "先听这一句"),
            (B0 + 0.2, C1 - 0.2, "比男低音及格线还低一个半音"),
            (D0 + 0.2, D1 - 0.2, "站了 0.35 秒，不是扫一下就过"),
            (E0 + 0.2, E1 - 0.2, "低下去的是音区，不是稳定度")]
    ass = tmp / "s.ass"
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
    for a, b, t in cues:
        body += "Dialogue: 0,%s,%s,D,,0,0,0,,%s\n" % (ts(a), ts(b), t)
    ass.write_text(body, encoding="utf-8")

    # 音频：原片 A 段 + 静音 + 配音 + 原片 D 段
    audio = tmp / "mix.m4a"
    subprocess.run([ff, "-y",
                    "-ss", str(LOW_T - 3.6), "-t", "4", "-i", str(CLIP),
                    "-i", str(tmp / "v1.mp3"),
                    "-i", str(tmp / "v2.mp3"),
                    "-ss", str(LOW_T - 1.0), "-t", "10", "-i", str(CLIP),
                    "-filter_complex",
                    "[0:a]aresample=44100[a0];"
                    "[1:a]adelay=%d|%d[a1];"
                    "[2:a]adelay=%d|%d[a2];"
                    "[3:a]aresample=44100[a3];"
                    "[a0][a1][a2][a3]amix=inputs=4:normalize=0[m]"
                    % (int(B0 * 1000), int(B0 * 1000), int(C0 * 1000), int(C0 * 1000)),
                    "-map", "[m]", "-t", str(total), str(audio)], capture_output=True)

    # 视频：单画布
    filt = (
        "[0:v]scale=1080:1920,fps=%d[bg];"
        "[1:v]format=rgba[c0];[2:v]format=rgba[mth];[c0][mth]overlay=0:0[c1];"
        "[bg][c1]overlay=331:'610+4*sin(2*PI*t/3.2)':format=auto[v1];"
        "[3:v]split=2[full0][pip0];"
        "[full0]scale=-1:1920,crop=1080:1920:(iw-1080)/2:0,setsar=1,fps=%d[full];"
        "[pip0]scale=420:236:force_original_aspect_ratio=increase,crop=420:236,setsar=1,fps=%d[pp];"
        "[pp][4:v]alphamerge[pipm];"
        "[v1][full]overlay=0:0:enable='between(t,0,%.2f)'[v2];"
        "[v2][pipm]overlay=620:150:enable='gte(t,%.2f)'[v3];"
        "[v3]ass='%s',format=yuv420p[v]"
        % (FPS, FPS, FPS, A1, A1, str(ass).replace("\\", "/").replace(":", "\\:"))
    )

    m = Image.new("L", (420, 236), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, 419, 235], radius=26, fill=255)
    m.filter(ImageFilter.GaussianBlur(6)).save(tmp / "mask.png")

    cmd = [ff, "-y",
           "-loop", "1", "-t", str(total), "-i", str(SCENE),
           "-loop", "1", "-t", str(total), "-i", str(char),
           "-framerate", str(FPS), "-t", str(total), "-i", str(tmp / "m_%04d.png"),
           "-ss", str(LOW_T - 3.6), "-t", str(total), "-i", str(CLIP),
           "-loop", "1", "-t", str(total), "-i", str(tmp / "mask.png"),
           "-i", str(audio),
           "-filter_complex", filt, "-map", "[v]", "-map", "5:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-t", str(total), str(OUT)]
    print("[render] 单画布合成…")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print((r.stderr or "")[-900:]); return 4
    print("[done]", OUT, "%.1f MB" % (OUT.stat().st_size / 1024 / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
