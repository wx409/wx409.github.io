#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大肥鱼评王晰（终版结构）：听 → 停 → 点评 → 再完整听。

32 秒
  0–3    酒馆：大肥鱼开口“先听一个音”
  3–11   王晰原片全屏（单音 7.4 秒），左下读秒 + 右上 220.6Hz
  11–19  停：大肥鱼点评（娃娃音），王晰静音
  19–27  再完整听同一段
  27–32  收尾

纪律：她说话时王晰完全静音；放王晰时她只安静听（不出声）。
输出 yuv420p / High profile，保证能播。
"""
from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

BASE = Path(r"E:\wx\论文素材_王晰作传")
CLIP = sorted((BASE / "现场录音-补充").glob("BV1Qm42177HY_*想游泳的星*.mp4"))[0]
BG = BASE / "场景_酒馆_手绘v4.png"
SEQ = BASE / "blender_out3" / "f_%04d.png"
OUT = BASE / "大肥鱼评王晰_32s.mp4"
FPS = 25
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="fin_"))

NOTE_AT = 99.3      # 单音起点 3:57.8
NOTE_LEN = 6.09               # 单音持续
T_TALK1, T_TALK2 = 3.0, 5.0
TOTAL = T_TALK1 + NOTE_LEN + 8.0 + NOTE_LEN + T_TALK2
T0_NOTE1 = T_TALK1
T0_TALK = T_TALK1 + NOTE_LEN
T0_NOTE2 = T0_TALK + 8.0
T0_END = T0_NOTE2 + NOTE_LEN

LINES = [("先听一个音。", T_TALK1 - 0.5),
         ("一口气，六点一秒，中间没有换气。", T0_TALK + 0.3),
         ("低音能稳，是因为气一直没有断。", T0_END + 0.3)]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stderr or "")


def main() -> int:
    # ① 三段配音
    async def go():
        for i, (t, _) in enumerate(LINES):
            await edge_tts.Communicate(t, "zh-CN-XiaoyiNeural", rate="+4%", pitch="+26Hz").save(str(tmp / ("v%d.mp3" % i)))
    asyncio.run(go())
    durs = []
    for i in range(len(LINES)):
        rc, e = run([ff, "-i", str(tmp / ("v%d.mp3" % i))])
        d = 0.0
        for l in e.splitlines():
            if "Duration" in l:
                hh, mm, ss = l.split("Duration:")[1].split(",")[0].strip().split(":")
                d = int(hh) * 3600 + int(mm) * 60 + float(ss)
        durs.append(d)
    print("[tts] 时长:", [round(d, 2) for d in durs])

    # ② 读秒帧（只在两段原片里出现）
    fnt = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 58)
    f2 = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 38)
    n = int(TOTAL * FPS)
    for i in range(n):
        t = i / FPS
        im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for base in (T0_NOTE1, T0_NOTE2):
            if base <= t <= base + NOTE_LEN:
                sec = t - base
                d.rounded_rectangle([50, 1430, 700, 1560], radius=18, fill=(9, 13, 17, 178))
                d.text((80, 1442), "%.1f 秒" % sec, font=fnt, fill=(150, 225, 255))
                d.rounded_rectangle([340, 1490, 660, 1526], radius=16, fill=(30, 40, 52, 220))
                d.rounded_rectangle([340, 1490, 340 + int(320 * sec / NOTE_LEN), 1526],
                                    radius=16, fill=(106, 208, 255, 240))
                d.text((700, 1452), "A3 · 220.6Hz", font=f2, fill=(255, 210, 160))
        im.save(tmp / ("tm_%04d.png" % i))

    # ③ 字幕
    def ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%d:%02d:%05.2f" % (h, m, s)
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
    cues = [(0.2, T_TALK1 - 0.2, "先听一个音"),
            (T0_NOTE1, T0_TALK - 0.2, "《想游泳的星》· 四巡上海 2024-04-06"),
            (T0_TALK + 0.2, T0_NOTE2 - 0.3, "一个音，7.4 秒，中间没有断"),
            (T0_NOTE2 + 0.2, T0_END - 0.2, "同一段，完整再听一遍"),
            (T0_END + 0.2, TOTAL - 0.2, "低音稳，是因为气不断")]
    for a, b, t in cues:
        body += "Dialogue: 0,%s,%s,D,,0,0,0,,%s\n" % (ts(a), ts(b), t)
    ass.write_text(body, encoding="utf-8")

    # ④ 视频：酒馆常驻，原片按时间窗叠上来
    v = tmp / "v.mp4"
    filt = (
        "[0:v]scale=1080:1920,fps=%d[bg];"
        "[1:v]format=rgba,scale=560:730[ch];[bg][ch]overlay=280:760:format=auto[v1];"
        "[2:v]format=rgba[tm];[v1][tm]overlay=0:0:format=auto[v2];"
        "[3:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=%d[clip];"
        "[v2][clip]overlay=0:0:enable='between(t,%.2f,%.2f)+between(t,%.2f,%.2f)'[v3];"
        "[v3]ass='%s',format=yuv420p[vout]"
        % (FPS, FPS, T0_NOTE1, T0_TALK, T0_NOTE2, T0_END,
           str(ass).replace("\\", "/").replace(":", "\\:"))
    )
    rc, err = run([ff, "-y",
                   "-loop", "1", "-t", str(TOTAL), "-i", str(BG),
                   "-framerate", str(FPS), "-stream_loop", "-1", "-t", str(TOTAL), "-i", str(SEQ),
                   "-framerate", str(FPS), "-t", str(TOTAL), "-i", str(tmp / "tm_%04d.png"),
                   "-ss", str(NOTE_AT - T0_NOTE1), "-t", str(TOTAL), "-i", str(CLIP),
                   "-filter_complex", filt, "-map", "[vout]",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                   "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0", "-an", str(v)])
    if rc != 0:
        print("视频失败:", err[-700:]); return 4
    print("[1/3] 视频 OK")

    # ⑤ 音频：原片两段 + 三段配音（互不重叠）
    a = tmp / "a.m4a"
    fa = ("[0:a]atrim=0:%.3f,asetpts=PTS-STARTPTS,adelay=%d|%d[g1];"
          "[0:a]atrim=0:%.3f,asetpts=PTS-STARTPTS,adelay=%d|%d[g2];"
          "[1:a]adelay=%d|%d[a1];[2:a]adelay=%d|%d[a2];[3:a]adelay=%d|%d[a3];"
          "[g1][g2][a1][a2][a3]amix=inputs=5:normalize=0:duration=longest,"
          "afade=t=out:st=%.1f:d=1.2[aout]"
          % (NOTE_LEN, int(T0_NOTE1 * 1000), int(T0_NOTE1 * 1000),
             NOTE_LEN, int(T0_NOTE2 * 1000), int(T0_NOTE2 * 1000),
             int(0 * 1000), int(0 * 1000),
             int((T0_TALK + 0.3) * 1000), int((T0_TALK + 0.3) * 1000),
             int((T0_END + 0.3) * 1000), int((T0_END + 0.3) * 1000),
             TOTAL - 1.2))
    rc, err = run([ff, "-y",
                   "-ss", str(NOTE_AT), "-t", str(NOTE_LEN), "-i", str(CLIP),
                   "-i", str(tmp / "v0.mp3"), "-i", str(tmp / "v1.mp3"), "-i", str(tmp / "v2.mp3"),
                   "-filter_complex", fa, "-map", "[aout]",
                   "-c:a", "aac", "-b:a", "160k", "-t", str(TOTAL), str(a)])
    if rc != 0:
        print("音频失败:", err[-700:]); return 4
    print("[2/3] 音频 OK")

    rc, err = run([ff, "-y", "-i", str(v), "-i", str(a), "-c", "copy", "-movflags", "+faststart",
                   "-shortest", str(OUT)])
    if rc != 0:
        print("合流失败:", err[-500:]); return 4
    rc, dec = run([ff, "-v", "error", "-i", str(OUT), "-f", "null", "-"])
    rc2, info = run([ff, "-i", str(OUT)])
    print("[3/3]", OUT, round(OUT.stat().st_size / 1024 / 1024, 2), "MB", "| 解码错误:", (dec or "无")[:100])
    print([l.strip()[:95] for l in info.splitlines() if "Stream #" in l or "Duration" in l])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
