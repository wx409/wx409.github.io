import subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'E:\wx\论文素材_王晰作传\现场录音-小卡带'
EXE = r'E:\wx\论文素材_王晰作传\音域分析\批量专辑音域.py'
shows = [
    '20191116 一巡·“Cherish珍晰”王晰2019全国巡回音乐会·海口',
    '20240127 四巡·“肆益”个人巡回音乐会·南京',
    '20241221 五巡·王晰吾个人巡回音乐会·杭州（首场）',
]
for s in shows:
    print('=== 开始', s, flush=True)
    r = subprocess.run([sys.executable, '-X', 'utf8', EXE, '--root', ROOT, '--albums', s],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    tail = (r.stdout or '').strip().splitlines()[-3:]
    print('\n'.join(tail), flush=True)
    if r.returncode != 0:
        print('失败:', (r.stderr or '')[-300:], flush=True)
print('全部结束', flush=True)
