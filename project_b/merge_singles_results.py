import json, sys
from pathlib import Path
from statistics import median
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
srcs = [r'E:\wx\论文素材_王晰作传\单曲音频_汇总.json', r'E:\wx\论文素材_王晰作传\音域分析_汇总.json']
songs, seen = [], set()
for p in srcs:
    try:
        for s in json.load(open(p, encoding='utf-8'))['songs']:
            t = s['title']
            if t in seen:
                continue
            seen.add(t); songs.append(s)
    except Exception as e:
        print('跳过', p, e)
(ROOT / 'data/research/singles_analysis.json').write_text(
    json.dumps({"schema": "singles_analysis/v1", "count": len(songs), "songs": songs},
               ensure_ascii=False, indent=1), encoding='utf-8')
rows = [(s['title'], s.get('stability_cents_median')) for s in songs if s.get('stability_cents_median') is not None]
rows.sort(key=lambda r: r[1])
print('合计已测', len(songs), '｜有稳定性', len(rows), '｜稳定性中位', round(median([r[1] for r in rows]), 2))
rank = [i for i, r in enumerate(rows, 1) if '火光' in r[0]]
print('火光', [(r[0], r[1]) for r in rows if '火光' in r[0]], '｜排名', rank, '/', len(rows))
print('最稳 5:', [(r[0][:10], r[1]) for r in rows[:5]])
