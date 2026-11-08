#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终样片 v2：把手绘场景 + 绑定立绘 + 画中画 + F0 曲线 + 波形 + 读秒 + Hz 读数。

15 秒
  0–2    标题
  2–8    听长音（读秒 0→5.7、Hz 读数、曲线、波形、画中画）
  8–12.5 说（娃娃音，嘴型、曲线继续、画中画）
  12.5–15 再听（淡出）
"""
from __future__ import annotations

import asyncio
import csv
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = Path(r"E:\wx\论文素材_王晰作传")
BG = BASE / "场景_酒馆_手绘v4.png"
SEQ = BASE / "blender_out3" / "f_%04d.png"
CLIP = sorted((BASE / "现场录音-补充").glob("BV1Qm42177HY_*想游泳的星*.mp4"))[0]
SING = sorted((BASE / "现场录音-补充").glob("BV1Qm42177HY_*想游泳的星*.wav"))[0]
F0 = BASE / "音域分析" / "分析结果" / "想游泳的星_f0.csv"
MASK = BASE / "_pipmask.png"
OUT = BASE / "样片_最终_15s.mp4"
FPS = 25
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="fin2_"))
FONT = r"C:\Windows\Fonts\msyhbd.ttc"

T_TITLE, T_SING1, T_TALK, T_SING2 = 2.0, 14.8, 4.5, 3.0
TOTAL = T_TITLE + T_SING1 + T_TALK + T_SING2
T0_SING1 = T_TITLE
T0_TALK = T_TITLE + T_SING1
T0_SING2 = T0_TALK + T_TALK
SING_AT = 233.7     # 想游泳的星 长音起点（3:53.7）


def fnt(s):
    return ImageFont.truetype(FONT, s)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stderr or "")


def make_overlays():
    """曲线帧 + 读秒/Hz 帧。"""
    n = int(TOTAL * FPS)
    pts = []
    with open(F0, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                t, hz = float(r["time_s"]), float(r["f0_hz"])
            except Exception:
                continue
            if SING_AT - 0.5 <= t <= SING_AT + T_SING1 + 0.5 and hz > 0:
                pts.append((t, hz))
    lo, hi = (min(h for _, h in pts), max(h for _, h in pts)) if pts else (200, 240)
    rng = max(hi - lo, 8.0)
    CW, CH = 460, 150
    for i in range(n):
        t = i / FPS
        # 曲线
        cur = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        d = ImageDraw.Draw(cur)
        prog = min(1.0, max(0.0, (t - T0_SING1) / T_SING1)) if t >= T0_SING1 else 0.0
        seg = [(x, h) for x, h in pts if x <= SING_AT + prog * T_SING1]
        line = [(int((x - SING_AT) / T_SING1 * CW), int(CH - (h - lo) / rng * (CH - 12) - 6)) for x, h in seg]
        if len(line) > 1:
            d.line(line, fill=(106, 208, 255, 255), width=3)
            d.ellipse([line[-1][0] - 5, line[-1][1] - 5, line[-1][0] + 5, line[-1][1] + 5], fill=(190, 240, 255, 255))
        cur.save(tmp / ("c_%04d.png" % i))

        # 读秒 + Hz
        ov = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        do = ImageDraw.Draw(ov)
        if T0_SING1 <= t <= T0_SING1 + T_SING1:
            sec = min(14.8, max(0.0, t - T0_SING1))
            do.rounded_rectangle([70, 1440, 1010, 1560], radius=18, fill=(9, 13, 17, 175))
            do.text((100, 1452), "%.1f 秒" % sec, font=fnt(56), fill=(150, 225, 255))
            bw = int(560 * min(1.0, sec / 14.8))
            do.rounded_rectangle([360, 1490, 920, 1526], radius=16, fill=(30, 40, 52, 220))
            do.rounded_rectangle([360, 1490, 360 + bw, 1526], radius=16, fill=(106, 208, 255, 240))
            do.text((640, 1452), "A3 · 220.6Hz", font=fnt(40), fill=(255, 210, 160))
        ov.save(tmp / ("t_%04d.png" % i))
    print("[overlay] 帧数", n)


def main() -> int:
    async def go():
        for i, t in enumerate(["这一口气，十四点八秒，中间没有换气。", "嗓音像件乐器，颤音十年没变。"]):
            await edge_tts.Communicate(t, "zh-CN-XiaoyiNeural", rate="+6%", pitch="+28Hz").save(str(tmp / ("v%d.mp3" % i)))
    asyncio.run(go())
    tts = tmp / "talk.wav"
    run([ff, "-y", "-i", str(tmp / "v0.mp3"), "-i", str(tmp / "v1.mp3"),
         "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", "-ar", "44100", "-ac", "2", str(tts)])

    def ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%d:%02d:%05.2f" % (h, m, s)
    cues = [(0.2, T_TITLE - 0.2, "《想游泳的星》· 四巡上海"),
            (T0_SING1 + 0.2, T0_TALK - 0.2, "一口气 14.8 秒"),
            (T0_TALK + 0.2, T0_SING2 - 0.2, "中间没有换气，嗓音像件乐器"),
            (T0_SING2 + 0.2, TOTAL - 0.2, "颤音十年没变")]
    ass = tmp / "s.ass"
    body = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: D,Microsoft YaHei,40,&H00D8EAF5,&H00000000,&H00000000,-1,1,4,0,2,60,60,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    for a, b, t in cues:
        body += "Dialogue: 0,%s,%s,D,,0,0,0,,%s\n" % (ts(a), ts(b), t)
    ass.write_text(body, encoding="utf-8")

    make_overlays()

    video = tmp / "v.mp4"
    filt = (
        "[0:v]scale=1080:1920,fps=%d[bg];"
        "[1:v]format=rgba[ch];[bg][ch]overlay=0:0:format=auto[v1];"
        "[2:v]format=rgba[cur];[v1][cur]overlay=64:300:format=auto[v2];"
        "[3:v]format=rgba[tm];[v2][tm]overlay=0:0:format=auto[v3];"
        "[4:v]trim=start=0:end=%.2f,setpts=PTS-STARTPTS,scale=420:236:force_original_aspect_ratio=increase,crop=420:236,setsar=1,fps=%d[p0];"
        "[p0][5:v]alphamerge[p1];[v3][p1]overlay=620:150:format=auto[v4];"
        "[6:a]showwaves=s=1080x110:mode=p2p:colors=0x6ad0ff@0.85:rate=%d[w];"
        "[v4][w]overlay=x=0:y=1740:format=auto[v5];"
        "[v5]ass='%s',format=yuv420p[out]"
        % (FPS, TOTAL, FPS, FPS, str(ass).replace("\\", "/").replace(":", "\\:"))
    )
    rc, err = run([ff, "-y",
                   "-loop", "1", "-t", str(TOTAL), "-i", str(BG),
                   "-framerate", str(FPS), "-stream_loop", "-1", "-t", str(TOTAL), "-i", str(SEQ),
                   "-framerate", str(FPS), "-t", str(TOTAL), "-i", str(tmp / "c_%04d.png"),
                   "-framerate", str(FPS), "-t", str(TOTAL), "-i", str(tmp / "t_%04d.png"),
                   "-ss", str(SING_AT - T0_SING1), "-t", str(TOTAL), "-i", str(CLIP),
                   "-loop", "1", "-t", str(TOTAL), "-i", str(MASK),
                   "-ss", str(SING_AT), "-t", str(T_SING1), "-i", str(SING),
                   "-filter_complex", filt, "-map", "[out]",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-an", str(video)])
    if rc != 0:
        print("视频轨失败:", err[-600:]); return 4
    print("[1/3] 视频 OK")

    audio = tmp / "a.m4a"
    fa = ("[0:a]atrim=0:%.2f,asetpts=PTS-STARTPTS,adelay=%d|%d[a1];"
          "[1:a]adelay=%d|%d,volume=1.6[a2];"
          "[2:a]atrim=0:%.2f,asetpts=PTS-STARTPTS,adelay=%d|%d[a3];"
          "[a1][a2][a3]amix=inputs=3:normalize=0:duration=longest,alimiter=limit=0.95,"
          "afade=t=out:st=%.1f:d=1.2[aout]"
          % (T_SING1, int(T0_SING1 * 1000), int(T0_SING1 * 1000),
             int(T0_TALK * 1000), int(T0_TALK * 1000),
             T_SING2, int(T0_SING2 * 1000), int(T0_SING2 * 1000), TOTAL - 1.2))
    rc, err = run([ff, "-y",
                   "-ss", str(SING_AT), "-t", str(T_SING1), "-i", str(SING),
                   "-i", str(tts),
                   "-ss", "239.2", "-t", "3.2", "-i", str(SING),
                   "-filter_complex", fa, "-map", "[aout]",
                   "-c:a", "aac", "-b:a", "160k", "-t", str(TOTAL), str(audio)])
    if rc != 0:
        print("音频轨失败:", err[-600:]); return 4
    print("[2/3] 音频 OK")

    rc, err = run([ff, "-y", "-i", str(video), "-i", str(audio), "-c:v", "copy", "-c:a", "copy",
                   "-movflags", "+faststart", "-shortest", str(OUT)])
    if rc != 0:
        print("合流失败:", err[-600:]); return 4
    rc, err = run([ff, "-i", str(OUT)])
    print("[3/3]", OUT, round(OUT.stat().st_size / 1024 / 1024, 2), "MB",
          "| Video", "Video:" in err, "| Audio", "Audio:" in err,
          "|", [l.strip()[:36] for l in err.splitlines() if "Duration" in l])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
