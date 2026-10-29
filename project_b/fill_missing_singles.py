import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
OUT = Path(r'E:\wx\论文素材_王晰作传\音域分析\网易云补_单曲')
OUT.mkdir(parents=True, exist_ok=True)
inv = json.load(open(r'D:\wx409.github.io\data\singles_inventory.json', encoding='utf-8'))['rows']
an = {s['title'] for s in json.load(open(r'D:\wx409.github.io\data\research\singles_analysis.json', encoding='utf-8'))['songs']}
miss = [r['name'] for r in inv if r['name'] not in an and not any(r['name'] in t for t in an)]
UA = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://music.163.com/'}

def search(name):
    q = urllib.parse.quote(f'王晰 {name}')
    u = f'https://music.163.com/api/search/get?s={q}&type=1&limit=10'
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20) as r:
        d = json.loads(r.read().decode('utf-8'))
    return ((d.get('result') or {}).get('songs') or [])

got = 0
for name in miss:
    dst = OUT / f'{name}.mp3'
    if dst.exists() and dst.stat().st_size > 200_000:
        continue
    try:
        songs = search(name)
    except Exception as e:
        print('搜索失败', name); continue
    best = None
    for s in songs:
        singers = ' '.join(a.get('name', '') for a in (s.get('artists') or []))
        if '王晰' in singers and (name in s.get('name', '') or s.get('name', '') in name):
            best = s; break
    if not best:
        print('未命中', name); time.sleep(0.3); continue
    url = f"https://music.163.com/song/media/outer/url?id={best['id']}.mp3"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            data = r.read()
        if len(data) < 200_000:
            print('过小', name, len(data)); continue
        dst.write_bytes(data); got += 1
        print('OK', name, round(len(data) / 1e6, 1), 'MB')
    except Exception as e:
        print('失败', name, repr(e)[:50])
    time.sleep(0.4)
print('新增', got, '｜仍缺', len([n for n in miss if not (OUT / f'{n}.mp3').exists()]))
