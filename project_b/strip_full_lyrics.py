import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')

# 1) 清除 songs_meta 里的全文歌词字段（版权口径：只留片段）
p = ROOT / 'data' / 'songs_meta.json'
raw = json.loads(p.read_text(encoding='utf-8'))
stripped = 0
for name, rec in raw['songs'].items():
    if rec.get('lyrics'):
        rec.pop('lyrics')
        stripped += 1
p.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding='utf-8')
print('songs_meta 移除全文歌词字段', stripped, '首')

# 2) 头部计数改为 lyric_frags
q = ROOT / 'project_b' / 'update_songs_meta_tags.py'
s = q.read_text(encoding='utf-8')
s = s.replace("lyr = sum(1 for s in data.values() if s.get('lyrics'))",
              "lyr = sum(1 for s in data.values() if s.get('lyric_frags'))")
q.write_text(s, encoding='utf-8')
print('update_songs_meta_tags 改为统计片段')
