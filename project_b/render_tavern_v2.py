# -*- coding: utf-8 -*-
"""v2 渲染：让「静态立绘 + 纯音频」变成「有动作 + 看得见声音」。

新增三样
  1. 角色微动：上下呼吸浮动 + 极轻旋转（ffmpeg overlay 表达式，按 t 驱动）
  2. 声音可视：底部 showwaves 波形（把音频变成画面）
  3. F0 曲线逐帧生长：PIL 预渲染一组 PNG，叠加在数据面板里，随原音推进

用法
  python project_b\render_tavern_v2.py --json 脚本.json --out demo.mp4 --preview 6
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw

BASE = Path(r"E:\wx\论文素材_王晰作传")
BG = BASE / "_bg_clean.png"
CHAR = BASE / "_char_front_v3.png"
FONT_DIR = r"C:\Windows\Fonts\msyhbd.ttc"

CHAR_W = 629
CHAR_H = 820
CHAR_X = 1080 - 170 - CHAR_W
CHAR_Y = 1920 - 545 - CHAR_H + 60

# 数据面板内区域（与设计稿一致：left 64, top 286, w 500, h 256）
PANEL = (64, 286, 500, 256)
CURVE_BOX = (76, 286 + 52, 476, 172)   # 曲线绘制区

FPS = 25


def make_curve_frames(n: int, total: float, tmp: Path) -> list[Path]:
    """生成 n 帧 PNG：F0 曲线从左到右生长。"""
    out = []
    # 一条“更像人声”的曲线：先平稳，后下探
    pts = []
    w = CURVE_BOX[2]
    for i in range(w):
        x = i / w
        if x < 0.62:
            y = 0.22 + 0.03 * math.sin(x * 18)
        else:
            k = (x - 0.62) / 0.38
            y = 0.22 + 0.62 * (k ** 0.8) + 0.01 * math.sin(k * 30)
        pts.append(y)
    for f in range(n):
        img = Image.new("RGBA", (CURVE_BOX[2], CURVE_BOX[3]), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        upto = int(CURVE_BOX[2] * min(1.0, (f + 1) / max(1, n - 1) * 1.0))
        line = [(i, int(pts[i] * CURVE_BOX[3])) for i in range(upto)]
        if len(line) > 1:
            d.line(line, fill=(106, 208, 255, 255), width=3)
            d.ellipse([line[-1][0] - 5, line[-1][1] - 5, line[-1][0] + 5, line[-1][1] + 5],
                      fill=(150, 225, 255, 255))
        p = tmp / ("curve_%04d.png" % f)
        img.save(p)
        out.append(p)
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--audio", default=str(BASE / "音域分析" / "专辑音频" / "重游往昔" / "静止了的夜晚.mp3"))
    ap.add_argument("--audio-start", type=float, default=188.0)
    ap.add_argument("--preview", type=float, default=6.0)
    args = ap.parse_args()

    d = json.loads(Path(args.json).read_text(encoding="utf-8"))
    dur = min(float(d.get("duration") or 40), args.preview)
    n_frames = int(dur * FPS)

    tmp = Path(tempfile.mkdtemp(prefix="tavern_v2_"))
    frames = make_curve_frames(n_frames, dur, tmp)

    ff = imageio_ffmpeg.get_ffmpeg_exe()

    # 字幕
    def st(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%02d:%02d:%06.3f" % (h, m, s)
    srt, i = [], 1
    for b in d["beats"]:
        t0, t1 = float(b["t"]), float(b["t"]) + float(b["dur"])
        if t0 >= dur:
            continue
        srt += [str(i), "%s --> %s" % (st(t0), st(min(t1, dur))),
                (b.get("caption") or b.get("line") or ""), ""]
        i += 1
    srt_p = tmp / "sub.srt"
    srt_p.write_text("\n".join(srt), encoding="utf-8")

    # 输入：0 背景 / 1 角色 / 2 曲线序列 / 3 音频
    cmd = [ff, "-y",
           "-loop", "1", "-t", str(dur), "-i", str(BG),
           "-loop", "1", "-t", str(dur), "-i", str(CHAR),
           "-framerate", str(FPS), "-t", str(dur), "-i", str(tmp / "curve_%04d.png"),
           "-ss", str(args.audio_start), "-t", str(dur), "-i", str(args.audio)]

    # 角色微动：呼吸浮动 6px + 旋转 0.6°
    bob = "6*sin(2*PI*t/3.4)"
    rot = "0.6*sin(2*PI*t/6.8)"
    filt = (
        "[0:v]scale=1080:1920[bg];"
        "[1:v]format=rgba,scale=%d:%d,rotate='%s*PI/180':c=none:ow=rotw(iw):oh=roth(ih)[ch];"
        "[bg][ch]overlay=x=%d:y='%d+%s':format=auto[v1];"
        "[v1][2:v]overlay=x=%d:y=%d:format=auto[v2];"
        "[3:a]showwaves=s=1080x160:mode=cline:colors=0x6ad0ff@0.85:rate=%d[w];"
        "[v2][w]overlay=x=0:y=1560:format=auto[v3];"
        "[v3]subtitles='%s':force_style='FontName=Microsoft YaHei,Fontsize=22,"
        "PrimaryColour=&H00D8EAF5,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=60',"
        "format=yuv420p[vout]"
        % (CHAR_W, CHAR_H, rot, CHAR_X, CHAR_Y, bob,
           CURVE_BOX[0], CURVE_BOX[1],
           FPS, str(srt_p).replace("\\", "/").replace(":", "\\:"))
    )

    cmd += ["-filter_complex", filt, "-map", "[vout]", "-map", "3:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-shortest", args.out]

    print("渲染 v2（%d 帧）…" % n_frames)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("失败：", (r.stderr or "")[-700:])
        return 4
    p = Path(args.out)
    print("完成：", p, "%.1f MB" % (p.stat().st_size / 1024 / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
