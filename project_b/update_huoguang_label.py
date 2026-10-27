import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
p = Path(r'D:\wx409.github.io\data\songs_meta.json')
raw = json.loads(p.read_text(encoding='utf-8'))
song = raw['songs']['火光']
song['label'] = 'Columbia Records China X 韶愔音乐娱乐'
song['type'] = 'single'
song['official_intro'] = (
    '《火光》由王晰演唱，Bryan 作词作曲，并担任制作人。'
    '王晰以低沉深邃独特声线，赋予整首歌曲极强张力与格局。'
    '由暗境开篇，在漫天尘埃与迷雾困顿之中，揭开绝境之下的坚守与共生。'
    '命运倾覆、前路遍布荒芜，但依旧有人并肩而立，互为依托。'
    '以热血为新，以信仰为炬，于荒芜岁月里生生不息，绽放永不熄灭的灼灼火光。'
)
song['official_intro_source'] = '官方发行文案（用户提供，2026-10-27）'
p.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding='utf-8')
print('已补：label / type / 官方文案')

t = Path(r'D:\wx409.github.io\data\timeline.json')
tl = json.loads(t.read_text(encoding='utf-8'))
for e in tl:
    if '火光' in e.get('title', ''):
        e['source'] = ('官方发行信息：Columbia Records China X 韶愔音乐娱乐；'
                       '制作 The U.M.C / 出品 韶愔音乐娱乐（用户提供）')
        break
t.write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding='utf-8')
print('时间轴出处已补唱片公司')
