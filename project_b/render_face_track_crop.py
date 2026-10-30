#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""人脸跟随裁切：把横屏现场裁成 9:16，窗口跟着脸走，避免人头出框。

输入：源视频 + 区间列表（从 plan_xyy_long.json 读）
输出：竖屏成片（复用已有音频）
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import cv2
import imageio_ffmpeg
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
SRC = r'E:\wx\论文素材_王晰作传\现场录音-补充\BV1Qm42177HY_前方高能，观看视频的过程中允许喘气_【王晰四巡】《想游泳的星》首唱_王晰【肆益】个人巡回音乐会-20240406_上海.mp4'
PLAN = r'E:\wx\video_clip1\plan_xyy_long.json'
OUT = Path(r'E:\wx\video_clip1')
AUDIO = OUT / '06_想游泳的星_52s_竖屏.mp4'   # 复用其音轨
FINAL = OUT / '06_想游泳的星_52s_竖屏_人脸跟随.mp4'
OUTW, OUTH = 1080, 1920
CROPW = 608
FF = imageio_ffmpeg.get_ffmpeg_exe()

plan = json.loads(Path(PLAN).read_text(encoding='utf-8'))
segs = plan['segments']

# 1) 按区间切出片段（无音轨）
parts = []
for i, s in enumerate(segs):
    p = OUT / f'_seg_{i:02d}.mp4'
    subprocess.run([FF, '-y', '-ss', f"{s['src_in']:.3f}", '-to', f"{s['src_out']:.3f}",
                    '-i', SRC, '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', str(p)],
                   capture_output=True)
    parts.append(p)
concat = OUT / '_concat.mp4'
with open(OUT / '_list.txt', 'w', encoding='utf-8') as f:
    for p in parts:
        f.write(f"file '{p.as_posix()}'\n")
subprocess.run([FF, '-y', '-f', 'concat', '-safe', '0', '-i', str(OUT / '_list.txt'),
                '-c', 'copy', str(concat)], capture_output=True)

# 2) 逐帧检测人脸 → 平滑轨迹
cap = cv2.VideoCapture(str(concat))
srch, srcw = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
fps = cap.get(cv2.CAP_PROP_FPS) or 30
cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
centers = []
while True:
    ok, frame = cap.read()
    if not ok:
        break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, 1.15, 5, minSize=(60, 60))
    if len(faces):
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        centers.append(x + w / 2)
    else:
        centers.append(np.nan)
cap.release()
centers = np.array(centers, dtype=float)
# 用中位填补再滑动平均
idx = np.arange(len(centers))
good = ~np.isnan(centers)
if good.sum() < 10:
    centers[:] = srcw / 2
else:
    centers = np.interp(idx, idx[good], centers[good])
k = 45
kernel = np.ones(k) / k
smooth = np.convolve(np.pad(centers, (k // 2, k // 2), mode='edge'), kernel, mode='valid')
half = CROPW // 2
smooth = np.clip(smooth, half, srcw - half)
print(f'帧数 {len(centers)}｜检出人脸 {int(good.sum())} 帧｜窗口 x 范围 {smooth.min():.0f}–{smooth.max():.0f}')

# 3) 按轨迹裁切 + 缩放
cap = cv2.VideoCapture(str(concat))
writer = cv2.VideoWriter(str(OUT / '_tracked_raw.mp4'), cv2.VideoWriter_fourcc(*'mp4v'), fps, (OUTW, OUTH))
i = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    cx = int(smooth[min(i, len(smooth) - 1)])
    x0 = max(0, min(srcw - CROPW, cx - half))
    crop = frame[0:srch, x0:x0 + CROPW]
    out = cv2.resize(crop, (OUTW, OUTH), interpolation=cv2.INTER_LANCZOS4)
    writer.write(out)
    i += 1
cap.release()
writer.release()

# 4) 合音轨
subprocess.run([FF, '-y', '-i', str(OUT / '_tracked_raw.mp4'), '-i', str(AUDIO),
                '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
                '-c:a', 'copy', '-shortest', str(FINAL)], capture_output=True)
for p in parts + [concat, OUT / '_tracked_raw.mp4']:
    p.unlink(missing_ok=True)
(OUT / '_list.txt').unlink(missing_ok=True)
print('完成', FINAL.name, round(FINAL.stat().st_size / 1e6, 1), 'MB')
