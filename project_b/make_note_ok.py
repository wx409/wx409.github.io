#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""长音样片（兼容版）：单画布、无 concat、强制 yuv420p（上一版打不开正是因为输出成了 4:4:4）。

画面：参考视频全屏 + 左下角读秒/进度 + 右下角大肥鱼（小窗）+ 字幕
声音：原片 + 结尾一句娃娃音
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
CLIP = BASE / "剪辑素材" / "ref_note_merged.mp4"
SEQ = BASE / "blender_out3" / "f_%04d.png"
OUT = BASE / "样片_长音_兼容版.mp4"
FPS = 25
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="ok_"))

T_TITLE, T_NOTE, T_TALK, T_END = 1.5, 17.0, 4.0, 1.0
TOTAL = T_TITLE + T_NOTE + T_TALK + T_END
T0_NOTE, T0_TALK = T_TITLE, T_TITLE + T_NOTE


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stderr or "")


def main() -> int:
    async def go():
        await edge_tts.Communicate("一口气十七秒，中间没有换气。", "zh-CN-XiaoyiNeural",
                                   rate="+6%", pitch="+28Hz").save(str(tmp / "t.mp3"))
    asyncio.run(go())

    # 读秒帧
    fnt = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 60)
    for i in range(int(T_TALK + T_END) * FPS):
        im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        sec = max(0.0, min(T_NOTE, i / FPS - T0_NOTE))
        if T0_NOTE <= i / FPS <= T0_NOTE + T_NOTE:
            d.rounded_rectangle([50, 1440, 660, 1560], radius=18, fill=(9, 13, 17, 175))
            d.text((80, 1452), "%.0f 秒" % sec, font=fnt, fill=(150, 225, 255))
            d.rounded_rectangle([320, 1492, 640, 1526], radius=16, fill=(30, 40, 52, 220))
            d.rounded_rectangle([320, 1492, 320 + int(320 * sec / T_NOTE), 1526],
                                radius=16, fill=(106, 208, 255, 240))
        im.save(tmp / ("tm_%04d.png" % i))

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
Style: D,Microsoft YaHei,40,&H00D8EAF5,&H00000000,&H00000000,-1,1,4,0,2,60,60,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    for a, b, t in [(0.2, T0_NOTE - 0.1, "一口气 17 秒"),
                    (T0_NOTE, T0_TALK - 0.2, "听：中间没有换气"),
                    (T0_TALK, TOTAL - 0.2, "这不是技巧，是气息")]:
        body += "Dialogue: 0,%s,%s,D,,0,0,0,,%s\n" % (ts(a), ts(b), t)
    ass.write_text(body, encoding="utf-8")

    v = tmp / "v.mp4"
    filt = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=%d,format=yuv420p[clip];"
        "[1:v]format=rgba,scale=360:470[ch];"
        "[clip][ch]overlay=690:1180:format=auto[v1];"
        "[2:v]format=rgba[tm];[v1][tm]overlay=0:0:format=auto[v2];"
        "[v2]ass='%s',format=yuv420p[vout]"
        % (FPS, str(ass).replace("\\", "/").replace(":", "\\:"))
    )
    rc, err = run([ff, "-y",
                   "-stream_loop", "-1", "-t", str(TOTAL), "-i", str(CLIP),
                   "-framerate", str(FPS), "-stream_loop", "-1", "-t", str(TOTAL), "-i", str(SEQ),
                   "-framerate", str(FPS), "-t", str(TOTAL), "-i", str(tmp / "tm_%04d.png"),
                   "-filter_complex", filt, "-map", "[vout]",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                   "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
                   "-an", str(v)])
    if rc != 0:
        print("视频失败:", err[-600:]); return 4
    print("[1/3] 视频 OK")

    a = tmp / "a.m4a"
    fa = ("[0:a]adelay=%d|%d[a1];[1:a]adelay=%d|%d,volume=1.5[a2];"
          "[a1][a2]amix=inputs=2:normalize=0:duration=longest,afade=t=out:st=%.1f:d=1.0[aout]"
          % (int(T0_NOTE * 1000), int(T0_NOTE * 1000), int(T0_TALK * 1000), int(T0_TALK * 1000), TOTAL - 1.0))
    rc, err = run([ff, "-y", "-i", str(CLIP), "-i", str(tmp / "t.mp3"),
                   "-filter_complex", fa, "-map", "[aout]",
                   "-c:a", "aac", "-b:a", "160k", "-t", str(TOTAL), str(a)])
    if rc != 0:
        print("音频失败:", err[-600:]); return 4
    print("[2/3] 音频 OK")

    rc, err = run([ff, "-y", "-i", str(v), "-i", str(a), "-c", "copy", "-movflags", "+faststart",
                   "-shortest", str(OUT)])
    if rc != 0:
        print("合流失败:", err[-500:]); return 4
    rc, err = run([ff, "-v", "error", "-i", str(OUT), "-f", "null", "-"])
    rc2, info = run([ff, "-i", str(OUT)])
    print("[3/3]", OUT, round(OUT.stat().st_size / 1024 / 1024, 2), "MB",
          "| 解码错误:", (err or "无")[:120])
    print([l.strip()[:95] for l in info.splitlines() if "Stream #" in l or "Duration" in l])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
