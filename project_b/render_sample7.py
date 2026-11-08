#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""样片 v7：老师原声背书 + 我们的数据 + 会眨眼/会说话的立绘。

结构（约 34 秒）
  0–3s    标题：《想游泳的星》· 四巡上海 2024-04-06
  3–10s   老师原声（主歌/预副歌/副歌都有）——第三方背书，画面是她安静听
  10–25s  放 14.8 秒长音（原声），右下角秒数计时，她安静听
  25–33s  我们的话（TTS）：“嗓音像个乐器，颤音速率十年没变过，5.12 赫兹”——她开口说
  33–34s  收尾
"""
from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter

BASE = Path(r"E:\wx\论文素材_王晰作传")
BG = BASE / "_bg_bar_v6.png"
SEQ = BASE / "blender_out3" / "f_%04d.png"     # 6 秒，带眨眼/点头
NEUTRAL = BASE / "blender_out3" / "f_0001.png"  # 静止（闭嘴）帧
SING = BASE / "_staging_现场" / "s36_20240406" / "12 想游泳的星.wav"
TEACH = BASE / "剪辑素材" / "ref_long_merged.mp4"
OUT = BASE / "样片_v7_背书版.mp4"
FPS = 25
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="s7_"))

T_TITLE = 3.0
T_TEACH = 7.0
T_SING = 15.0
T_TALK = 9.0
T_END = 2.0
T0_TEACH = T_TITLE
T0_SING = T0_TEACH + T_TEACH
T0_TALK = T0_SING + T_SING
T0_END = T0_TALK + T_TALK
TOTAL = T0_END + T_END

VOICE = "zh-CN-YunjianNeural"
TALK_LINE = "他的嗓音，真的像个乐器。颤音速率十年没变过，五点一二赫兹。"


def tts(path: Path) -> None:
    async def go():
        await edge_tts.Communicate(TALK_LINE, VOICE, rate="+0%").save(str(path))
    asyncio.run(go())


def ass() -> Path:
    def ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%d:%02d:%05.2f" % (h, m, s)
    body = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: D,Microsoft YaHei,40,&H00D8EAF5,&H00000000,&H00000000,-1,1,4,0,2,60,60,230,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    cues = [
        (0.3, T_TITLE - 0.2, "《想游泳的星》· 四巡上海 2024-04-06"),
        (T0_TEACH + 0.2, T0_SING - 0.2, "“主歌也有，预副歌也有，副歌也有。”"),
        (T0_SING + 0.2, T0_TALK - 0.3, "一口气 14.8 秒，不换气"),
        (T0_TALK + 0.2, T0_END - 0.2, "“嗓音像个乐器，颤音速率十年没变”"),
        (T0_END + 0.2, TOTAL - 0.2, "低音的稳，是气不断"),
    ]
    for a, b, t in cues:
        body += "Dialogue: 0,%s,%s,D,,0,0,0,,%s\n" % (ts(a), ts(b), t)
    p = tmp / "s.ass"
    p.write_text(body, encoding="utf-8")
    return p


def main() -> int:
    tts(tmp / "talk.mp3")
    a = ass()

    # 音频：老师原声(443.0–450.0) + 长音(3:53.7,15s) + TTS
    filt_v = (
        "[0:v]scale=1080:1920,fps=%d[bg];"
        "[3:v]format=rgba[neu];"
        "[bg][neu]overlay=0:0:format=auto[b1];"
        "[4:v]format=rgba[seq];"
        "[b1][seq]overlay=0:0:enable='between(t,%.2f,%.2f)':format=auto[b2];"
        "[b2]ass='%s',format=yuv420p[v]"
        % (FPS, T0_TALK, T0_TALK + 6.0, str(a).replace("\\", "/").replace(":", "\\:"))
    )
    filt_a = (
        "[5:a]atrim=443.0:450.0,asetpts=PTS-STARTPTS,adelay=%d|%d,volume=1.4[ta];"
        "[6:a]atrim=0:%.2f,asetpts=PTS-STARTPTS,adelay=%d|%d[sa];"
        "[7:a]adelay=%d|%d,volume=1.5[tk];"
        "[ta][sa][tk]amix=inputs=3:normalize=0:duration=longest[aout]"
        % (int(T0_TEACH * 1000), int(T0_TEACH * 1000),
           T_SING, int(T0_SING * 1000), int(T0_SING * 1000),
           int(T0_TALK * 1000), int(T0_TALK * 1000))
    )
    cmd = [ff, "-y",
           "-loop", "1", "-t", str(TOTAL), "-i", str(BG),                 # 0
           "-i", str(TEACH),                                              # 1（老师原声源）
           "-ss", "233.7", "-t", str(T_SING), "-i", str(SING),            # 2
           "-loop", "1", "-t", str(TOTAL), "-i", str(NEUTRAL),            # 3
           "-framerate", str(FPS), "-t", str(TOTAL), "-stream_loop", "-1", "-i", str(SEQ),  # 4
           "-i", str(TEACH),                                              # 5
           "-ss", "0", "-t", str(T_SING), "-i", str(SING),                # 6
           "-i", str(tmp / "talk.mp3"),                                   # 7
           "-filter_complex", filt_v + ";" + filt_a,
           "-map", "[v]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-t", str(TOTAL), str(OUT)]
    print("[render] 合成 v7（%.1fs）…" % TOTAL)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print((r.stderr or "")[-900:]); return 4
    print("[done]", OUT, "%.1f MB" % (OUT.stat().st_size / 1024 / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
