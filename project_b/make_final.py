#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""最终样片（稳健三段式）：视频轨 → 音频轨 → 合流，避免复杂滤镜一次失败。

15 秒结构
  0–2.0s   标题
  2.0–8.0s 听（想游泳的星 14.8 秒段的前 6 秒）
  8.0–12.5s 说（TTS，角色嘴型）
  12.5–15s 再听

三段式的好处：任何一段失败都能单独重跑，不会整条报废。
"""
from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg

BASE = Path(r"E:\wx\论文素材_王晰作传")
BG = BASE / "场景_酒馆_手绘v4.png"
SEQ = BASE / "blender_out3" / "f_%04d.png"
CLIP = sorted((BASE / "剪辑素材").glob("BV1i4411d7MJ_*_merged.mp4"))[0]
SING = BASE / "_staging_现场" / "s36_20240406" / "12 想游泳的星.wav"
OUT = BASE / "样片_最终_15s.mp4"
FPS = 25
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="fin_"))

T_TITLE, T_SING1, T_TALK, T_SING2 = 2.0, 6.0, 4.5, 2.5
TOTAL = T_TITLE + T_SING1 + T_TALK + T_SING2
T0_SING1 = T_TITLE
T0_TALK = T_TITLE + T_SING1
T0_SING2 = T0_TALK + T_TALK

LINES = ["这一口气，十四点八秒，中间没有换气。", "嗓音像件乐器，颤音十年没变。"]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stderr or "")


def main() -> int:
    # ① TTS（一次事件循环）
    async def go():
        for i, t in enumerate(LINES):
            await edge_tts.Communicate(t, "zh-CN-XiaoyiNeural", rate="+6%", pitch="+28Hz").save(str(tmp / ("v%d.mp3" % i)))
    asyncio.run(go())
    tts = tmp / "talk.wav"
    run([ff, "-y", "-i", str(tmp / "v0.mp3"), "-i", str(tmp / "v1.mp3"),
         "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1", "-ar", "44100", "-ac", "2", str(tts)])

    # ② 字幕
    def ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%d:%02d:%05.2f" % (h, m, s)
    cues = [(0.2, T_TITLE - 0.2, "《想游泳的星》· 四巡上海"),
            (T0_SING1 + 0.2, T0_TALK - 0.2, "一口气 14.8 秒"),
            (T0_TALK + 0.2, T0_SING2 - 0.2, "中间没有换气，嗓音像件乐器"),
            (T0_SING2 + 0.2, TOTAL - 0.2, "颤音十年没变")]
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
    for a, b, t in cues:
        body += "Dialogue: 0,%s,%s,D,,0,0,0,,%s\n" % (ts(a), ts(b), t)
    ass = tmp / "s.ass"
    ass.write_text(body, encoding="utf-8")

    # ③ 视频轨（无声）
    video = tmp / "video.mp4"
    filt = ("[0:v]scale=1080:1920,fps=%d[bg];"
            "[1:v]format=rgba[ch];"
            "[bg][ch]overlay=0:0:format=auto[v1];"
            "[2:v]trim=start=0:end=%.2f,setpts=PTS-STARTPTS,scale=420:236:force_original_aspect_ratio=increase,crop=420:236,setsar=1,fps=%d[p0];"
            "[p0][3:v]alphamerge[p1];"
            "[v1][p1]overlay=620:150:format=auto[v2];"
            "[v2]ass='%s',format=yuv420p[out]"
            % (FPS, TOTAL, FPS, str(ass).replace("\\", "/").replace(":", "\\:")))
    rc, err = run([ff, "-y",
                   "-loop", "1", "-t", str(TOTAL), "-i", str(BG),
                   "-framerate", str(FPS), "-stream_loop", "-1", "-t", str(TOTAL), "-i", str(SEQ),
                   "-ss", "199.5", "-t", str(TOTAL), "-i", str(CLIP),
                   "-loop", "1", "-t", str(TOTAL), "-i", str(BASE / "_pipmask.png"),
                   "-filter_complex", filt, "-map", "[out]",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-an", str(video)])
    if rc != 0:
        print("视频轨失败:", err[-500:]); return 4
    print("[1/3] 视频轨 OK", round(video.stat().st_size / 1024 / 1024, 2), "MB")

    # ④ 音频轨
    audio = tmp / "audio.m4a"
    fa = ("[0:a]atrim=0:%.2f,asetpts=PTS-STARTPTS,adelay=%d|%d[a1];"
          "[1:a]adelay=%d|%d,volume=1.5[a2];"
          "[2:a]atrim=0:%.2f,asetpts=PTS-STARTPTS,adelay=%d|%d[a3];"
          "[a1][a2][a3]amix=inputs=3:normalize=0:duration=longest,alimiter=limit=0.95,afade=t=out:st=%.1f:d=1.2[aout]"
          % (T_SING1, int(T0_SING1 * 1000), int(T0_SING1 * 1000),
             int(T0_TALK * 1000), int(T0_TALK * 1000),
             T_SING2, int(T0_SING2 * 1000), int(T0_SING2 * 1000), TOTAL - 1.2))
    rc, err = run([ff, "-y",
                   "-ss", "233.7", "-t", str(T_SING1), "-i", str(SING),
                   "-i", str(tts),
                   "-ss", "239.7", "-t", str(T_SING2), "-i", str(SING),
                   "-filter_complex", fa, "-map", "[aout]",
                   "-c:a", "aac", "-b:a", "160k", "-t", str(TOTAL), str(audio)])
    if rc != 0:
        print("音频轨失败:", err[-500:]); return 4
    print("[2/3] 音频轨 OK")

    # ⑤ 合流
    rc, err = run([ff, "-y", "-i", str(video), "-i", str(audio),
                   "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart",
                   "-shortest", str(OUT)])
    if rc != 0:
        print("合流失败:", err[-500:]); return 4
    print("[3/3] 完成:", OUT, round(OUT.stat().st_size / 1024 / 1024, 2), "MB")

    # 校验：必须有视频+音频两条流
    rc, err = run([ff, "-i", str(OUT)])
    has_v = "Video:" in err
    has_a = "Audio:" in err
    print("[校验] 视频流:", has_v, "｜音频流:", has_a)
    return 0 if (has_v and has_a) else 5


if __name__ == "__main__":
    raise SystemExit(main())
