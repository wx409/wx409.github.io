import sys, json
from pathlib import Path
import numpy as np, soundfile as sf
sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(r'E:\wx\论文素材_王晰作传\视频素材_长音')
OUT.mkdir(parents=True, exist_ok=True)

CLIPS = [
    ("01_想游泳的星_首唱", r'E:\wx\论文素材_王晰作传\现场录音-补充\BV1Qm42177HY_前方高能，观看视频的过程中允许喘气_【王晰四巡】《想游泳的星》首唱_王晰【肆益】个人巡回音乐会-20240406_上海.wav',
     247.4, 14.3),
    ("02_海然海然_录音笔", r'E:\wx\论文素材_王晰作传\现场录音-录音笔\录音笔直出\BV1Mi421C7gW_录音笔直出高音质，诚邀大家戴上耳机沉浸式体验王哥的现场魅力_【4K字幕】《海然海然_x_嘎达梅林》_王晰【肆益】个人巡回.wav',
     283.35, 12.8),
]
meta = []
for name, path, t0, dur in CLIPS:
    x, sr = sf.read(path, dtype='float32', always_2d=True)
    a = int(max(0, t0 - 0.6) * sr)
    b = int((t0 + dur + 0.8) * sr)
    seg = x[a:b]
    f = OUT / f'{name}.wav'
    sf.write(str(f), seg, sr)
    meta.append({"name": name, "file": str(f), "core_start": t0, "core_dur": dur,
                 "clip_dur": round(len(seg) / sr, 2), "sr": sr})
    print(f'{name}: 核心 {dur}s，含前后引子共 {len(seg)/sr:.1f}s -> {f.name}')

# 合并预览（两段之间留 1 秒）
import numpy as np
arrs = []
for m in meta:
    x, sr = sf.read(m['file'], dtype='float32', always_2d=True)
    arrs.append(x)
gap = np.zeros((int(1.0 * sr), arrs[0].shape[1]), dtype='float32')
allx = np.concatenate([arrs[0], gap, arrs[1]], axis=0)
sf.write(str(OUT / '00_合集预览.wav'), allx, sr)
print('合集预览', round(len(allx) / sr, 1), '秒')
json.dump(meta, open(OUT / 'meta.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
