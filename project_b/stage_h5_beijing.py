import os, sys, subprocess
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
SRC = Path(r'H:\王晰巡演素材存档\现场录制视频\四巡\2023.11.12北京第1场')
STAGE = Path(r'E:\wx\论文素材_王晰作传\_staging_现场')
TAG = 'h5_bj_20231112'
dst = STAGE / TAG
dst.mkdir(parents=True, exist_ok=True)
added = 0
for f in sorted(SRC.glob('*.flac')):
    if '(2)' in f.name or ' ' == f.name.strip():
        continue
    t = dst / f.name
    if t.exists():
        continue
    try:
        os.link(f, t)
    except Exception:
        import shutil; shutil.copy2(f, t)
    added += 1
print('就位', added, '个 FLAC →', dst)
r = subprocess.run([sys.executable, '-X', 'utf8',
                    r'E:\wx\论文素材_王晰作传\音域分析\批量专辑音域.py',
                    '--root', str(STAGE), '--albums', TAG],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
print('\n'.join((r.stdout or '').strip().splitlines()[-5:]))
if r.returncode != 0:
    print('错误', (r.stderr or '')[-300:])
