import sys, subprocess
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
p = Path(r'E:\wx\论文素材_王晰作传\基线口径\generate_voice_page.py')
s = p.read_text(encoding='utf-8')
reps = [
    ("四、录音室专辑全量实测（{s['songs']} 曲）", "二、录音室专辑全量实测（{s['songs']} 曲）"),
    ("五、情境对比：他主导时 vs 他人主导时", "三、情境对比：他主导时 vs 他人主导时"),
    ("六之二、低音区动态范围实测（7.1）", "四、低音区动态范围实测（7.1）"),
    ("七、权威点评（央视《经典·咏流传》）", "五、权威点评（央视《经典咏流传》）"),
    ("七、权威点评（央视《经典咏流传》）", "五、权威点评（央视《经典咏流传》）"),
    ("七之二、低音档案", "五之二、低音档案"),
    ("七之三、权威点评与已发表来源", "五之三、权威点评与已发表来源"),
    ("八、公开资料互证", "六、公开资料互证"),
]
n = 0
for a, b in reps:
    if a in s and b not in s:
        s = s.replace(a, b); n += 1
p.write_text(s, encoding='utf-8')
print('voice 编号重排', n, '处')
