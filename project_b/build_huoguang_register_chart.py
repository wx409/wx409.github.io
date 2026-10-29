import json, sys
from pathlib import Path
from statistics import median
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
S = json.load(open(r'D:\wx409.github.io\data\research\singles_analysis.json', encoding='utf-8'))['songs']
h = next(s for s in S if '火光' in s['title'])['register_share']
keys = ['low_lt_C3', 'mid_C3_B3', 'high_ge_C4']
labels = ['C3 以下（低音区）', 'C3–B3（中音区）', 'C4 以上（高音区）']
cat = [median([s['register_share'][k] for s in S if s.get('register_share')]) * 100 for k in keys]
fire = [h[k] * 100 for k in keys]
fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
x = range(3)
ax.bar([i - 0.2 for i in x], cat, width=0.4, label='他的 84 首单曲/OST 平均', color='#999')
ax.bar([i + 0.2 for i in x], fire, width=0.4, label='《火光》', color='#c41e3a')
for i, v in enumerate(cat):
    ax.text(i - 0.2, v + 1.5, f'{v:.1f}%', ha='center', fontsize=9)
for i, v in enumerate(fire):
    ax.text(i + 0.2, v + 1.5, f'{v:.1f}%', ha='center', fontsize=9, color='#c41e3a')
ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=10)
ax.set_ylabel('音符占比（%）')
ax.set_title('《火光》里他几乎没唱低音：高音区占比是平时的 3.6 倍')
ax.legend(fontsize=9)
ax.grid(axis='y', alpha=0.25, linestyle='--')
fig.tight_layout()
out = Path(r'D:\wx409.github.io\dashboard\video_huoguang_register.png')
fig.savefig(out)
print('图已生成', out, round(out.stat().st_size / 1024), 'KB')
