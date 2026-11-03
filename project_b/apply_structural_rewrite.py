import sys, subprocess
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')

# 0) 回退点
subprocess.run(['git', 'tag', '-f', 'pre-ability-rewrite', 'HEAD'], cwd=ROOT, capture_output=True)
subprocess.run(['git', 'push', 'origin', 'pre-ability-rewrite', '--force'], cwd=ROOT, capture_output=True)
print('回退点已建：tag pre-ability-rewrite')

# 1) voice 生成器：把低音主导的三节降为"附"
p = Path(r'E:\wx\论文素材_王晰作传\基线口径\generate_voice_page.py')
s = p.read_text(encoding='utf-8')
reps = [
    ("二、{d['count']} 首歌曲最低稳定音（精确数据）", "附一、最低稳定音档案（存在性证明，非主线）"),
    ("三、低音现场复现：录音室与现场同区", "附二、现场低音复现（档案）"),
    ("六、录音室 vs 现场：现场同样到得了 B1 一带", "附三、录音室 vs 现场：同区复现（档案）"),
]
n = 0
for a, b in reps:
    if a in s and b not in s:
        s = s.replace(a, b); n += 1
p.write_text(s, encoding='utf-8')
print('voice 生成器改写', n, '处')

# 2) live 生成器：标题与一句表述
q = ROOT / 'project_b' / 'build_compact.py'
t = q.read_text(encoding='utf-8')
m = 0
if '<h2>二、现场声学实测（稳定音口径）</h2>' in t:
    t = t.replace('<h2>二、现场声学实测（稳定音口径）</h2>', '<h2>二、现场声学实测（稳定性与复现为主）</h2>'); m += 1
old = '同曲对照显示低音区在现场同样可复现（如《多听有益》现场稳定音 C2 65.3Hz，与录音室 B1 相差约 1 个半音）；'
new = '同曲对照显示低音区在现场同样可复现（同一首歌跨场落点极差可小到 0.14 个半音）；'
if old in t:
    t = t.replace(old, new); m += 1
q.write_text(t, encoding='utf-8')
print('live 生成器改写', m, '处')
