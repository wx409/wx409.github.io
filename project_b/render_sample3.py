#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""样片 v3：修正四处对位 + 让「重点」看得见。

新增（针对「既不低也不长，你想夸啥」）
  · 左下角「音高标尺」：58.2Hz 实测点 vs Low C 65.4Hz 参考线，差值标 −1.1 半音
  · 「0.35 秒」保持条：第 3.2s 起填充，填满后定格，直观看到「站住了」
  · 大字提示：第 3.6s 弹出「比男低音及格线还低一个半音」

修正
  · 字幕改用 ASS 绝对定位（\pos），不再被 MarginV 顶到画面外
  · 围裙下移、收窄；嘴部坐标上移缩小；场景提亮
"""
from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = Path(r"E:\wx\论文素材_王晰作传")
SCENE = BASE / "场景_酒馆_手绘v4.png"
CHAR_SRC = BASE / "_char_front_v3.png"
CLIP = sorted(BASE.glob("剪辑素材/BV1i4411d7MJ_*_merged.mp4"))[0]
F0 = BASE / "音域分析" / "专辑音频_分析" / "重游往昔" / "静止了的夜晚_f0.csv"
OUT = BASE / "样片_v3_24s.mp4"
FPS, DUR, LOW_T = 25, 24, 201.6
START = LOW_T - 3.0
FONT = r"C:\Windows\Fonts\msyhbd.ttc"
ff = imageio_ffmpeg.get_ffmpeg_exe()
tmp = Path(tempfile.mkdtemp(prefix="s3_"))


def fnt(sz):
    return ImageFont.truetype(FONT, sz)


def dress() -> Path:
    ch = Image.open(CHAR_SRC).convert("RGBA")
    w, h = ch.size
    ap = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ap)
    top, bot = int(h * 0.615), int(h * 0.90)
    d.polygon([(int(w * .41), top), (int(w * .59), top),
               (int(w * .64), bot), (int(w * .36), bot)], fill=(247, 250, 252, 232))
    d.line([(int(w * .43), int(h * .50)), (int(w * .43), top)], fill=(247, 250, 252, 232), width=8)
    d.line([(int(w * .57), int(h * .50)), (int(w * .57), top)], fill=(247, 250, 252, 232), width=8)
    d.polygon([(int(w * .35), int(h * .60)), (int(w * .41), int(h * .60)),
               (int(w * .41), int(h * .86)), (int(w * .34), int(h * .86))], fill=(38, 62, 104, 220))
    d.polygon([(int(w * .65), int(h * .60)), (int(w * .59), int(h * .60)),
               (int(w * .59), int(h * .86)), (int(w * .66), int(h * .86))], fill=(38, 62, 104, 220))
    d.rectangle([int(w * .39), int(h * .625), int(w * .61), int(h * .645)], fill=(30, 48, 82, 225))
    p = tmp / "char_dressed.png"
    Image.alpha_composite(ch, ap.filter(ImageFilter.GaussianBlur(0.6))).save(p)
    return p


def envelope() -> np.ndarray:
    wav = tmp / "a.wav"
    subprocess.run([ff, "-y", "-ss", str(START), "-t", str(DUR), "-i", str(CLIP),
                    "-ac", "1", "-ar", "8000", str(wav)], capture_output=True)
    raw = subprocess.run([ff, "-i", str(wav), "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    hop = int(8000 / FPS)
    n = DUR * FPS
    env = np.array([float(np.abs(a[i * hop:(i + 1) * hop]).mean()) if len(a) else 0.0 for i in range(n)])
    return env / (env.max() or 1)


def mouth_frames(char: Image.Image, env: np.ndarray):
    w, h = char.size
    cx, cy = int(w * 0.50), int(h * 0.437)
    for i, v in enumerate(env):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        rw, rh = int(7 + 7 * v), int(3 + 9 * v)
        d.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill=(120, 45, 60, int(90 + 140 * v)))
        t = i / FPS
        if t % 3.4 < 0.12:
            for ex in (int(w * 0.40), int(w * 0.60)):
                d.rounded_rectangle([ex - 20, int(h * 0.372), ex + 20, int(h * 0.381)],
                                    radius=4, fill=(255, 236, 220, 255))
        img.save(tmp / ("m_%04d.png" % i))


def curve_and_ruler():
    W, H = 440, 140
    pts = []
    with open(F0, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            try:
                t, hz = float(r["time_s"]), float(r["f0_hz"])
            except Exception:
                continue
            if START <= t <= START + DUR and hz > 0:
                pts.append((t, hz))
    lo, hi = min(h for _, h in pts), max(h for _, h in pts)
    n = DUR * FPS
    # 音高标尺（常驻，左下）
    RW, RH = 420, 250
    ruler = Image.new("RGBA", (RW, RH), (9, 13, 17, 175))
    dr = ImageDraw.Draw(ruler)
    dr.rounded_rectangle([0, 0, RW - 1, RH - 1], radius=12, outline=(106, 208, 255, 120), width=2)
    dr.text((16, 10), "音高标尺", font=fnt(20), fill=(106, 208, 255))
    # 刻度：50-90Hz
    def y_of(hz):
        return int(200 - (hz - 50) / 40 * 150)
    for hz in (55, 60, 65, 70, 75, 80, 85):
        yy = y_of(hz)
        dr.line([(60, yy), (RW - 20, yy)], fill=(255, 255, 255, 28), width=1)
        dr.text((12, yy - 9), "%d" % hz, font=fnt(14), fill=(185, 166, 141))
    # Low C 参考线
    yy = y_of(65.4)
    dr.line([(60, yy), (RW - 20, yy)], fill=(255, 157, 92, 220), width=2)
    dr.text((RW - 130, yy - 26), "Low C 65.4", font=fnt(15), fill=(255, 157, 92))
    # 实测点
    yy2 = y_of(58.2)
    dr.ellipse([96, yy2 - 7, 110, yy2 + 7], fill=(106, 208, 255))
    dr.text((120, yy2 - 12), "58.2Hz（实测）", font=fnt(16), fill=(170, 230, 255))
    dr.text((16, 208), "差 1.1 个半音", font=fnt(17), fill=(255, 210, 160))
    ruler.save(tmp / "ruler.png")
    # 曲线 + 保持条
    for i in range(n):
        t = i / FPS
        frac = (i + 1) / n
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        cut = START + frac * DUR
        line = [(int((tt - START) / DUR * W), int(H - (hz - lo) / max(hi - lo, 6) * (H - 12) - 6))
                for tt, hz in pts if tt <= cut]
        if len(line) > 1:
            d.line(line, fill=(106, 208, 255, 255), width=3)
            d.ellipse([line[-1][0] - 5, line[-1][1] - 5, line[-1][0] + 5, line[-1][1] + 5],
                      fill=(190, 240, 255, 255))
        img.save(tmp / ("c_%04d.png" % i))
        # 保持条：3.2s 起 0.35s 填满
        bar = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        db = ImageDraw.Draw(bar)
        if t >= 3.2:
            p = min(1.0, (t - 3.2) / 0.35)
            x0, y0 = 120, 1180
            db.rounded_rectangle([x0, y0, x0 + 400, y0 + 26], radius=13, fill=(20, 26, 32, 200))
            db.rounded_rectangle([x0, y0, x0 + int(400 * p), y0 + 26], radius=13, fill=(106, 208, 255, 235))
            db.text((x0, y0 - 36), "站住 0.35 秒", font=fnt(26), fill=(245, 234, 216))
        if t >= 3.6:
            db.text((120, 1240), "比男低音及格线还低一个半音", font=fnt(30), fill=(255, 210, 160))
        bar.save(tmp / ("b_%04d.png" % i))


def pip_mask() -> Path:
    m = Image.new("L", (420, 236), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, 419, 235], radius=26, fill=255)
    p = tmp / "pipmask.png"
    m.filter(ImageFilter.GaussianBlur(6)).save(p)
    return p


def ass_file() -> Path:
    def ts(x):
        h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
        return "%d:%02d:%05.2f" % (h, m, s)
    lines = ["""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: D,Microsoft YaHei,46,&H00D8EAF5,&H00000000,&H00000000,-1,1,4,0,2,60,60,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""]
    cues = [(0.2, 3.4, "先听这一句"), (3.4, 8.6, "3:21 · A#1 58.2Hz"),
            (8.8, 15.0, "他在这个音上站了 0.35 秒"), (15.2, 22.0, "两千多个版本，七成以上开口就在那儿"),
            (22.2, 23.9, "低下去的是音区，不是稳定度")]
    for a, b, txt in cues:
        lines.append("Dialogue: 0,%s,%s,D,,0,0,0,,%s" % (ts(a), ts(b), txt))
    p = tmp / "s.ass"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def main() -> int:
    char = dress()
    env = envelope()
    mouth_frames(Image.open(char), env)
    curve_and_ruler()
    pip_mask()
    ass = ass_file()
    filt = (
        "[0:v]scale=1080:1920,fps=%d,eq=brightness=0.05:contrast=1.04[bg];"
        "[6:v]format=rgba[c0];[1:v]format=rgba[mth];[c0][mth]overlay=0:0[c1];"
        "[bg][c1]overlay=331:'610+4*sin(2*PI*t/3.2)':format=auto[v1];"
        "[2:v]format=rgba[cur];[v1][cur]overlay=84:342:format=auto[v2];"
        "[3:v]format=rgba[rul];[v2][rul]overlay=44:1180:format=auto[vz];"
        "[4:v]format=rgba[bars];[vz][bars]overlay=0:0:format=auto[v3];"
        "[5:v]trim=start=0:end=%d,setpts=PTS-STARTPTS,scale=420:236:force_original_aspect_ratio=increase,crop=420:236,fps=%d,split=1[p0];"
        "[p0][7:v]alphamerge[p1];"
        "[v3][p1]overlay=620:150:format=auto[v4];"
        "[5:a]showwaves=s=1080x110:mode=p2p:colors=0x6ad0ff@0.8:rate=%d[w];"
        "[v4][w]overlay=x=0:y=1760:format=auto[v5];"
        "[v5]ass='%s',format=yuv420p[v]"
        % (FPS, DUR, FPS, FPS, str(ass).replace("\\", "/").replace(":", "\\:"))
    )
    cmd = [ff, "-y",
           "-loop", "1", "-t", str(DUR), "-i", str(SCENE),
           "-framerate", str(FPS), "-t", str(DUR), "-i", str(tmp / "m_%04d.png"),
           "-framerate", str(FPS), "-t", str(DUR), "-i", str(tmp / "c_%04d.png"),
           "-loop", "1", "-t", str(DUR), "-i", str(tmp / "ruler.png"),
           "-framerate", str(FPS), "-t", str(DUR), "-i", str(tmp / "b_%04d.png"),
           "-ss", str(START), "-t", str(DUR), "-i", str(CLIP),
           "-loop", "1", "-t", str(DUR), "-i", str(char),
           "-loop", "1", "-t", str(DUR), "-i", str(tmp / "pipmask.png"),
           "-filter_complex", filt, "-map", "[v]", "-map", "5:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-c:a", "aac", "-b:a", "160k", "-t", str(DUR), str(OUT)]
    print("渲染 v3 …")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print((r.stderr or "")[-900:]); return 4
    print("完成：", OUT, "%.1f MB" % (OUT.stat().st_size / 1024 / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
