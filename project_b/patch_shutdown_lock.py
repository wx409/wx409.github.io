import sys, time
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
p = Path(r'D:\wx409.github.io\project_b\night_shutdown_gate.py')
s = p.read_text(encoding='utf-8')

anchor = 'LOG = Path(r"E:\\wx\\私有工具\\night_shutdown_log.jsonl")'
add = anchor + '\n# 长任务锁：存在且未过期（8 小时）时一律不关机，避免跑分析时被关机打断\nLONGJOB_LOCK = Path(r"D:\\wx409.github.io\\temp\\longjob.lock")\nLONGJOB_TTL_H = 8\n\n\ndef longjob_active() -> bool:\n    try:\n        if not LONGJOB_LOCK.exists():\n            return False\n        age_h = (time.time() - LONGJOB_LOCK.stat().st_mtime) / 3600\n        return age_h < LONGJOB_TTL_H\n    except Exception:\n        return False\n'
assert s.count(anchor) == 1
s = s.replace(anchor, add)

# 在 main 判定前插入保险
old = 'def main() -> int:'
new = '''def main() -> int:
    if longjob_active():
        print("检测到长任务锁 temp/longjob.lock（8 小时内），本次不关机")
        return 0
'''
assert s.count(old) == 1
s = s.replace(old, new)
if 'import time' not in s.split('import subprocess')[0]:
    s = s.replace('import subprocess', 'import subprocess\nimport time', 1)
p.write_text(s, encoding='utf-8')
print('关机闸门已加长任务锁')

lock = Path(r'D:\wx409.github.io\temp\longjob.lock')
lock.parent.mkdir(parents=True, exist_ok=True)
lock.write_text('live analysis 2026-10-28 三场 58 曲\n', encoding='utf-8')
print('锁文件已创建:', lock)
