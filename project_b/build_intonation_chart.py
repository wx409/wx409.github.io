import json, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
d = json.loads((ROOT / 'data' / 'research' / 'live_intonation.json').read_text(encoding='utf-8'))
shows = d['shows']

# 中文字体
for fp in (r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf'):
    if Path(fp).exists():
        font_manager.fontManager.addfont(fp)
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=fp).get_name()
        break
plt.rcParams['axes.unicode_minus'] = False

years = sorted({s['year'] for s in shows})
fig, ax = plt.subplots(figsize=(9, 4.8), dpi=140)
for i, y in enumerate(years):
    ys = [s['intonation_med'] for s in shows if s['year'] == y]
    xs = [i + (j - (len(ys) - 1) / 2) * 0.08 for j in range(len(ys))]
    ax.scatter(xs, ys, s=28, alpha=0.75, label=f'{y}（{len(ys)} 场）')
    ax.hlines(sum(ys) / len(ys), i - 0.3, i + 0.3, colors='#c41e3a', linewidth=2)
ax.set_xticks(range(len(years)))
ax.set_xticklabels(years)
ax.set_ylabel('音准偏差中位（音分）')
ax.set_title('王晰 37 场现场：音准偏差五年基本持平（红=年度均值）')
ax.grid(alpha=0.25, linestyle='--')
ax.legend(fontsize=8, ncol=len(years), loc='upper center', bbox_to_anchor=(0.5, -0.12))
fig.tight_layout()
out = ROOT / 'dashboard' / 'live_intonation_37.png'
out.parent.mkdir(exist_ok=True)
fig.savefig(out)
print('图已生成', out, round(out.stat().st_size / 1024), 'KB')
