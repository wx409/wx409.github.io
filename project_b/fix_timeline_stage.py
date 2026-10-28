import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')

# 1) 页面：stage 不在阶段白名单时，按年份推断（否则整条被静默丢弃）
p = ROOT / 'timeline.html'
s = p.read_text(encoding='utf-8')
old = """            if (t.stage) return t.stage;"""
new = """            if (t.stage && STAGES.some(function (s) { return s.key === t.stage; })) return t.stage;"""
assert s.count(old) == 1
p.write_text(s.replace(old, new), encoding='utf-8')
print('timeline.html 已修：非法 stage 回退按年份')

# 2) 数据：清掉不是阶段的 stage 值
t = ROOT / 'data' / 'timeline.json'
tl = json.loads(t.read_text(encoding='utf-8'))
KEYS = {'背景', '奠基', '海政', '乐华', '东演'}
fixed = 0
for e in tl:
    if e.get('stage') and e['stage'] not in KEYS:
        e.pop('stage')
        fixed += 1
t.write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding='utf-8')
print('timeline.json 清理非法 stage', fixed, '条')
print('火光:', [e for e in tl if '火光' in e.get('title', '')])
