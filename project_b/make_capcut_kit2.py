#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付包 v2：眼睛不再闪（去掉眨眼）+ 带配音的预览 + 单独配音文件。

改动
  · Blender 序列：关掉眨眼（上一版眼睛忽有忽无的根因），保留点头/嘴动/呼吸
  · 预览视频：加 TTS 配音（三段），导出 mp4 带声音
  · 另给 char_alpha.mov（透明）、voiceover.wav（剪映里可替换）
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = Path(r"E:\wx\论文素材_王晰作传")
OUTD = BASE / "剪映素材"
OUTD.mkdir(exist_ok=True)
BG = BASE / "场景_酒馆_手绘v4.png"
BLENDER = r"D:\Blender 5.1\blender.exe"
RIG = r"D:\wx409.github.io\project_b\blender_rig3.py"
FPS = 25
TOTAL = 16.0
PIP = (60, 300, 1020, 840)
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="kit2_"))

LINES = [("先听一个音。", 0.6),
         ("一个音，六点一秒，中间没有换气。", 10.3),
         ("低音的稳，是气不断。", 14.2)]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stderr or "")


def main() -> int:
    # ① 配音
    async def go():
        for i, (t, _) in enumerate(LINES):
            await edge_tts.Communicate(t, "zh-CN-XiaoyiNeural", rate="+4%", pitch="+26Hz").save(str(tmp / ("v%d.mp3" % i)))
    asyncio.run(go())

    # ② Blender：关眨眼，渲 16 秒
    env = {"fps": FPS, "frames": int(TOTAL * FPS), "talk_start": int(10.3 * FPS),
           "talk_frames": 90, "values": [abs(np.sin(i / 8)) * 0.8 for i in range(90)], "blink": False}
    (tmp / "env.json").write_text(json.dumps(env), encoding="utf-8")
    seq = tmp / "seq"
    rc, err = run([BLENDER, "-b", "--factory-startup", "--python", RIG, "--",
                   str(tmp / "env.json"), str(seq), str(int(TOTAL * FPS))])
    if "RIG3_DONE" not in err:
        print("Blender 失败:", err[-500:]); return 4
    print("[1/4] Blender 序列 OK（无眨眼）")

    # ③ 音轨：numpy 拼接（配音三段，落在时间点）
    n = int(TOTAL * 44100)
    buf = np.zeros((n, 2), dtype=np.float32)
    for i, (_, at) in enumerate(LINES):
        raw = subprocess.run([ff, "-v", "error", "-i", str(tmp / ("v%d.mp3" % i)),
                              "-f", "f32le", "-ac", "2", "-ar", "44100", "-"], capture_output=True).stdout
        a = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)
        i0 = int(at * 44100); i1 = min(n, i0 + len(a))
        if i1 > i0:
            buf[i0:i1] += a[: i1 - i0]
    peak = float(np.abs(buf).max()) or 1.0
    buf = buf / peak * 0.9
    wav = OUTD / "voiceover.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
        w.writeframes((buf * 32767).astype(np.int16).tobytes())
    print("[2/4] 配音 OK")

    # ④ 预览视频（带配音）
    srt = OUTD / "subtitles.srt"

    def ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%02d:%02d:%06.3f" % (h, m, s)
    cues = [(0.3, 3.7, "先听一个音"),
            (4.0, 9.9, "【这里放王晰的演唱片段】"),
            (10.0, 13.9, "一个音，6.1 秒，中间没有换气"),
            (14.0, 15.8, "低音的稳，是气不断")]
    lines = []
    for i, (a, b, t) in enumerate(cues, 1):
        lines += [str(i), "%s --> %s" % (ts(a), ts(b)), t, ""]
    srt.write_text("\n".join(lines), encoding="utf-8")

    ph = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(ph)
    d.rounded_rectangle(PIP, radius=22, fill=(10, 14, 18, 165), outline=(106, 208, 255, 170), width=3)
    f1 = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 54)
    f2 = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 40)
    d.text((PIP[0] + 40, PIP[1] + 210), "王晰演唱片段", font=f1, fill=(150, 225, 255))
    d.text((PIP[0] + 40, PIP[1] + 290), "（这里留给你放）", font=f2, fill=(200, 210, 220))
    ph.save(tmp / "pip.png")

    filt = (
        "[0:v]scale=1080:1920,fps=%d[bg];"
        "[1:v]format=rgba[ch];[bg][ch]overlay=0:0:format=auto[b1];"
        "[2:v]format=rgba[ph];[b1][ph]overlay=0:0:format=auto[b2];"
        "[b2]subtitles='%s':force_style='FontName=Microsoft YaHei,Fontsize=20,"
        "PrimaryColour=&H00D8EAF5,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=220',"
        "format=yuv420p[v]"
        % (FPS, str(srt).replace("\\", "/").replace(":", "\\:"))
    )
    rc, err = run([ff, "-y",
                   "-loop", "1", "-t", str(TOTAL), "-i", str(BG),
                   "-framerate", str(FPS), "-stream_loop", "-1", "-t", str(TOTAL), "-i", str(seq / "f_%04d.png"),
                   "-loop", "1", "-t", str(TOTAL), "-i", str(tmp / "pip.png"),
                   "-i", str(wav),
                   "-filter_complex", filt, "-map", "[v]", "-map", "3:a",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                   "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
                   "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest",
                   str(OUTD / "main_preview.mp4")])
    if rc != 0:
        print("预览失败:", err[-600:]); return 4
    print("[3/4] main_preview.mp4（带配音）OK")

    # ⑤ 透明角色视频（剪映叠加用）
    rc, err = run([ff, "-y", "-framerate", str(FPS), "-i", str(seq / "f_%04d.png"),
                   "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
                   "-vendor", "apl0", str(OUTD / "char_alpha.mov")])
    print("[4/4] char_alpha.mov", "OK" if rc.returncode == 0 else err[-300:])

    (OUTD / "README.txt").write_text(
        "剪映专业版操作（1080×1920）\n"
        "1) 主轨道：bg_tavern.png（16 秒）\n"
        "2) 上层：char_alpha.mov，位置 (280,900)，尺寸 520×680（透明通道可用）\n"
        "3) 你的王晰片段：位置 (60,300)，尺寸 960×540，时间 4.0–10.0 秒\n"
        "4) 字幕：subtitles.srt\n"
        "5) 配音：voiceover.wav（现已混进 main_preview.mp4；想自己换就导入这个文件替换）\n",
        encoding="utf-8")
    print("目录:", OUTD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
