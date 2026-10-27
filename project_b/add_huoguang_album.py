import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
p = Path(r'D:\wx409.github.io\data\albums.json')
d = json.loads(p.read_text(encoding='utf-8'))
if not any(a.get('name') == '火光' for a in d['albums']):
    d['albums'].append({
        "name": "火光",
        "release": "2026-10",
        "release_date": "2026-10-27",
        "kind": "single",
        "label": "Columbia Records China X 韶愔音乐娱乐",
        "songs": [{
            "title": "火光",
            "singer": "王晰",
            "credits": {
                "作词": "Bryan（孙伟）", "作曲": "Bryan（孙伟）", "制作人": "Bryan（孙伟）",
                "编曲": "刘苏毅@U.M.C", "吉他/贝斯": "刘苏毅@U.M.C",
                "配唱制作人": "胡宸@U.M.C", "制作统筹": "胡宸@U.M.C",
                "和声": "海青", "混音/母带": "王路遥", "音乐制作": "The U.M.C",
                "人声录音": "吕自雯", "录音棚": "韶愔音乐 Studio",
                "总监制": "王锋", "音乐总监": "丁爽",
                "OP": "韶愔音乐娱乐（北京）有限公司",
                "音乐出品发行": "韶愔音乐娱乐（北京）有限公司",
            },
            "official_intro": "由暗境开篇，在漫天尘埃与迷雾困顿之中，揭开绝境之下的坚守与共生。",
        }],
        "source": "官方发行信息（用户提供，2026-10-27）",
        "release_source": "官方发行信息",
    })
    p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    print('已加入 albums.json：火光（single）')
else:
    print('已存在')

# 统计口径：单曲不计入“录音室作品数”
albums = [a for a in d['albums'] if a.get('kind') != 'single']
print('录音室专辑/EP 数（不含单曲）:', len(albums))
