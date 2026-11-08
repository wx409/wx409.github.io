#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键：TTS → 包络 → Blender(绑定+眨眼+点头+发摆) → 合成 15 秒样片。

结构（15 秒）
  0–2.5s   标题
  2.5–8.5s 听：想游泳的星 14.8s 长音的前 6 秒
  8.5–13s  说：TTS 两句话（嘴型按真实包络）
  13–15s   再听：回到原音
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg
import numpy as np

BASE = Path(r"E:\wx\论文素材_王晰作传")
LAYERS = BASE / "layers"
BG = BASE / "_bg_bar_v6.png"
SEQ_DIR = BASE / "blender_out4"
SING = BASE / "_staging_现场" / "s36_20240406" / "12 想游泳的星.wav"
OUT = BASE / "样片_v8_15s.mp4"
BLENDER = r"D:\Blender 5.1\blender.exe"
FPS = 25
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="v8_"))

VOICE = "zh-CN-YunjianNeural"
LINES = ["这一口气，十四点八秒，中间没有换气。",
         "他的嗓音像件乐器——颤音速率十年没变过。"]

T_TITLE = 2.5
T_SING1 = 6.0
T_TALK = 4.5
T_SING2 = 2.0
TOTAL = T_TITLE + T_SING1 + T_TALK + T_SING2


def main() -> int:
    # 1) TTS
    async def go():
        for i, t in enumerate(LINES):
            await edge_tts.Communicate(t, VOICE, rate="+0%").save(str(tmp / ("t%d.mp3" % i)))
    asyncio.run(go())
    talk = tmp / "talk.wav"
    subprocess.run([ff, "-y", "-i", str(tmp / "t0.mp3"), "-i", str(tmp / "t1.mp3"),
                    "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1",
                    "-ar", "8000", "-ac", "1", str(talk)], capture_output=True)
    raw = subprocess.run([ff, "-i", str(talk), "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    hop = int(8000 / FPS)
    n_talk = max(1, int(T_TALK * FPS))
    env = []
    for i in range(n_talk):
        seg = a[i * hop:(i + 1) * hop]
        env.append(float(np.abs(seg).mean()) if len(seg) else 0.0)
    mx = max(env) or 1.0
    env = [min(1.0, v / mx) for v in env]
    total_frames = int(TOTAL * FPS)
    talk_start = int((T_TITLE + T_SING1) * FPS)
    payload = {"fps": FPS, "frames": total_frames, "talk_start": talk_start,
               "talk_frames": n_talk, "values": env}
    envp = tmp / "env.json"
    envp.write_text(json.dumps(payload), encoding="utf-8")
    print("[tts] 解说 %d 帧，嘴型峰值 %.2f" % (n_talk, max(env)))

    # 2) Blender
    r = subprocess.run([BLENDER, "-b", "--factory-startup",
                        "--python", r"D:\wx409.github.io\project_b\blender_rig3.py",
                        "--", str(envp), str(SEQ_DIR), str(total_frames)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if "RIG3_DONE" not in (r.stdout or "") + (r.stderr or ""):
        print((r.stdout or "")[-400:], (r.stderr or "")[-800:])
        return 4
    print("[blender] 序列完成:", total_frames)

    # 3) 合成
    srt = tmp / "s.srt"

    def ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%02d:%02d:%06.3f" % (h, m, s)
    cues = [(0.2, T_TITLE - 0.2, "《想游泳的星》· 四巡上海"),
            (T_TITLE, T_TITLE + T_SING1 - 0.2, "一口气 14.8 秒"),
            (T_TITLE + T_SING1, T_TITLE + T_SING1 + T_TALK - 0.2, "中间没有换气，嗓音像件乐器"),
            (T_TITLE + T_SING1 + T_TALK, TOTAL - 0.2, "颤音速率十年没变过")]
    body = ["1"]
    lines = []
    for i, (s, e, t) in enumerate(cues, 1):
        lines += [str(i), "%s --> %s" % (ts(s), ts(e)), t, ""]
    srt.write_text("\n".join(lines), encoding="utf-8")

    filt = (
        "[0:v]scale=1080:1920,fps=%d[bg];"
        "[1:v]format=rgba[ch];"
        "[bg][ch]overlay=0:0:format=auto[v1];"
        "[v1]subtitles='%s':force_style='FontName=Microsoft YaHei,Fontsize=20,"
        "PrimaryColour=&H00D8EAF5,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=240',"
        "format=yuv420p[v]"
        % (FPS, str(srt).replace("\\", "/").replace(":", "\\:"))
    )
    filt_a = (
        "[3:a]atrim=0:%.2f,asetpts=PTS-STARTPTS,adelay=%d|%d[sa];"
        "[4:a]adelay=%d|%d,volume=1.4[tk];"
        "[5:a]atrim=0:%.2f,asetpts=PTS-STARTPTS,adelay=%d|%d[sb];"
        "[sa][tk][sb]amix=inputs=3:normalize=0:duration=longest[a]"
        % (T_SING1, int(T_TITLE * 1000), int(T_TITLE * 1000),
           int((T_TITLE + T_SING1) * 1000), int((T_TITLE + T_SING1) * 1000),
           T_SING2, int((T_TITLE + T_SING1 + T_TALK) * 1000), int((T_TITLE + T_SING1 + T_TALK) * 1000))
    )
    cmd = [ff, "-y",
           "-loop", "1", "-t", str(TOTAL), "-i", str(BG),
           "-framerate", str(FPS), "-t", str(TOTAL), "-i", str(SEQ_DIR / "f_%04d.png"),
           "-ss", "233.7", "-t", str(T_SING1), "-i", str(SING),
           "-i", str(tmp / "talk.mp3"),
           "-ss", "233.7", "-t", str(T_SING2), "-i", str(SING),
           "-filter_complex", filt + ";" + filt_a,
           "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-t", str(TOTAL), str(OUT)]
    print("[render] 合成 %.1fs…" % TOTAL)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print((r.stderr or "")[-700:]); return 4
    print("[done]", OUT, "%.1f MB" % (OUT.stat().st_size / 1024 / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
