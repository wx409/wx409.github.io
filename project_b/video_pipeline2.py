#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""声学短片流水线 v2（本地全自动）

一条命令：选片 → 下载合并 → 酒馆背景板 → 真实 F0 曲线 → 眨眼 → 合成

  python -X utf8 project_b\\video_pipeline2.py --pick 1 --dur 10
  python -X utf8 project_b\\video_pipeline2.py --bv BV1i4411d7MJ --start 199 --dur 10

修掉的三个硬伤
  · 背景板：裁掉 B 站水印与原字幕区（y 60–600），底部渐变到黑
  · 波形：mode=p2p 加粗，右下角
  · 字幕：手动断行（caption 里用 \\n），不再被自动折成两半
新增
  · --pick N：按声学价值自动挑片段（过复核 → 最低音更低 → 持续更长），按 BV 去重
  · 眨眼：从立绘里自动定位眼白 → 生成眼皮帧 → 每 3–5 秒眨一次
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter

BASE = Path(r"E:\wx\论文素材_王晰作传")
CLIPS = BASE / "剪辑素材"
CHAR = BASE / "_char_front_v3.png"
PLATE = BASE / "_bg_bar_v6.png"
F0_CSV = BASE / "音域分析" / "专辑音频_分析" / "重游往昔" / "静止了的夜晚_f0.csv"
TOUR = Path(r"D:\wx409.github.io\data\archive_stage_tour.json")
FPS = 25
CHAR_W, CHAR_H = 629, 860
PANEL = (64, 286, 500, 250)
CURVE_BOX = (84, 342, 460, 150)

ff = imageio_ffmpeg.get_ffmpeg_exe()

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ── 选片 ───────────────────────────────────────────────────
def pick(n: int = 3) -> list[dict]:
    rows = json.loads(TOUR.read_text(encoding="utf-8"))["rows"]
    ok = [r for r in rows if r.get("bv") and r.get("low_t_s") and r.get("review_status") in ("谐波列通过", "人耳确认")]
    ok.sort(key=lambda r: (r.get("low_hz") or 999, -(r.get("low_dur_s") or 0)))
    seen, out = set(), []
    for r in ok:
        if r["bv"] in seen:
            continue
        seen.add(r["bv"])
        out.append(r)
        if len(out) >= n:
            break
    return out


# ── 下载 + 合并 ────────────────────────────────────────────
def _ffmpeg_alias() -> Path:
    d = Path(tempfile.gettempdir()) / "ffbin"
    d.mkdir(parents=True, exist_ok=True)
    a = d / "ffmpeg.exe"
    if not a.exists():
        try:
            shutil.copy2(ff, a)
        except Exception:
            pass
    return d


def _has_audio(p: Path) -> bool:
    r = subprocess.run([ff, "-i", str(p)], capture_output=True, text=True, errors="replace")
    return "Audio:" in (r.stderr or "")


def _merge_parts(bv: str) -> Path | None:
    vids = sorted(CLIPS.glob("%s_*.f*.mp4" % bv))
    auds = sorted(CLIPS.glob("%s_*.m4a" % bv))
    if not vids:
        return None
    base = re.sub(r"\.f\d+\.mp4$", "", vids[0].name)
    out = vids[0].with_name(base + "_merged.mp4")
    if out.exists() and _has_audio(out):
        return out
    cmd = [ff, "-y", "-i", str(vids[0])]
    if auds:
        cmd += ["-i", str(auds[0])]
    cmd += ["-c", "copy", "-shortest", str(out)]
    subprocess.run(cmd, capture_output=True)
    return out if out.exists() and _has_audio(out) else None


def fetch(bv: str, height: int = 1080) -> Path:
    CLIPS.mkdir(parents=True, exist_ok=True)
    for p in sorted(CLIPS.glob("%s_*_merged.mp4" % bv)):
        if _has_audio(p):
            print("[fetch] 复用：", p.name)
            return p
    m = _merge_parts(bv)
    if m:
        print("[fetch] 合并分轨：", m.name)
        return m
    url = "https://www.bilibili.com/video/%s" % bv
    cmd = ["yt-dlp", "--no-playlist", "--ffmpeg-location", str(_ffmpeg_alias()),
           "-f", "bv*[height<=%d]+ba/b[height<=%d]" % (height, height),
           "--merge-output-format", "mp4",
           "-o", str(CLIPS / ("%s_%%(title).40s.%%(ext)s" % bv)), url]
    print("[fetch] 下载", url)
    subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = _merge_parts(bv)
    if not m:
        raise SystemExit("下载失败：%s" % bv)
    return m


# ── 背景板（无水印/无原字幕）───────────────────────────────
def make_plate() -> Path:
    if PLATE.exists():
        print("[plate] 复用：", PLATE.name)
        return PLATE
    src = fetch("BV1C8411U7MR", 720)
    raw = BASE / "_plate_tmp.png"
    subprocess.run([ff, "-y", "-ss", "146.5", "-i", str(src), "-frames:v", "1", str(raw)], capture_output=True)
    im = Image.open(raw).convert("RGB")
    # y 60–600：上方避开 B 站水印，下方避开原字幕
    crop = im.crop((0, 60, 620, 600))
    s = 1920 / crop.height
    crop = crop.resize((int(crop.width * s), 1920), Image.LANCZOS).crop((0, 0, 1080, 1920))
    crop = crop.filter(ImageFilter.GaussianBlur(3.4))
    crop = Image.blend(crop, Image.new("RGB", crop.size, (12, 9, 8)), 0.36)
    # 面板底板
    ov = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle([64, 286, 564, 536], radius=14,
                                         fill=(9, 13, 17, 168), outline=(106, 208, 255, 120), width=2)
    crop = Image.alpha_composite(crop.convert("RGBA"), ov).convert("RGB")
    crop.save(PLATE)
    print("[plate] 生成：", PLATE.name)
    return PLATE


# ── 真实 F0 曲线帧 ─────────────────────────────────────────
def load_f0(start: float, dur: float) -> list[tuple[float, float]]:
    out = []
    with open(F0_CSV, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                t, hz = float(r["time_s"]), float(r["f0_hz"])
            except Exception:
                continue
            if start <= t <= start + dur and hz > 0:
                out.append((t, hz))
    return out


def curve_frames(pts, start, n, tmp):
    lo, hi = min(h for _, h in pts), max(h for _, h in pts)
    rng = max(hi - lo, 6.0)
    W, H = CURVE_BOX[2], CURVE_BOX[3]
    files = []
    t_end = pts[-1][0]
    for f in range(n):
        frac = (f + 1) / n
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        cur = [p for p in pts if p[0] <= start + frac * (t_end - start)]
        line = [(int((t - start) / max(1e-6, t_end - start) * W),
                 int(H - (h - lo) / rng * (H - 12) - 6)) for t, h in cur]
        if len(line) > 1:
            d.line(line, fill=(106, 208, 255, 255), width=3)
            x, y = line[-1]
            d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(170, 230, 255, 255))
        p = tmp / ("c_%04d.png" % f)
        img.save(p)
        files.append(p)
    return files


# ── 眨眼帧 ─────────────────────────────────────────────────
def find_eyes(char: Image.Image) -> list[tuple[int, int, int, int]]:
    """在立绘上半部找两块最大「近白」区域 = 眼白。"""
    a = char.convert("RGBA")
    w, h = a.size
    px = a.load()
    y0, y1 = int(h * 0.16), int(h * 0.42)
    x0, x1 = int(w * 0.25), int(w * 0.78)
    pts = [(x, y) for y in range(y0, y1) for x in range(x0, x1)
           if px[x, y][0] > 242 and px[x, y][1] > 242 and px[x, y][2] > 242 and px[x, y][3] > 200]
    if not pts:
        return []
    # 简单聚类：按 x 分成两簇
    pts.sort()
    mid = len(pts) // 2
    boxes = []
    for grp in (pts[:mid], pts[mid:]):
        xs = [p[0] for p in grp]; ys = [p[1] for p in grp]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return boxes


def blink_frames(char: Image.Image, n: int, dur: float, tmp: Path) -> list[Path]:
    eyes = find_eyes(char)
    if len(eyes) < 2:
        print("[blink] 未能定位眼睛，跳过")
        return []
    print("[blink] 眼睛位置:", eyes)
    # 每 3–5 秒眨一次
    times, t = [], 1.8
    while t < dur:
        times.append(t)
        t += 3.0 + random.random() * 2.0
    files = []
    for f in range(n):
        tt = f / FPS
        img = Image.new("RGBA", char.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for bt in times:
            if bt <= tt <= bt + 0.12:
                for x0, y0, x1, y1 in eyes:
                    pad = 6
                    d.rounded_rectangle([x0 - pad, (y0 + y1) // 2 - 5, x1 + pad, (y0 + y1) // 2 + 6],
                                        radius=8, fill=(255, 236, 220, 255))
                    d.line([x0 - pad, (y0 + y1) // 2 + 4, x1 + pad, (y0 + y1) // 2 + 4],
                           fill=(120, 90, 70, 255), width=3)
        p = tmp / ("b_%04d.png" % f)
        img.save(p)
        files.append(p)
    return files


# ── 合成 ───────────────────────────────────────────────────
def render(video: Path, start: float, dur: float, out: Path, caption: str) -> int:
    plate = make_plate()
    n = int(dur * FPS)
    tmp = Path(tempfile.mkdtemp(prefix="vp2_"))
    pts = load_f0(start, dur)
    if not pts:
        raise SystemExit("该时间段无 F0 数据")
    curves = curve_frames(pts, start, n, tmp)
    char_img = Image.open(CHAR).convert("RGBA")
    blinks = blink_frames(char_img, n, dur, tmp)

    def st(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%02d:%02d:%06.3f" % (h, m, s)

    srt = tmp / "s.srt"
    srt.write_text("1\n%s --> %s\n%s\n" % (st(0), st(dur), caption), encoding="utf-8")

    cmd = [ff, "-y",
           "-loop", "1", "-t", str(dur), "-i", str(plate),
           "-loop", "1", "-t", str(dur), "-i", str(CHAR),
           "-framerate", str(FPS), "-t", str(dur), "-i", str(tmp / "c_%04d.png")]
    idx = 3
    if blinks:
        cmd += ["-framerate", str(FPS), "-t", str(dur), "-i", str(tmp / "b_%04d.png")]
    cmd += ["-ss", str(start), "-t", str(dur), "-i", str(video)]
    audio_idx = 4 if blinks else 3

    cx, cy = 1080 - 120 - CHAR_W, 1920 - 500 - CHAR_H + 30
    chain = ("[0:v]scale=1080:1920[bg];"
             "[1:v]format=rgba,scale=%d:%d,rotate='0.5*sin(2*PI*t/7.2)*PI/180':c=none:ow=rotw(iw):oh=roth(ih)[ch];"
             "[bg][ch]overlay=x=%d:y='%d+5*sin(2*PI*t/3.4)':format=auto[v1];"
             % (CHAR_W, CHAR_H, cx, cy))
    if blinks:
        chain += ("[3:v]format=rgba[bk];[v1][bk]overlay=x=%d:y='%d+5*sin(2*PI*t/3.4)':format=auto[v2];"
                  % (cx, cy))
        chain += "[v2][2:v]overlay=x=%d:y=%d:format=auto[v3];" % (CURVE_BOX[0], CURVE_BOX[1])
        src = "[v3]"
    else:
        chain += "[v1][2:v]overlay=x=%d:y=%d:format=auto[v2];" % (CURVE_BOX[0], CURVE_BOX[1])
        src = "[v2]"
    chain += ("[%d:a]showwaves=s=1080x140:mode=p2p:colors=0x6ad0ff@0.9:rate=%d[w];"
              "%s[w]overlay=x=0:y=1590:format=auto[v4];"
              "[v4]subtitles='%s':force_style='FontName=Microsoft YaHei,Fontsize=24,"
              "PrimaryColour=&H00D8EAF5,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=56',"
              "format=yuv420p[vout]"
              % (audio_idx, FPS, src,
                 str(srt).replace("\\", "/").replace(":", "\\:")))


    cmd += ["-filter_complex", chain, "-map", "[vout]", "-map", "%d:a" % audio_idx,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)]
    print("[render] 合成中…")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print((r.stderr or "")[-800:])
        return 4
    print("[render] 完成：", out, "%.1f MB" % (out.stat().st_size / 1024 / 1024))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bv", default="")
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--dur", type=float, default=10)
    ap.add_argument("--pick", type=int, default=0, help="自动挑 N 个片段并列出")
    ap.add_argument("--out", default=str(BASE / "demo_v3.mp4"))
    ap.add_argument("--caption", default="站了 0.35 秒，不是扫一下就过")
    a = ap.parse_args()

    if a.pick:
        for i, r in enumerate(pick(a.pick), 1):
            print("%d) %s  %s  %s %.1fHz  %.2fs  @%.1fs" % (
                i, r["bv"], r.get("song"), r.get("low_note"), r["low_hz"],
                r.get("low_dur_s") or 0, r["low_t_s"]))
        return 0

    if not a.bv:
        r = pick(1)[0]
        a.bv, a.start = r["bv"], max(0, r["low_t_s"] - 3.0)
        print("[pick] 自动选中：%s %s @%.1fs" % (a.bv, r.get("song"), a.start))

    v = fetch(a.bv)
    return render(v, a.start, a.dur, Path(a.out), a.caption)


if __name__ == "__main__":
    raise SystemExit(main())
