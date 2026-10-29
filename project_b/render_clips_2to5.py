#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""招牌系列第 2–5 条：竖屏草稿（黑底 + 滚动波形 + 字幕 + 多源拼接音轨）。"""
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

SRC = {
    'huoguang': r'E:\wx\论文素材_王晰作传\音域分析\网易云补_单曲\火光.mp3',
    'maixia': r'E:\wx\论文素材_王晰作传\单曲音频\正式发行单曲_OST\埋下记忆.mp3',
    'wj_live': r'E:\wx\论文素材_王晰作传\音域分析\场次音频\wav_五巡上海20251121\20251121205303 0035 无尽的夜里第1遍\20251121205303 0035 无尽的夜里第1遍.wav',
    'wj_studio': r'E:\wx\论文素材_王晰作传\音域分析\专辑音频\不说\无尽的夜里.mp3',
    'lv_studio': r'E:\wx\论文素材_王晰作传\单曲音频\舞台对照·QQ官方版\小毛驴.mp3',
    'lv_live': r'E:\wx\论文素材_王晰作传\音域分析\场次音频\wav_新源现场\钢铁小毛驴\一巡北京收官20200102_p16_钢铁小毛驴.wav',
}

# 每条：(输出名, 时长, [(入, 出, 源key, 源起点, 字幕, 增益)])
CLIPS = {
    '02_他没往上飙': (22.0, [
        (0.0, 3.0, None, None, '以为他在喊？', None),
        (3.0, 10.0, 'huoguang', 197.0, '', 0.6),
        (10.0, 16.0, 'huoguang', 197.0, '高频一直没上去', 0.6),
        (16.0, 22.0, 'huoguang', 197.0, '他是往下压，不是往上喊', 0.6),
    ]),
    '03_越用力越干净': (20.0, [
        (0.0, 3.0, None, None, '该用力的地方，他反而更干净', None),
        (3.0, 12.0, 'maixia', 80.0, '', 0.75),
        (12.0, 20.0, 'maixia', 80.0, '副歌比主歌干净 1.6 分贝', 0.75),
    ]),
    '04_现场比录音室还轻': (20.0, [
        (0.0, 3.0, None, None, '现场应该更炸？他更轻', None),
        (3.0, 9.0, 'wj_live', 40.0, '现场 −19.4 dB', 0.8),
        (9.0, 15.0, 'wj_studio', 40.0, '录音室 −16.2 dB', 0.8),
        (15.0, 20.0, None, None, '他靠的不是大', None),
    ]),
    '05_该炸的时候他真炸': (20.0, [
        (0.0, 3.0, None, None, '一首儿歌，被他改成了重型', None),
        (3.0, 9.0, 'lv_studio', 20.0, '录音室：每秒 5.1 次起音', 0.8),
        (9.0, 15.0, 'lv_live', 40.0, '现场：每秒 12.2 次', 0.6),
        (15.0, 20.0, None, None, '不是不会炸，是挑着炸', None),
    ]),
}


def font(size):
    return ImageFont.truetype(FONT, size)


def build(clip: str):
    dur, plan = CLIPS[clip]
    mix = None
    sr = None
    for a, b, key, src_t, text, gain in plan:
        if key is None:
            continue
        x, s = sf.read(SRC[key], dtype='float32', always_2d=True)
        m = x.mean(axis=1)
        if mix is None:
            sr = s
            mix = np.zeros(int(dur * sr), dtype='float32')
        if s != sr:
            idx = np.linspace(0, len(m) - 1, int(len(m) * sr / s))
            m = np.interp(idx, np.arange(len(m)), m).astype('float32')
        seg = m[int(src_t * sr):int((src_t + (b - a)) * sr)].copy()
        if gain:
            seg *= gain
        A = int(a * sr)
        mix[A:A + len(seg)] += seg[:max(0, len(mix) - A)]
    if mix is None:
        sr = 44100
        mix = np.zeros(int(dur * sr), dtype='float32')
    peak = float(np.abs(mix).max())
    if peak > 0.98:
        mix *= 0.98 / peak
    wav = OUT / f'{clip}_audio.wav'
    sf.write(str(wav), mix, sr)

    win = int(0.03 * sr)
    n = len(mix) // win
    env = np.array([np.abs(mix[i*win:(i+1)*win]).max() for i in range(n)])
    env = env / (env.max() + 1e-9)

    with open(OUT / f'{clip}_卡点表.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['序号', '入点', '出点', '时长', '音频源', '源起点', '字幕'])
        for i, (a, b, key, src_t, text, gain) in enumerate(plan, 1):
            w.writerow([i, a, b, round(b - a, 2), key or '', src_t if src_t else '', text])

    tmp = OUT / f'_{clip}_v.mp4'
    container = av.open(str(tmp), mode='w', format='mp4')
    vs = container.add_stream('libx264', rate=FPS)
    vs.width, vs.height, vs.pix_fmt = W, H, 'yuv420p'
    vs.options = {'crf': '23', 'preset': 'veryfast'}
    f_title, f_mid, f_small = font(60), font(52), font(42)
    for fi in range(int(dur * FPS)):
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
        d.rectangle([0, H - 10, int(W * (t / dur)), H], fill=(200, 30, 58))
        for a, b, key, src_t, text, gain in plan:
            if a <= t < b and text:
                fnt = f_small if key else (f_title if a == 0 else f_mid)
                y = int(H * 0.18) if key else (int(H * 0.40) if a == 0 else int(H * 0.36))
                box = d.textbbox((0, 0), text, font=fnt)
                d.text(((W - (box[2] - box[0])) // 2, y), text, font=fnt, fill=(245, 245, 245))
        for pkt in vs.encode(av.VideoFrame.from_image(img)):
            container.mux(pkt)
    for pkt in vs.encode():
        container.mux(pkt)
    container.close()

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    final = OUT / f'{clip}_竖屏草稿.mp4'
    subprocess.run([ff, '-y', '-i', str(tmp), '-i', str(wav), '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '192k', '-shortest', str(final)],
                   capture_output=True)
    tmp.unlink(missing_ok=True)
    print(f'{clip} 完成 {dur}s → {final.name} {round(final.stat().st_size/1e6,2)} MB')


for c in CLIPS:
    build(c)
