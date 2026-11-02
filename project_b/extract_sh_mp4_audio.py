import sys, os
from pathlib import Path
import numpy as np, av, soundfile as sf
sys.stdout.reconfigure(encoding='utf-8')
BASE = Path(r'H:\王晰巡演素材存档\现场录制视频\五巡\大疆录制上海场20251121')
DST = Path(r'E:\wx\论文素材_王晰作传\_staging_现场\h5_sh_20251121_ok')
DST.mkdir(parents=True, exist_ok=True)
n = 0
for f in sorted(BASE.glob('*.MP4')):
    if 'talk' in f.name.lower():
        continue
    out = DST / (f.stem.replace('吾巡演上海站_', '')[:40] + '.wav')
    if out.exists():
        continue
    c = av.open(str(f))
    a = c.streams.audio[0]
    buf = []
    for fr in c.decode(audio=0):
        arr = fr.to_ndarray()
        buf.append(arr.mean(axis=0) if arr.ndim > 1 else arr)
    x = np.concatenate(buf).astype('float32')
    sf.write(str(out), x, a.rate)
    n += 1
    print('抽轨', out.name[:44], '%.1f 分钟' % (len(x)/a.rate/60), flush=True)
print('完成', n, '个')
