import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')

# 1) 火光歌词片段（只存片段，遵守版权口径）
p = ROOT / 'tavern' / 'lyrics_fragments.json'
d = json.loads(p.read_text(encoding='utf-8'))
if '火光' not in d:
    d['火光'] = {"fragments": [
        {"text": "在命运的废墟之上，披上不可一世的装", "moods": ["决绝", "力量"], "source": "歌词《火光》"},
        {"text": "燃尽了血泪，也要化作火光无悔这一场", "moods": ["热血", "坚守"], "source": "歌词《火光》"},
    ]}
    meta = d.get('_meta') or {}
    meta['description'] = meta.get('description', '').replace('42 首', '43 首')
    d['_meta'] = meta
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    print('已为《火光》补歌词片段')
else:
    print('火光片段已存在')

# 2) songs 页统计改为 lyric_frags
q = ROOT / 'songs.html'
s = q.read_text(encoding='utf-8')
s = s.replace("var lyr = songs.filter(function (s) { return s.lyrics && s.lyrics.length; }).length;",
              "var lyr = songs.filter(function (s) { return s.lyric_frags && s.lyric_frags.length; }).length;")
s = s.replace("' 首有歌词 · '", "' 首含歌词片段 · '")
q.write_text(s, encoding='utf-8')
print('songs.html 统计改为 lyric_frags')

# 3) 停用全文同步脚本（避免再犯）
sy = ROOT / 'project_b' / 'sync_lyrics.py'
if sy.exists():
    txt = sy.read_text(encoding='utf-8')
    txt = txt.replace('"""把 albums.json 的歌词/制作名单同步到 songs_meta.json（单一事实源：专辑库）。',
                      '"""【已停用】原意：把 albums.json 全文歌词同步到 songs_meta。\n\n'
                      '停用原因：songs_meta 只允许存歌词片段（版权口径，见 build_songs_meta.py 注释）；\n'
                      '全文歌词不得进入公开 JSON。保留脚本仅作记录，默认不执行。')
    sy.write_text(txt, encoding='utf-8')
    print('sync_lyrics.py 已标注停用')
