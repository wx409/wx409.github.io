#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""声学短片流水线（本地全自动）：选片 → 下载 → 取段 → 背景板 → 曲线 → 合成。

一条命令跑完整条链：
  python -X utf8 project_b\\video_pipeline.py ^
     --bv BV1i4411d7MJ --start 199 --dur 8 ^
     --plate-src BV1C8411U7MR --out "E:\\wx\\论文素材_王晰作传\\demo_8s.mp4"

它做四件事
  1) fetch     ：yt-dlp 下 B 站片段（≤1080p，缓存到 剪辑素材\\）
  2) plate     ：用「微醺23点08分」那间酒馆的实拍帧做 1080×1920 背景板（渐变遮罩，无硬边）
  3) curve     ：读真实逐帧 F0（专辑音频_分析\\*.csv），生成随音频生长的曲线帧
  4) render    ：背景 + 鲸鱼娘（微浮动/微旋转）+ 曲线 + 波形 + 字幕 + 署名

设计原则：每一步都可单独跑（--only fetch|plate|curve|render），产物落盘可复用。
"""
from __future__ import annotations

import argparse
import csv
import re
import glob
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = Path(r"E:\wx\论文素材_王晰作传")
CLIPS = BASE / "剪辑素材"
CHAR = BASE / "_char_front_v3.png"
PLATE = BASE / "_bg_bar_v5.png"
F0_CSV = BASE / "音域分析" / "专辑音频_分析" / "重游往昔" / "静止了的夜晚_f0.csv"
FONT = r"C:\Windows\Fonts\msyhbd.ttc"
FPS = 25
CHAR_W, CHAR_H = 629, 860
PANEL = (64, 286, 500, 250)
CURVE_BOX = (84, 342, 460, 150)

ff = imageio_ffmpeg.get_ffmpeg_exe()

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ── 1) 下载 ────────────────────────────────────────────────
def _ffmpeg_alias() -> Path:
    """yt-dlp 只认名为 ffmpeg(.exe) 的二进制；imageio 的是 ffmpeg-win-x86_64-v7.1.exe，
    这里建一个同目录别名，返回该目录。"""
    d = Path(tempfile.gettempdir()) / "ffbin"
    d.mkdir(parents=True, exist_ok=True)
    alias = d / "ffmpeg.exe"
    if not alias.exists():
        try:
            shutil.copy2(ff, alias)
        except Exception:
            pass
    return d


def _probe_has_audio(path: Path) -> bool:
    r = subprocess.run([ff, "-i", str(path)], capture_output=True, text=True, errors="replace")
    return "Audio:" in (r.stderr or "")


def _merge_parts(bv: str) -> Path | None:
    vids = sorted(CLIPS.glob("%s_*.f*.mp4" % bv))
    auds = sorted(CLIPS.glob("%s_*.m4a" % bv))
    if not vids:
        return None
    base = re.sub(r"\.f\d+\.mp4$", "", vids[0].name)
    out = vids[0].with_name(base + "_merged.mp4")
    if out.exists() and _probe_has_audio(out):
        return out
    cmd = [ff, "-y", "-i", str(vids[0])]
    if auds:
        cmd += ["-i", str(auds[0])]
    cmd += ["-c", "copy", "-shortest", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if out.exists() and _probe_has_audio(out):
        print("[fetch] 已合并分轨：", out.name)
        return out
    return None


def fetch(bv: str, height: int = 1080) -> Path:
    CLIPS.mkdir(parents=True, exist_ok=True)
    # 1) 已有「合并且带音轨」的成品？
    for p in sorted(CLIPS.glob("%s_*.mp4" % bv)):
        if "_merged" in p.name and _probe_has_audio(p):
            print("[fetch] 已缓存（合并版）：", p.name)
            return p
    # 2) 已有分轨 → 直接合并
    merged = _merge_parts(bv)
    if merged:
        return merged

    url = "https://www.bilibili.com/video/%s" % bv
    ffdir = str(_ffmpeg_alias())
    cmd = ["yt-dlp", "--no-playlist",
           "--ffmpeg-location", ffdir,
           "-f", "bv*[height<=%d]+ba/b[height<=%d]" % (height, height),
           "--merge-output-format", "mp4",
           "-o", str(CLIPS / ("%s_%%(title).40s.%%(ext)s" % bv)), url]
    print("[fetch] 下载", url)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    for p in sorted(CLIPS.glob("%s_*.mp4" % bv)):
        if _probe_has_audio(p) and ".f" not in p.stem[-6:]:
            return p
    merged = _merge_parts(bv)
    if merged:
        return merged
    raise SystemExit("下载或合并失败：%s" % (r.stderr or "")[-300:])


# ── 2) 背景板 ──────────────────────────────────────────────
def make_plate(src_bv: str, at: float = 146.5) -> Path:
    if PLATE.exists():
        print("[plate] 复用：", PLATE.name)
        return PLATE
    v = fetch(src_bv, 720)
    raw = BASE / "_plate_tmp.png"
    subprocess.run([ff, "-y", "-ss", str(at), "-i", str(v), "-frames:v", "1", str(raw)],
                   capture_output=True)
    im = Image.open(raw).convert("RGB")
    crop = im.crop((0, 34, 600, 690))
    s = 1920 / crop.height
    crop = crop.resize((int(crop.width * s), 1920), Image.LANCZOS).crop((0, 0, 1080, 1920))
    crop = crop.filter(ImageFilter.GaussianBlur(3.6))
    crop = Image.blend(crop, Image.new("RGB", crop.size, (12, 9, 8)), 0.34)

    # 渐变遮罩（顶部盖水印、底部盖原字幕），不再是硬边
    top = Image.linear_gradient("L").resize((1, 320)).rotate(180).resize((1080, 320))
    crop.paste(Image.new("RGB", (1080, 320), (9, 7, 6)), (0, 0), top)
    bot = Image.linear_gradient("L").resize((1, 360)).rotate(180).resize((1080, 360))
    crop.paste(Image.new("RGB", (1080, 360), (9, 7, 6)), (0, 1560), bot)
    # 数据面板底板（半透明深色 + 蓝边）
    ov = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.rounded_rectangle([64, 286, 64 + 500, 286 + 250], radius=14,
                         fill=(9, 13, 17, 165), outline=(106, 208, 255, 120), width=2)
    crop = Image.alpha_composite(crop.convert("RGBA"), ov).convert("RGB")
    crop.save(PLATE)
    print("[plate] 生成：", PLATE.name)
    return PLATE


# ── 3) 真实 F0 曲线帧 ──────────────────────────────────────
def load_f0(path: Path, start: float, dur: float) -> list[tuple[float, float]]:
    out = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                t = float(r["time_s"])
                hz = float(r["f0_hz"])
            except Exception:
                continue
            if start <= t <= start + dur and hz > 0:
                out.append((t, hz))
    return out


def curve_frames(pts: list[tuple[float, float]], start: float, n: int, tmp: Path) -> list[Path]:
    if not pts:
        raise SystemExit("该时间段没有 F0 数据")
    lo, hi = min(h for _, h in pts), max(h for _, h in pts)
    rng = max(hi - lo, 6.0)
    W, H = CURVE_BOX[2], CURVE_BOX[3]
    out = []
    for f in range(n):
        frac = (f + 1) / n
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        cur = [p for p in pts if p[0] <= start + frac * (pts[-1][0] - start)]
        line = [(int((t - start) / max(1e-6, pts[-1][0] - start) * W),
                 int(H - (h - lo) / rng * (H - 12) - 6)) for t, h in cur]
        if len(line) > 1:
            d.line(line, fill=(106, 208, 255, 255), width=3)
            x, y = line[-1]
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(170, 230, 255, 255))
        p = tmp / ("c_%04d.png" % f)
        img.save(p)
        out.append(p)
    return out


# ── 4) 合成 ────────────────────────────────────────────────
def render(video: Path, start: float, dur: float, out: Path, beats: list[dict] | None = None) -> int:
    plate = make_plate("BV1C8411U7MR")
    n = int(dur * FPS)
    tmp = Path(tempfile.mkdtemp(prefix="vpipe_"))
    pts = load_f0(F0_CSV, start, dur)
    frames = curve_frames(pts, start, n, tmp)

    srt = Path(tmp / "s.srt")

    def st(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%02d:%02d:%06.3f" % (h, m, s)

    lines, i = [], 1
    for b in (beats or [{"t": 0, "dur": dur, "caption": "F0 轨迹 · 真实逐帧数据"}]):
        lines += [str(i), "%s --> %s" % (st(b["t"]), st(min(b["t"] + b["dur"], dur))),
                  b.get("caption") or b.get("line") or "", ""]
        i += 1
    srt.write_text("\n".join(lines), encoding="utf-8")

    cmd = [ff, "-y",
           "-loop", "1", "-t", str(dur), "-i", str(plate),
           "-loop", "1", "-t", str(dur), "-i", str(CHAR),
           "-framerate", str(FPS), "-t", str(dur), "-i", str(tmp / "c_%04d.png"),
           "-ss", str(start), "-t", str(dur), "-i", str(video)]
    filt = (
        "[0:v]scale=1080:1920[bg];"
        "[1:v]format=rgba,scale=%d:%d,rotate='0.5*sin(2*PI*t/7.2)*PI/180':c=none:ow=rotw(iw):oh=roth(ih)[ch];"
        "[bg][ch]overlay=x=%d:y='%d+5*sin(2*PI*t/3.4)':format=auto[v1];"
        "[v1][2:v]overlay=x=%d:y=%d:format=auto[v2];"
        "[3:a]showwaves=s=1080x130:mode=cline:colors=blue@0.85:rate=%d[w];"
        "[v2][w]overlay=x=0:y=1600:format=auto[v3];"
        "[v3]subtitles='%s':force_style='FontName=Microsoft YaHei,Fontsize=22,"
        "PrimaryColour=&H00D8EAF5,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=56',"
        "format=yuv420p[vout]"
        % (CHAR_W, CHAR_H, 1080 - 120 - CHAR_W, 1920 - 500 - CHAR_H + 30,
           CURVE_BOX[0], CURVE_BOX[1], FPS,
           str(srt).replace("\\", "/").replace(":", "\\:"))
    )
    cmd += ["-filter_complex", filt, "-map", "[vout]", "-map", "3:a",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)]
    print("[render] 合成中…")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print((r.stderr or "")[-700:])
        return 4
    print("[render] 完成：", out, "%.1f MB" % (out.stat().st_size / 1024 / 1024))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bv", default="BV1i4411d7MJ", help="要用的现场片段 BV")
    ap.add_argument("--start", type=float, default=199.0)
    ap.add_argument("--dur", type=float, default=8.0)
    ap.add_argument("--out", default=str(BASE / "demo_pipeline_8s.mp4"))
    ap.add_argument("--only", default="", choices=["", "fetch", "plate", "curve", "render"])
    ap.add_argument("--height", type=int, default=1080)
    a = ap.parse_args()

    if a.only == "plate":
        make_plate("BV1C8411U7MR"); return 0
    if a.only == "curve":
        tmp = Path(tempfile.mkdtemp(prefix="vpipe_"))
        pts = load_f0(F0_CSV, a.start, a.dur)
        print("曲线点:", len(pts), "Hz范围:", (min(h for _, h in pts), max(h for _, h in pts)) if pts else None)
        print("帧:", len(curve_frames(pts, a.start, int(a.dur * FPS), tmp)))
        return 0
    if a.only == "fetch":
        fetch(a.bv, a.height); return 0

    v = fetch(a.bv, a.height)
    return render(v, a.start, a.dur, Path(a.out))


if __name__ == "__main__":
    raise SystemExit(main())
