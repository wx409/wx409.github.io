#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按参考视频 BV1g14y127yw 做样片：以它的 17 秒长音为主体。

结构（约 24 秒）
  0–1.5s    标题
  1.5–18.5s 原视频全屏（17 秒），右下角读秒 1→17 + 音高读数
  18.5–23s  大肥鱼在酒馆里说（娃娃音 TTS）
  23–24s    收尾
"""
from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg

BASE = Path(r"E:\wx\论文素材_王晰作传")
CLIP = BASE / "剪辑素材" / "ref_note_merged.mp4"
BG = BASE / "场景_酒馆_手绘v4.png"
SEQ = BASE / "blender_out3" / "f_%04d.png"
OUT = BASE / "样片_长音_24s.mp4"
FPS = 25
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="note_"))

T_TITLE, T_NOTE, T_TALK, T_END = 1.5, 17.0, 4.5, 1.0
TOTAL = T_TITLE + T_NOTE + T_TALK + T_END
T0_NOTE = T_TITLE
T0_TALK = T_TITLE + T_NOTE


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stderr or "")


def main() -> int:
    async def go():
        await edge_tts.Communicate("一口气十七秒，中间没有换气。这不是技巧，是气息。",
                                   "zh-CN-XiaoyiNeural", rate="+6%", pitch="+28Hz").save(str(tmp / "t.mp3"))
    asyncio.run(go())

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
    for a, b, t in [(0.2, T_TITLE - 0.1, "一口气 17 秒"),
                    (T0_NOTE + 0.2, T0_TALK - 0.2, "听：中间没有换气"),
                    (T0_TALK + 0.2, TOTAL - 0.2, "气息不断，低音才稳")]:
        body += "Dialogue: 0,%s,%s,D,,0,0,0,,%s\n" % (ts(a), ts(b), t)
    ass.write_text(body, encoding="utf-8")

    # 读秒帧（17 秒 × 25fps）
    from PIL import Image, ImageDraw, ImageFont
    fnt = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 64)
    for i in range(int(T_NOTE * FPS)):
        im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        sec = (i + 1) / FPS
        d.rounded_rectangle([50, 1440, 640, 1560], radius=18, fill=(9, 13, 17, 170))
        d.text((80, 1452), "%.0f 秒" % sec, font=fnt, fill=(150, 225, 255))
        d.rounded_rectangle([300, 1490, 620, 1526], radius=16, fill=(30, 40, 52, 220))
        d.rounded_rectangle([300, 1490, 300 + int(320 * min(1, sec / T_NOTE)), 1526],
                            radius=16, fill=(106, 208, 255, 240))
        im.save(tmp / ("tm_%04d.png" % i))

    # 视频：第一段原片全屏，第二段酒馆+立绘
    v = tmp / "v.mp4"
    filt = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=%d[clip];"
        "[4:v]format=rgba[tm];[clip][tm]overlay=0:0:format=auto[c1];"
        "[1:v]scale=1080:1920,fps=%d[bg];[3:v]format=rgba[ch];"
        "[bg][ch]overlay=0:0:format=auto[b1];"
        "[b1]ass='%s',format=yuv420p[b2];"
        "[c1][b2]concat=n=2:v=1:a=0[vout]"
        % (FPS, FPS, str(ass).replace("\\", "/").replace(":", "\\:"))
    )
    rc, err = run([ff, "-y",
                   "-t", str(T_NOTE), "-i", str(CLIP),
                   "-loop", "1", "-t", str(T_TALK + T_END), "-i", str(BG),
                   "-loop", "1", "-t", str(T_TALK + T_END), "-i", str(BG),
                   "-framerate", str(FPS), "-stream_loop", "-1", "-t", str(T_TALK + T_END), "-i", str(SEQ),
                   "-framerate", str(FPS), "-t", str(T_NOTE), "-i", str(tmp / "tm_%04d.png"),
                   "-filter_complex", filt, "-map", "[vout]",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-an", str(v)])
    if rc != 0:
        print("视频失败:", err[-700:]); return 4
    print("[1/3] 视频 OK")

    a = tmp / "a.m4a"
    fa = ("[0:a]adelay=%d|%d[a1];[1:a]adelay=%d|%d,volume=1.5[a2];"
          "[a1][a2]amix=inputs=2:normalize=0:duration=longest,afade=t=out:st=%.1f:d=1.0[aout]"
          % (int(T0_NOTE * 1000), int(T0_NOTE * 1000), int(T0_TALK * 1000), int(T0_TALK * 1000), TOTAL - 1.0))
    rc, err = run([ff, "-y",
                   "-i", str(CLIP), "-i", str(tmp / "t.mp3"),
                   "-filter_complex", fa, "-map", "[aout]",
                   "-c:a", "aac", "-b:a", "160k", "-t", str(TOTAL), str(a)])
    if rc != 0:
        print("音频失败:", err[-700:]); return 4
    print("[2/3] 音频 OK")

    rc, err = run([ff, "-y", "-i", str(v), "-i", str(a), "-c:v", "copy", "-c:a", "copy",
                   "-movflags", "+faststart", "-shortest", str(OUT)])
    if rc != 0:
        print("合流失败:", err[-500:]); return 4
    rc, err = run([ff, "-i", str(OUT)])
    print("[3/3]", OUT, round(OUT.stat().st_size / 1024 / 1024, 2), "MB",
          "| Video", "Video:" in err, "| Audio", "Audio:" in err,
          [l.strip()[:40] for l in err.splitlines() if "Duration" in l])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
