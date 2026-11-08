#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""大肥鱼评王晰 · 修正版（逐条对应你指出的硬伤）

修掉的六处
  1. 人脸被切 → 不再硬裁 9:16；原片按宽度完整显示，上下用自身模糊铺满（无黑边）
  2. 大黑边   → 同上（模糊填充，不是黑）
  3. 数字不一致 → 统一 6.09 秒（字幕/配音/读秒三处同一个数）
  4. 后面黑屏  → 结尾用酒馆画面收尾，不放黑场
  5. 音画不同步 → 放王晰时用的是**原片自己的音轨**，同一个文件、同一起点
  6. 结构混乱 → 五段固定：听 → 停 → 说 → 再听 → 收尾
"""
from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = Path(r"E:\wx\论文素材_王晰作传")
CLIP = sorted((BASE / "现场录音-补充").glob("BV1Qm42177HY_*想游泳的星*.mp4"))[0]
BG = BASE / "场景_酒馆_手绘v4.png"
CHAR = BASE / "blender_out3" / "f_0001.png"
OUT = BASE / "大肥鱼评王晰_修正版.mp4"
FPS = 25
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="fix_"))

SEG = 6.09
AT = 99.3
T1, T2, T3, T4, T5 = 2.0, SEG, 4.9, SEG, 2.0
TOTAL = T1 + T2 + T3 + T4 + T5
T0_CLIP1 = T1
T0_TALK = T1 + T2
T0_CLIP2 = T0_TALK + T3
T0_END = T0_CLIP2 + T4

LINE = "一口气，六点一秒，中间没有换气。"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stderr or "")


def main() -> int:
    # ① 配音（与字幕、读秒同一个数）
    async def go():
        await edge_tts.Communicate(LINE, "zh-CN-XiaoyiNeural", rate="+4%", pitch="+26Hz").save(str(tmp / "t.mp3"))
    asyncio.run(go())
    mkv = tmp / "t.wav"
    run([ff, "-y", "-i", str(tmp / "t.mp3"), "-ar", "44100", "-ac", "2", str(mkv)])

    # ② 字幕
    def ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%d:%02d:%05.2f" % (h, m, s)
    cues = [(0.2, T1 - 0.1, "先听一句"),
            (T0_CLIP1 + 0.2, T0_TALK - 0.2, "《想游泳的星》· 一口气 6.1 秒"),
            (T0_TALK + 0.2, T0_CLIP2 - 0.2, "一口气，6.1 秒，中间没有换气"),
            (T0_CLIP2 + 0.2, T0_END - 0.2, "同一段，再听一遍"),
            (T0_END + 0.2, TOTAL - 0.2, "低音的稳，是气不断")]
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

    # ③ 读秒帧（只覆盖总长，窗口内显示）
    fnt = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 56)
    for i in range(int(TOTAL * FPS)):
        t = i / FPS
        im = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for base in (T0_CLIP1, T0_CLIP2):
            if base <= t <= base + SEG:
                sec = t - base
                d.rounded_rectangle([60, 1600, 720, 1730], radius=18, fill=(9, 13, 17, 180))
                d.text((90, 1610), "%.1f 秒" % sec, font=fnt, fill=(150, 225, 255))
                d.rounded_rectangle([350, 1660, 670, 1694], radius=16, fill=(30, 40, 52, 220))
                d.rounded_rectangle([350, 1660, 350 + int(320 * sec / SEG), 1694],
                                    radius=16, fill=(106, 208, 255, 240))
                d.text((700, 1612), "A3 · 220.6Hz", font=ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 34),
                       fill=(255, 210, 160))
        im.save(tmp / ("tm_%04d.png" % i))

    # ④ 视频：五段，全部 1080x1920 / 25fps / yuv420p
    # 关键：原片不裁脸——按宽度缩到 1080，上下用「自身模糊放大」铺满
    v = tmp / "v.mp4"
    filt = (
        # 段1 开场
        "[0:v]split=3[b0][b1][b2];"
        "[b0]scale=1080:1920,fps=%d[c0];"
        "[1:v]split=2[ch0][ch1];"
        "[ch0]format=rgba,scale=420:548[ch];[c0][ch]overlay=330:980:format=auto[s1];"
        # 原片：模糊底 + 完整画面
        "[2:v]split=2[ca][cb];"
        "[ca]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:2,eq=brightness=-0.12[cbg];"
        "[cb]scale=1080:-1[cfg];"
        "[cbg][cfg]overlay=(W-w)/2:(H-h)/2:format=auto[cf0];"
        "[cf0]split=2[cfa][cfb];"
        "[cfa]trim=start=0:end=%.3f,setpts=PTS-STARTPTS,fps=%d[s2];"
        "[cfb]trim=start=0:end=%.3f,setpts=PTS-STARTPTS,fps=%d[s4];"
        # 段3 说
        "[b1]scale=1080:1920,fps=%d[c1];[ch1]format=rgba,scale=420:548[ch2];"
        "[c1][ch2]overlay=330:980:format=auto[s3];"
        # 段5 收尾
        "[b2]scale=1080:1920,fps=%d[c2];[1:v]format=rgba,scale=380:496[ch3];"
        "[c2][ch3]overlay=350:1010:format=auto[s5];"
        # 读秒叠在两段原片上
        "[3:v]split=2[t1][t2];[t1]format=rgba[tm1];[s2][tm1]overlay=0:0:format=auto[s2b];"
        "[t2]format=rgba[tm2];[s4][tm2]overlay=0:0:format=auto[s4b];"
        "[s1][s2b][s3][s4b][s5]concat=n=5:v=1:a=0[vc];"
        "[vc]ass='%s',format=yuv420p[vout]"
        % (FPS, SEG, FPS, SEG, FPS, FPS, FPS,
           str(ass).replace("\\", "/").replace(":", "\\:"))
    )
    rc, err = run([ff, "-y",
                   "-loop", "1", "-t", str(TOTAL), "-i", str(BG),
                   "-framerate", str(FPS), "-loop", "1", "-t", str(TOTAL), "-i", str(CHAR),
                   "-ss", str(AT), "-t", str(SEG), "-i", str(CLIP),
                   "-framerate", str(FPS), "-t", str(TOTAL), "-i", str(tmp / "tm_%04d.png"),
                   "-filter_complex", filt, "-map", "[vout]",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                   "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0", "-an", str(v)])
    if rc != 0:
        print("视频失败:", err[-800:]); return 4
    print("[1/3] 视频 OK")

    # ⑤ 音频：原片两段（自身音轨，天然同步）+ 中间配音
    n = int(TOTAL * 44100)
    buf = np.zeros((n, 2), dtype=np.float32)

    def put(x, at):
        i0 = int(at * 44100); i1 = min(n, i0 + len(x))
        if i1 > i0:
            buf[i0:i1] += x[: i1 - i0]

    seg = subprocess.run([ff, "-v", "error", "-ss", str(AT), "-t", str(SEG), "-i", str(CLIP),
                          "-f", "f32le", "-ac", "2", "-ar", "44100", "-"], capture_output=True).stdout
    seg = np.frombuffer(seg, dtype=np.float32).reshape(-1, 2)
    put(seg, T0_CLIP1)
    put(seg, T0_CLIP2)
    talk = subprocess.run([ff, "-v", "error", "-i", str(mkv), "-f", "f32le", "-ac", "2", "-ar", "44100", "-"],
                          capture_output=True).stdout
    put(np.frombuffer(talk, dtype=np.float32).reshape(-1, 2), T0_TALK + 0.3)

    peak = float(np.abs(buf).max()) or 1.0
    buf = buf / peak * 0.9
    import wave
    wav = tmp / "mix.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())

    rc, err = run([ff, "-y", "-i", str(v), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0",
                   "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                   "-movflags", "+faststart", "-shortest", str(OUT)])
    if rc != 0:
        print("合流失败:", err[-500:]); return 4
    rc, dec = run([ff, "-v", "error", "-i", str(OUT), "-f", "null", "-"])
    _, info = run([ff, "-i", str(OUT)])
    print("[2/3] 合并 OK")
    print("[3/3]", OUT, round(OUT.stat().st_size / 1024 / 1024, 2), "MB", "| 解码:", (dec or "无错误")[:80])
    print([l.strip()[:95] for l in info.splitlines() if "Stream #" in l or "Duration" in l])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
