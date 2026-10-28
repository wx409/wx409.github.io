import subprocess, sys
sys.stdout.reconfigure(encoding='utf-8')
EXE = r'E:\wx\论文素材_王晰作传\音域分析\批量专辑音域.py'
ROOT = r'E:\wx\论文素材_王晰作传\_staging_现场'
for tag in ('haikou_20191116', 'nanjing_20240127', 'hangzhou_20241221'):
    print('=== 开始', tag, flush=True)
    r = subprocess.run([sys.executable, '-X', 'utf8', EXE, '--root', ROOT, '--albums', tag],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (r.stdout or '').strip().splitlines()
    print('\n'.join(out[-4:]), flush=True)
    if r.returncode != 0:
        print('失败:', (r.stderr or '')[-300:], flush=True)
print('三场全部结束', flush=True)
