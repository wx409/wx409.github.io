import os, sys, subprocess, json
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
STAGE = Path(r'E:\wx\论文素材_王晰作传\_staging_现场')
rep = json.load(open(r'D:\wx409.github.io\temp\h5_split_report.json', encoding='utf-8'))
EXE = r'E:\wx\论文素材_王晰作传\音域分析\批量专辑音域.py'
for tag, rows in rep.items():
    ok = [r for r in rows if 45 <= r['dur'] <= 720]
    dst = STAGE / (tag + '_ok')
    dst.mkdir(parents=True, exist_ok=True)
    for r in ok:
        src = STAGE / tag / r['file']
        t = dst / r['file']
        if src.exists() and not t.exists():
            try: os.link(src, t)
            except Exception:
                import shutil; shutil.copy2(src, t)
    print(tag, '就位', len(list(dst.glob('*.wav'))), '段', flush=True)
    r = subprocess.run([sys.executable, '-X', 'utf8', EXE, '--root', str(STAGE), '--albums', tag + '_ok'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    tail = (r.stdout or '').strip().splitlines()[-2:]
    print('\n'.join(tail), flush=True)
