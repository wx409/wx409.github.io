#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交付「主画面模板」：背景 + 大肥鱼 + 字幕 + 预留画中画位，并导出剪映可用的素材。

产出（都在 E:\\wx\\论文素材_王晰作传\\剪映素材\\）
  main_preview.mp4    预览（含「王晰片段放这里」占位框），可直接看排版
  char_alpha.mov      大肥鱼带透明通道（ProRes 4444），剪映里放主画面上层
  bg_tavern.png       背景图 1080×1920
  subtitles.srt       字幕（时间轴与预览一致）
  README.txt          剪映操作步骤
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

BASE = Path(r"E:\wx\论文素材_王晰作传")
OUTD = BASE / "剪映素材"
OUTD.mkdir(exist_ok=True)
BG = BASE / "场景_酒馆_手绘v4.png"
SEQ = BASE / "blender_out3" / "f_%04d.png"
FPS = 25
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="jY_"))

# 画中画区域（预留）：1080 宽画布里的 16:9 安全区
PIP = (60, 300, 1020, 840)          # x0,y0,x1,y1  960×540

TOTAL = 16.0
T1, T2 = 0.0, 4.0                   # 4s 开场
T3 = T2 + 6.0                       # 6s 放片段（占位）
T4 = T3 + 4.0                       # 4s 点评
T5 = TOTAL                          # 2s 收尾

fnt_big = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 54)
fnt_mid = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 40)


def main() -> int:
    # ① 占位框图层（只是预览用）
    ph = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    d = ImageDraw.Draw(ph)
    d.rounded_rectangle(PIP, radius=22, fill=(10, 14, 18, 165), outline=(106, 208, 255, 170), width=3)
    d.text((PIP[0] + 40, PIP[1] + 210), "王晰演唱片段", font=fnt_big, fill=(150, 225, 255))
    d.text((PIP[0] + 40, PIP[1] + 290), "（这里留给你放）", font=fnt_mid, fill=(200, 210, 220))
    ph.save(tmp / "pip.png")

    # ② 预览视频：背景 + 角色 + 占位框 + 字幕
    srt = OUTD / "subtitles.srt"

    def ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%02d:%02d:%06.3f" % (h, m, s)
    cues = [(0.3, 3.7, "先听一个音"),
            (4.0, 9.7, "【这里放王晰的演唱片段】"),
            (10.0, 13.7, "一个音，六点一秒，中间没有换气"),
            (14.0, 15.8, "低音的稳，是气不断")]
    lines = []
    for i, (a, b, t) in enumerate(cues, 1):
        lines += [str(i), "%s --> %s" % (ts(a), ts(b)), t, ""]
    srt.write_text("\n".join(lines), encoding="utf-8")

    filt = (
        "[0:v]scale=1080:1920,fps=%d[bg];"
        "[1:v]format=rgba,scale=520:680[ch];[bg][ch]overlay=280:900:format=auto[b1];"
        "[2:v]format=rgba[ph];[b1][ph]overlay=0:0:format=auto[b2];"
        "[b2]subtitles='%s':force_style='FontName=Microsoft YaHei,Fontsize=20,"
        "PrimaryColour=&H00D8EAF5,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=220',"
        "format=yuv420p[v]"
        % (FPS, str(srt).replace("\\", "/").replace(":", "\\:"))
    )
    rc = subprocess.run([ff, "-y",
                         "-loop", "1", "-t", str(TOTAL), "-i", str(BG),
                         "-framerate", str(FPS), "-stream_loop", "-1", "-t", str(TOTAL), "-i", str(SEQ),
                         "-loop", "1", "-t", str(TOTAL), "-i", str(tmp / "pip.png"),
                         "-filter_complex", filt, "-map", "[v]",
                         "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                         "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
                         "-an", str(OUTD / "main_preview.mp4")],
                        capture_output=True, text=True, errors="replace")
    if rc.returncode != 0:
        print("预览失败:", rc.stderr[-500:]); return 4
    print("[1/4] main_preview.mp4 OK")

    # ③ 角色透明视频（剪映可叠加）
    rc = subprocess.run([ff, "-y", "-framerate", str(FPS), "-stream_loop", "-1", "-t", "8",
                         "-i", str(SEQ), "-c:v", "prores_ks", "-profile:v", "4444",
                         "-pix_fmt", "yuva444p10le", "-vendor", "apl0", str(OUTD / "char_alpha.mov")],
                        capture_output=True, text=True, errors="replace")
    print("[2/4] char_alpha.mov", "OK" if rc.returncode == 0 else rc.stderr[-300:])

    # ④ 背景图 + 说明
    Image.open(BG).convert("RGB").resize((1080, 1920)).save(OUTD / "bg_tavern.png")
    (OUTD / "README.txt").write_text(
        "剪映专业版操作步骤\n"
        "1) 新建 1080×1920 竖屏项目\n"
        "2) 导入 bg_tavern.png 放主轨道，铺满 16 秒\n"
        "3) 导入 char_alpha.mov 放上层，位置 (280,900)、尺寸 520×680，铺满 16 秒\n"
        "4) 导入你的王晰片段，放到预留区：位置 (60,300)、尺寸 960×540，时间 4.0–10.0 秒\n"
        "5) 导入 subtitles.srt，检查字号/描边\n"
        "6) 配音：可先用我给的 TTS，或你自己录\n",
        encoding="utf-8")
    print("[3/4] 素材 OK")
    print("[4/4] 输出目录:", OUTD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
