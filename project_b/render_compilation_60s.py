#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""60 秒合集 + 封面图（小红书/抖音通用）。"""
from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

import av
import imageio_ffmpeg
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(r'E:\wx\video_clip1')
W, H, FPS = 1080, 1920, 30
FONT = r'C:\Windows\Fonts\msyh.ttc'
DUR = 60.0

SRC = {
    'huoguang': r'E:\wx\论文素材_王晰作传\音域分析\网易云补_单曲\火光.mp3',
    'maixia': r'E:\wx\论文素材_王晰作传\单曲音频\正式发行单曲_OST\埋下记忆.mp3',
    'wj_live': r'E:\wx\论文素材_王晰作传\音域分析\场次音频\wav_五巡上海20251121\20251121205303 0035 无尽的夜里第1遍\20251121205303 0035 无尽的夜里第1遍.wav',
    'lv_live': r'E:\wx\论文素材_王晰作传\音域分析\场次音频\wav_新源现场\钢铁小毛驴\一巡北京收官20200102_p16_钢铁小毛驴.wav',
}

PLAN = [
    (0.0, 3.0, None, None, '同一个字，他唱了三遍', None),
    (3.0, 6.5, 'huoguang', 86.0, '1:26', 0.55),
    (6.5, 7.5, None, None, '', None),
    (7.5, 11.0, 'huoguang', 146.0, '2:26', 0.55),
    (11.0, 12.0, None, None, '', None),
    (12.0, 15.5, 'huoguang', 197.0, '3:17（最狠的一次）', 0.55),
    (15.5, 17.0, None, None, '', None),
    (17.0, 22.0, None, None, '音高一样｜2.55 秒一样｜变的只是"脏"了多少', None),
    (22.0, 24.0, None, None, '换个方向看', None),
    (24.0, 33.0, 'maixia', 80.0, '越用力，他越干净', 0.75),
    (33.0, 34.0, None, None, '', None),
    (34.0, 43.0, 'wj_live', 40.0, '现场比录音室还轻', 0.8),
    (43.0, 44.0, None, None, '', None),
    (44.0, 53.0, 'lv_live', 40.0, '该炸的时候他真炸', 0.6),
    (53.0, 60.0, None, None, '他的劲，是压到快没气还收得住', None),
]


def font(sz):
    return ImageFont.truetype(FONT, sz)


# 音轨
mix, sr = None, None
for a, b, key, src_t, text, gain in PLAN:
    if key is None:
        continue
    x, s = sf.read(SRC[key], dtype='float32', always_2d=True)
    m = x.mean(axis=1)
    if mix is None:
        sr = s
        mix = np.zeros(int(DUR * sr), dtype='float32')
    seg = m[int(src_t * sr):int((src_t + (b - a)) * sr)].copy()
    if gain:
        seg *= gain
    A = int(a * sr)
    mix[A:A + len(seg)] += seg[:max(0, len(mix) - A)]
mix *= 0.98 / max(float(np.abs(mix).max()), 1e-9)
sf.write(str(OUT / '合集60s_audio.wav'), mix, sr)

win = int(0.03 * sr)
n = len(mix) // win
env = np.array([np.abs(mix[i*win:(i+1)*win]).max() for i in range(n)])
env = env / (env.max() + 1e-9)

with open(OUT / '合集60s_卡点表.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['序号', '入点', '出点', '时长', '音频源', '源起点', '字幕'])
    for i, (a, b, key, src_t, text, gain) in enumerate(PLAN, 1):
        w.writerow([i, a, b, round(b - a, 2), key or '', src_t if src_t else '', text])

with open(OUT / '合集60s_字幕.srt', 'w', encoding='utf-8') as f:
    idx = 1
    for a, b, key, src_t, text, gain in PLAN:
        if not text:
            continue
        def ts(x):
            h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
            return f'{h:02d}:{m:02d}:{s:06.3f}'.replace('.', ',')
        f.write(f'{idx}\n{ts(a)} --> {ts(b)}\n{text}\n\n')
        idx += 1

tmp = OUT / '_60_v.mp4'
c = av.open(str(tmp), mode='w', format='mp4')
vs = c.add_stream('libx264', rate=FPS)
vs.width, vs.height, vs.pix_fmt = W, H, 'yuv420p'
vs.options = {'crf': '23', 'preset': 'veryfast'}
f_title, f_mid, f_small = font(64), font(54), font(44)
for fi in range(int(DUR * FPS)):
    t = fi / FPS
    img = Image.new('RGB', (W, H), (8, 8, 10))
    d = ImageDraw.Draw(img)
    base_y = int(H * 0.76)
    idx = min(int(t / 0.03), n - 1)
    for k in range(-70, 70):
        j = idx + k
        if 0 <= j < n:
            hgt = int(env[j] * 200)
            d.line([(W // 2 + k * 7, base_y - hgt), (W // 2 + k * 7, base_y + hgt)],
                   fill=(200, 30, 58), width=4)
    d.rectangle([0, H - 10, int(W * (t / DUR)), H], fill=(200, 30, 58))
    for a, b, key, src_t, text, gain in PLAN:
        if a <= t < b and text:
            fnt = f_small if key else (f_title if a == 0 else (f_mid if len(text) < 18 else f_small))
            y = int(H * 0.18) if key else (int(H * 0.40) if a == 0 else int(H * 0.36))
            box = d.textbbox((0, 0), text, font=fnt)
            d.text(((W - (box[2] - box[0])) // 2, y), text, font=fnt, fill=(245, 245, 245))
    for pkt in vs.encode(av.VideoFrame.from_image(img)):
        c.mux(pkt)
for pkt in vs.encode():
    c.mux(pkt)
c.close()

ff = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ff, '-y', '-i', str(tmp), '-i', str(OUT / '合集60s_audio.wav'),
                '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                str(OUT / '合集60s_竖屏.mp4')], capture_output=True)
tmp.unlink(missing_ok=True)
print('合集完成', round((OUT / '合集60s_竖屏.mp4').stat().st_size / 1e6, 2), 'MB')

# 封面
cover = Image.new('RGB', (W, H), (8, 8, 10))
d = ImageDraw.Draw(cover)
lines = [('同一个字', 110), ('他唱了三遍', 110), ('', 40), ('王晰《火光》实测', 52)]
y = 620
for text, sz in lines:
    if not text:
        y += 40
        continue
    fnt = font(sz)
    box = d.textbbox((0, 0), text, font=fnt)
    d.text(((W - (box[2] - box[0])) // 2, y), text, font=fnt, fill=(245, 245, 245))
    y += sz + 40
d.rectangle([0, H - 14, W, H], fill=(200, 30, 58))
cover.save(OUT / '封面_1080x1920.png')
print('封面完成')
