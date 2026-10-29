import json, sys, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
UA = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://y.qq.com/'}

# 1) 解析 mid
sid = 634191218
u = f'https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg?songid={sid}&format=json&platform=yqq'
with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=15) as r:
    d = json.loads(r.read().decode('utf-8', 'replace'))
info = (d.get('data') or [{}])[0]
print('mid', info.get('mid'), '| album', (info.get('album') or {}).get('name'), '| 发行', info.get('time_public'))

# 2) 更新 songs_meta
sm_path = ROOT / 'data' / 'songs_meta.json'
raw = json.loads(sm_path.read_text(encoding='utf-8'))
songs = raw['songs']
rec = songs.get('埋下记忆')
if rec is None:
    print('songs_meta 无此曲')
else:
    rec['release'] = '2026-01-14'
    rec['album'] = (info.get('album') or {}).get('name') or rec.get('album')
    if info.get('mid'):
        rec['mid'] = info['mid'].replace('L:', '')
    sm_path.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding='utf-8')
    print('songs_meta 已更新：埋下记忆 release=2026-01-14')

# 3) albums.json 里的单曲条目补 mid/发行日
alb_path = ROOT / 'data' / 'albums.json'
alb = json.loads(alb_path.read_text(encoding='utf-8'))
for a in alb.get('albums', []):
    for s in (a.get('songs') or []):
        if s.get('title') == '埋下记忆':
            s['mid'] = (info.get('mid') or '').replace('L:', '')
            s['release_date'] = '2026-01-14'
            print('albums.json 已补')
alb_path.write_text(json.dumps(alb, ensure_ascii=False, indent=1), encoding='utf-8')
