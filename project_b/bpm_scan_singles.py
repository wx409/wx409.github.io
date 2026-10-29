import sys, json
from pathlib import Path
import numpy as np, soundfile as sf
sys.stdout.reconfigure(encoding='utf-8')

def bpm_of(p):
    x, sr = sf.read(str(p), dtype='float32', always_2d=True)
    m = x.mean(axis=1)
    hop = 512
    env = np.array([np.sqrt(np.mean(m[i:i+hop]**2)) for i in range(0, len(m)-hop, hop)])
    env = env - env.mean()
    ac = np.correlate(env, env, 'full')[len(env)-1:]
    ac = ac[:int(sr/hop*1.2)]
    # 只允许 60–180 BPM 的周期（0.33–1.0 秒）
    lo, hi = int(sr/hop*0.333), int(sr/hop*1.0)
    seg = ac[lo:hi]
    lag = lo + int(np.argmax(seg))
    bpm = 60 * sr / hop / lag
    return round(bpm, 1)

roots = [Path(r'E:\wx\论文素材_王晰作传\单曲音频\正式发行单曲_OST'),
         Path(r'E:\wx\论文素材_王晰作传\音域分析\网易云补_单曲')]
seen, rows = set(), []
for r in roots:
    for f in sorted(r.glob('*.mp3')):
        t = f.stem
        if t in seen: continue
        seen.add(t)
        try:
            b = bpm_of(f)
            rows.append((t, b))
        except Exception:
            pass
rows.sort(key=lambda r: -r[1])
print('可测', len(rows))
print('最快 8:', rows[:8])
print('最慢 8:', rows[-8:])
ge = [r for r in rows if r[1] >= 130]
print(f'≥130: {len(ge)}/{len(rows)} = {len(ge)/len(rows)*100:.0f}%')
print('中位', round(float(np.median([r[1] for r in rows])), 1))
for n, b in rows:
    if n in ('火光', '暗潮涌动', '埋下记忆'):
        print('检查', n, b)
json.dump(rows, open(r'D:\wx409.github.io\data\research\singles_bpm.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
