#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 works.html 生成「正式单曲 / OST 实测」区块（只报音级，不报 Hz 精度）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import median

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
DATA = ROOT / 'data' / 'research' / 'singles_analysis.json'
HTML = ROOT / 'works.html'
OUT = ROOT / 'data' / 'singles_summary.json'
START, END = '<!-- SINGLES_START -->', '<!-- SINGLES_END -->'

songs = json.loads(DATA.read_text(encoding='utf-8'))['songs']
rows = []
for s in songs:
    low = s.get('low_stable') or {}
    if not low.get('note'):
        continue
    rows.append({"title": s['title'], "note": low['note'],
                 "span": round(s.get('span_octaves') or 0, 2),
                 "stab": round(s.get('stability_cents_median') or 0, 1)})
def low_order(note: str) -> int:
    names = {'C': 0, 'C#': 1, 'D': 2, 'D#': 3, 'E': 4, 'F': 5, 'F#': 6,
             'G': 7, 'G#': 8, 'A': 9, 'A#': 10, 'B': 11}
    n = note[:-1].replace('♯', '#')
    try:
        return names[n] + 12 * int(note[-1])
    except Exception:
        return 99

seen = set()
uniq = []
for r in rows:
    if r['title'] in seen:
        continue
    seen.add(r['title'])
    uniq.append(r)
rows = uniq
rows.sort(key=lambda r: (low_order(r['note']), r['title']))




summary = {"schema": "singles_summary/v1", "count": len(rows),
           "lowest_note_median": median([low_order(r['note']) for r in rows]),
           "top10": rows[:10]}
OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')

top = rows[:10]
trs = ''.join(
    f"<tr><td>{i+1}</td><td>{r['title']}</td><td class='n'>{r['note']}</td>"
    f"<td class='n'>{r['span']}</td><td class='n'>{r['stab']}</td></tr>"
    for i, r in enumerate(top))
block = f"""{START}
<h2>二之二、正式单曲 / OST 实测（{len(rows)} 首已测）</h2>
<p>与专辑不同，单曲与 OST 的主导权常在制作人与剧方：它们更能说明<strong>他的声音被怎样使用</strong>，
而不只是他自己想唱什么。下表只报<strong>音级</strong>——单曲多为 320k 有损，频率精度低于无损素材，故不报 Hz。</p>
<table><tr><th>#</th><th>曲目</th><th>最低音</th><th>跨度（八度）</th><th>稳定性（音分）</th></tr>{trs}</table>
<p class="src">按最低音排序，展示前 10 首；已测 {len(rows)} 首。数据源：
<a href="/data/singles_summary.json">data/singles_summary.json</a>（摘要）与
<a href="/data/research/singles_analysis.json">data/research/singles_analysis.json</a>（逐曲全量）。</p>
<p class="src">口径：稳定音（≥0.15s、HNR≥5dB、极值音本身≥0.2s）；未做逐曲谐波复核的读数不作能力断言。</p>
{END}"""

html = HTML.read_text(encoding='utf-8')
if START in html and END in html:
    a = html.index(START); b = html.index(END) + len(END)
    html = html[:a] + block + html[b:]
else:
    anchor = '<h2>三、怎么读这张表</h2>'
    assert anchor in html
    html = html.replace(anchor, block + '\n\n' + anchor, 1)
HTML.write_text(html, encoding='utf-8')
print(f'works.html 已注入单曲区块：{len(rows)} 首，展示前 {len(top)}')
