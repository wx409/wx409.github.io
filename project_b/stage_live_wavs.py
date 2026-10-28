import os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
B = Path(r'E:\wx\论文素材_王晰作传\现场录音-小卡带')
STAGE = Path(r'E:\wx\论文素材_王晰作传\_staging_现场')
STAGE.mkdir(parents=True, exist_ok=True)

def wavs(show, sub):
    d = B / show
    for x in d.iterdir():
        if x.is_dir() and sub in x.name:
            return sorted([f for f in x.rglob('*') if f.suffix.lower() in ('.wav', '.flac')])
    return []

jobs = [
    ('20191116 一巡·“Cherish珍晰”王晰2019全国巡回音乐会·海口', '纯享版 wav', 'haikou_20191116'),
    ('20240127 四巡·“肆益”个人巡回音乐会·南京', '单曲版（wav）', 'nanjing_20240127'),
    ('20241221 五巡·王晰吾个人巡回音乐会·杭州（首场）', '单曲 （wav）', 'hangzhou_20241221'),
]
for show, sub, tag in jobs:
    files = wavs(show, sub)
    dst = STAGE / tag
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in files:
        t = dst / f.name
        if t.exists():
            continue
        try:
            os.link(f, t)   # 硬链接，不占空间
        except Exception:
            import shutil; shutil.copy2(f, t)
        n += 1
    total = len(list(dst.glob('*')))
    print(f'{tag}: 新增链接 {n}｜共 {total} 个 wav')
