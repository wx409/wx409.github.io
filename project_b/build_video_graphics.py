import json, sys
from pathlib import Path
import numpy as np, soundfile as sf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

sys.stdout.reconfigure(encoding='utf-8')
for fp in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf'):
    if Path(fp).exists():
        font_manager.fontManager.addfont(fp)
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=fp).get_name()
        break
plt.rcParams['axes.unicode_minus'] = False
OUT = Path(r'D:\wx409.github.io\dashboard')
OUT.mkdir(exist_ok=True)

# 图1：音高尺
fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
notes = [('男低音下限 E2', 82.4, '#888'), ('王晰现场最低稳定 C2', 65.2, '#c41e3a'),
         ('王晰录音室最低 B1', 61.5, '#a8323d')]
for i, (label, hz, color) in enumerate(notes):
    ax.barh(i, hz, color=color, height=0.5)
    ax.text(hz + 1.2, i, f'{hz} Hz', va='center', fontsize=11)
ax.set_yticks(range(len(notes)))
ax.set_yticklabels([n[0] for n in notes], fontsize=11)
ax.set_xlim(40, 95)
ax.set_xlabel('频率（Hz）')
ax.set_title('61.5Hz 是什么概念：比男低音的"底线"还低一个大三度')
ax.grid(axis='x', alpha=0.25, linestyle='--')
fig.tight_layout()
fig.savefig(OUT / 'video_pitch_ladder.png')
print('图1 完成')

# 图2：15 秒长句的能量包络 + 气口标注
P = r'E:\wx\论文素材_王晰作传\现场录音-补充\xyy_vocals_6s.wav'
x, sr = sf.read(P, dtype='float32', always_2d=True); m = x.mean(axis=1)
t0, dur = 247.4, 15.2
a = int(t0 * sr); seg = m[a:a + int(dur * sr)]
hop = int(0.01 * sr); win = int(0.03 * sr)
n = (len(seg) - win) // hop
frames = np.lib.stride_tricks.sliding_window_view(seg, win)[np.arange(n) * hop]
db = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-12)
t = np.arange(n) * 0.01
fig, ax = plt.subplots(figsize=(8, 3.2), dpi=150)
ax.plot(t, db, color='#c41e3a', linewidth=1.2)
med = float(np.median(db))
ax.axhline(med - 12, color='#888', linestyle='--', linewidth=1, label='断点阈值（中位−12dB）')
ax.annotate('气口：仅低 12–20dB\n0.7–1.0 秒', xy=(14.3, db[int(14.3 * 100)] if int(14.3 * 100) < n else db[-1]),
            xytext=(9.5, med - 26), fontsize=10,
            arrowprops=dict(arrowstyle='->', color='#333'))
ax.set_xlabel('秒（那句"15 秒不换气"）')
ax.set_ylabel('能量 dBFS')
ax.set_title('为什么你听不出他换气：气口只压低 12–20 dB')
ax.legend(fontsize=9, loc='lower right')
fig.tight_layout()
fig.savefig(OUT / 'video_breath_envelope.png')
print('图2 完成')
