import json, re, sys
from collections import defaultdict
from statistics import median
sys.stdout.reconfigure(encoding='utf-8')
S = json.load(open(r'E:\wx\论文素材_王晰作传\_staging_现场_汇总.json', encoding='utf-8'))['songs']

def date_of(a):
    m = re.search(r'(\d{8})', a)
    return m.group(1) if m else ''

def year_of(a):
    d = date_of(a)
    return d[:4] if d else ''

def tour_of(y):
    return {'2019': '一巡', '2020': '二巡', '2021': '三巡(2021)', '2022': '三巡(2022)',
            '2023': '四巡(2023)', '2024': '四/五巡(2024)'}.get(y, y)

# 去重：同日期保留 s 前缀
seen = {}
for s in S:
    d = date_of(s['album'])
    if d not in seen or (s['album'].startswith('s') and not seen[d]['album'].startswith('s')):
        seen[d] = {"album": s['album'], "songs": []}
    if seen[d]['album'] == s['album']:
        seen[d]['songs'].append(s)

rows = []
for d, g in sorted(seen.items()):
    ints = [x['intonation_cents_median'] for x in g['songs'] if x.get('intonation_cents_median') is not None]
    stabs = [x['stability_cents_median'] for x in g['songs'] if x.get('stability_cents_median') is not None]
    if not ints:
        continue
    rows.append({"date": f"{d[:4]}-{d[4:6]}-{d[6:]}", "year": d[:4],
                 "n": len(g['songs']),
                 "intonation_med": round(median(ints), 1),
                 "intonation_p90": round(sorted(ints)[int(len(ints) * 0.9) - 1], 1),
                 "stability_med": round(median(stabs), 1)})

by_year = defaultdict(list)
for r in rows:
    by_year[r['year']].append(r)
print('场次', len(rows))
for y in sorted(by_year):
    a = by_year[y]
    print(f"{y}｜{len(a):2d} 场｜音准中位 {median([x['intonation_med'] for x in a]):5.1f} 音分｜场间极差 {max(x['intonation_med'] for x in a)-min(x['intonation_med'] for x in a):5.1f}")
json.dump({"shows": rows, "by_year": {y: len(v) for y, v in by_year.items()}},
          open(r'D:\wx409.github.io\data\research\live_intonation.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('已写 data/research/live_intonation.json')
