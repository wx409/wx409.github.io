import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')

# 1) 旧机制（生成器 23:55）保护：shutdown_skip.txt 全周列名 → 命中即不关机
skip = ROOT / 'project_b' / 'shutdown_skip.txt'
skip.write_text('\n'.join(['周一', '周二', '周三', '周四', '周五', '周六', '周日']) + '\n', encoding='utf-8')
print('shutdown_skip.txt 已写全周（旧路径不关机）')

# 2) 生成器 schedule_shutdown 也加长任务锁判断
p = ROOT / 'project_b' / 'QQ音乐大屏生成器_GEO优化版_源码.py'
s = p.read_text(encoding='utf-8')
old = 'def schedule_shutdown():\n    now = datetime.now()'
new = ('def schedule_shutdown():\n'
       '    # 长任务锁：有分析在跑就不关机\n'
       '    _lock = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp", "longjob.lock")\n'
       '    try:\n'
       '        if os.path.exists(_lock) and (time.time() - os.path.getmtime(_lock)) < 8 * 3600:\n'
       '            logger.info("检测到长任务锁，跳过自动关机")\n'
       '            return\n'
       '    except Exception:\n'
       '        pass\n'
       '    now = datetime.now()')
assert s.count(old) == 1
p.write_text(s.replace(old, new), encoding='utf-8')
print('生成器 schedule_shutdown 已加锁判断')
