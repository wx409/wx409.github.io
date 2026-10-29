#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""招牌条第 1 条：竖屏草稿渲染（黑底 + 波形 + 字幕 + 三段原声）。

产物：cutout/03-卡点表.csv、05-字幕.srt、05-竖屏草稿.mp4
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import av
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx\论文素材_王晰作传\视频素材_招牌')
OUT = ROOT / 'cutout'
OUT.mkdir(parents=True, exist_ok=True)
SRC = Path(r'E:\wx\论文素材_王晰作传\音域分析\网易云补_单曲\火光.mp3')
W, H, FPS = 1080, 1920, 30
DUR = 30.0

# 时间轴（秒）
PLAN = [
    (0.0, 3.0, None, '同一个字，他唱了三遍', None),
    (3.0, 6.5, 86.0, '1:26', 0.55),
    (6.5, 7.5, None, '', None),
    (7.5, 11.0, 146.0, '2:26', 0.55),
    (11.0, 12.0, None, '', None),
    (12.0, 15.5, 197.0, '3:17（最狠的一次）', 0.55),
    (15.5, 16.5, None, '', None),
    (16.5, 23.0, None, '音高一样｜2.55 秒一样｜变的只是"脏"了多少', None),
    (23.0, 30.0, 197.0, '第三次最险，多一点点就破了', 0.25),
]

# 字体
FONT = None
for fp in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf'):
    if Path(fp).exists():
        FONT = fp
        break


def font(size):
    return ImageFont.truetype(FONT, size) if FONT else ImageFont.load_default()


# 读源音频
x, sr = sf.read(str(SRC), dtype='float32', always_2d=True)
m = x.mean(axis=1)
# 30 秒音轨
mix = np.zeros(int(DUR * sr), dtype='float32')
env_marks = []
for a, b, src_t, text, gain in PLAN:
    if src_t is None:
        continue
    seg = m[int(src_t * sr):int((src_t + (b - a)) * sr)].copy()
    if gain:
        seg *= gain
    A, B = int(a * sr), int(a * sr) + len(seg)
    mix[A:B] += seg[:max(0, len(mix) - A)]
# 归一化防削波
peak = np.abs(mix).max()
if peak > 0.98:
    mix *= 0.98 / peak
sf.write(str(OUT / 'audio_30s.wav'), mix, sr)

# 包络（用于波形）
win = int(0.03 * sr)
n = len(mix) // win
env = np.array([np.abs(mix[i*win:(i+1)*win]).max() for i in range(n)])
env = env / (env.max() + 1e-9)

# 卡点表
with open(OUT / '03-卡点表.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['序号', '入点(秒)', '出点(秒)', '时长', '音频源起点(秒)', '字幕', '画面'])
    for i, (a, b, t, text, gain) in enumerate(PLAN, 1):
        w.writerow([i, a, b, round(b - a, 2), t if t else '', text, '黑底+波形'])

# 字幕 SRT
def ts(sec):
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')

with open(OUT / '05-字幕.srt', 'w', encoding='utf-8') as f:
    idx = 1
    for a, b, t, text, gain in PLAN:
        if not text:
            continue
        f.write(f'{idx}\n{ts(a)} --> {ts(b)}\n{text}\n\n')
        idx += 1

# 画面
container = av.open(str(OUT / '05-竖屏草稿.mp4'), mode='w', format='mp4')
vstream = container.add_stream('libx264', rate=FPS)
vstream.width, vstream.height = W, H
vstream.pix_fmt = 'yuv420p'
vstream.options = {'crf': '23', 'preset': 'veryfast'}

f_title = font(64)
f_mid = font(52)
f_small = font(40)

for fi in range(int(DUR * FPS)):
    t = fi / FPS
    img = Image.new('RGB', (W, H), (8, 8, 10))
    d = ImageDraw.Draw(img)

    # 波形（底部）：以当前位置为中线，随播放滚动
    base_y = int(H * 0.76)
    idx = min(int(t / 0.03), n - 1)
    half = 70
    for k in range(-half, half):
        j = idx + k
        if 0 <= j < n:
            v = env[j]
            hgt = int(v * 200)
            x0 = W // 2 + k * 7
            d.line([(x0, base_y - hgt), (x0, base_y + hgt)], fill=(200, 30, 58), width=4)
    # 进度条
    d.rectangle([0, H - 10, int(W * (t / DUR)), H], fill=(200, 30, 58))

    # 字幕
    for a, b, src_t, text, gain in PLAN:
        if a <= t < b and text:
            if src_t is not None:      # 正在播原声：标签放上方，字小
                fnt, y = f_small, int(H * 0.18)
            elif a == 0:               # 片头标题
                fnt, y = f_title, int(H * 0.40)
            else:                      # 说明卡
                fnt, y = (f_mid if len(text) < 16 else f_small), int(H * 0.36)
            bbox = d.textbbox((0, 0), text, font=fnt)
            d.text(((W - (bbox[2] - bbox[0])) // 2, y), text, font=fnt, fill=(245, 245, 245))

    frame = av.VideoFrame.from_image(img)
    for pkt in vstream.encode(frame):
        container.mux(pkt)

for pkt in vstream.encode():
    container.mux(pkt)

container.close()

# 用 ffmpeg 合音轨（PyAV 直连音频会报 rebase 错误）
import subprocess, imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()
tmpv = OUT / '_video_only.mp4'
(OUT / '05-竖屏草稿.mp4').rename(tmpv)
subprocess.run([FF, '-y', '-i', str(tmpv), '-i', str(OUT / 'audio_30s.wav'),
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                str(OUT / '05-竖屏草稿.mp4')], capture_output=True)
tmpv.unlink(missing_ok=True)
print('视频已生成', OUT / '05-竖屏草稿.mp4', round((OUT / '05-竖屏草稿.mp4').stat().st_size / 1e6, 1), 'MB')
print('卡点表', OUT / '03-卡点表.csv')
print('字幕', OUT / '05-字幕.srt')
