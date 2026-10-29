import os, shutil, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
tmp = Path(r'E:\wx\收听人数（2026.7.24）_tmp.xlsx')
dst = Path(r'E:\wx\收听人数（2026.7.24）_含火光.xlsx')
if tmp.exists():
    if dst.exists():
        dst.unlink()
    tmp.rename(dst)
print('清单副本:', dst.exists(), dst.stat().st_size if dst.exists() else 0)

GEN = [Path(r'E:\wx\QQ音乐大屏生成器_GEO优化版_源码.py'),
       Path(r'D:\wx409.github.io\project_b\QQ音乐大屏生成器_GEO优化版_源码.py')]
old = 'EXCEL_INPUT = r"收听人数（2026.7.24）.xlsx"      # 链接清单'
new = ('EXCEL_INPUT = r"收听人数（2026.7.24）.xlsx"      # 链接清单\n'
       '# 若有追加过新歌的副本（主文件被 Excel 占用时使用），优先读它\n'
       '_EXCEL_ALT = r"收听人数（2026.7.24）_含火光.xlsx"\n'
       'if os.path.exists(_EXCEL_ALT):\n'
       '    EXCEL_INPUT = _EXCEL_ALT')
for g in GEN:
    s = g.read_text(encoding='utf-8')
    if '_EXCEL_ALT' in s:
        print('已存在', g); continue
    assert s.count(old) == 1, g
    g.write_text(s.replace(old, new), encoding='utf-8')
    print('已改', g)
