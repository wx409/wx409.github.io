#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""酒馆短片 · 最小渲染器（MVP）：脚本 JSON → 草稿 mp4。

能力边界（第一版只说做了什么）
  ✅ 背景 + 角色立绘 + 字幕 + 原音片段 + 饭盆纵向位移（按 beat 的 basin）
  ⬜ 表情切换（expr 字段先留位，需要多张表情立绘才能切）
  ⬜ 口型同步

素材
  E:\\wx\\论文素材_王晰作传\\_bg_clean.png       背景 1080×1920
  E:\\wx\\论文素材_王晰作传\\_char_front_v3.png 角色（透明底）
  E:\\wx\\论文素材_王晰作传\\_basin.png         饭盆（透明底，没有就先跳过）

用法
  python -X utf8 project_b\\render_tavern_short.py --json "脚本.json" --out draft.mp4 --preview 10
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg

BASE = Path(r"E:\wx\论文素材_王晰作传")
BG = BASE / "_bg_clean.png"
CHAR = BASE / "_char_front_v3.png"
BASIN = BASE / "_basin.png"
FONT = r"C:\Windows\Fonts\msyhbd.ttc"

# 角色/饭盆在 1080×1920 画布上的位置（与设计稿一致）
CHAR_X, CHAR_Y = 1080 - 170 - 629, 1920 - 545 - 820 + 60
BASIN_X, BASIN_Y = 120, 1920 - 566 - 96
BASIN_SHIFT = {"idle": 0, "sink": 14, "rise": -46, "align": -10, "head": -300}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def esc_text(s: str) -> str:
    return (s.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
             .replace(",", "\\,").replace("%", "\\%"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--out", default=str(BASE / "草稿_酒馆_40s.mp4"))
    ap.add_argument("--audio", default=str(BASE / "音域分析" / "专辑音频" / "重游往昔" / "静止了的夜晚.mp3"),
                    help="草稿用的临时音源（正式版应改用 B 站片段，避免版权问题）")
    ap.add_argument("--audio-start", type=float, default=188.0, help="原音起点（秒）")
    ap.add_argument("--preview", type=float, default=0, help="只渲染前 N 秒")
    args = ap.parse_args()

    d = json.loads(Path(args.json).read_text(encoding="utf-8"))
    dur = float(d.get("duration") or 40)
    if args.preview:
        dur = min(dur, args.preview)

    if not BG.exists() or not CHAR.exists():
        print("缺少素材：", BG if not BG.exists() else CHAR)
        return 3

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    inputs = ["-loop", "1", "-t", str(dur), "-i", str(BG),
              "-loop", "1", "-t", str(dur), "-i", str(CHAR)]
    has_basin = BASIN.exists()
    if has_basin:
        inputs += ["-loop", "1", "-t", str(dur), "-i", str(BASIN)]

    # 饭盆纵向位移：按 beat 的 basin 生成阶梯函数（覆盖整段时长）
    def basin_expr() -> str:
        pts = []
        for b in d["beats"]:
            key = b.get("basin") or "idle"
            pts.append((float(b["t"]), BASIN_SHIFT.get(key, 0)))
        pts.sort()
        expr = "%d" % pts[-1][1]
        for t, v in reversed(pts):
            expr = "if(gte(t,%.2f),%d,%s)" % (t, v, expr)
        return expr

    # 字幕：写 SRT，交给 subtitles 滤镜烧（避免 drawtext 转义地狱）
    def srt_time(x: float) -> str:
        h = int(x // 3600); m = int((x % 3600) // 60); sec = x % 60
        return "%02d:%02d:%06.3f" % (h, m, sec)

    srt_lines, idx = [], 1
    for b in d["beats"]:
        t0, t1 = float(b["t"]), float(b["t"]) + float(b["dur"])
        if t0 >= dur:
            continue
        text = (b.get("caption") or b.get("line") or "").replace("\n", "\n")
        if not text:
            continue
        srt_lines += [str(idx), "%s --> %s" % (srt_time(t0), srt_time(min(t1, dur))), text, ""]
        idx += 1
    srt_path = Path(tempfile.gettempdir()) / "tavern_sub.srt"
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")
    subs = ("subtitles='%s':force_style='FontName=Microsoft YaHei,Fontsize=22,"
            "PrimaryColour=&H00D8EAF5,BorderStyle=1,Outline=4,Shadow=0,"
            "Alignment=2,MarginV=60'" % str(srt_path).replace("\\", "/").replace(":", "\\:"))

    chain = "[0:v][1:v]overlay=%d:%d:format=auto[v1]" % (CHAR_X, CHAR_Y)
    if has_basin:
        chain += ";[v1][2:v]overlay=%d:'%d+%s':format=auto[v2]" % (BASIN_X, BASIN_Y, basin_expr())
        last = "[v2]"
    else:
        last = "[v1]"
    chain += ";%sscale=1080:1920,setpts=PTS-STARTPTS,%s,format=yuv420p[vout]" % (last, subs)

    cmd = [ffmpeg, "-y"] + inputs + [
        "-ss", str(args.audio_start), "-t", str(dur), "-i", str(args.audio),
        "-filter_complex", chain,
        "-map", "[vout]", "-map", ("3:a" if has_basin else "2:a"),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "160k", "-shortest", str(args.out)]

    print("渲染中…", "（预览 %.0fs）" % dur if args.preview else "（全片 %.0fs）" % dur)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("ffmpeg 失败：", (r.stderr or "")[-800:])
        return 4
    p = Path(args.out)
    print("完成：", p, "%.1f MB" % (p.stat().st_size / 1024 / 1024))
    print("⚠ 草稿用的是本地录音室音源，仅供看节奏；对外发布必须换成 B 站引用片段。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
