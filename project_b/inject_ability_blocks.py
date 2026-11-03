#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「能力主线」区块注入 voice.html 与 live.html（幂等，靠标记替换）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
d = json.loads((ROOT / 'data' / 'ability_highlights.json').read_text(encoding='utf-8'))
S, C, L, V = d['stability'], d['cross_version']['examples'][0], d['long_phrase'], d['live_vs_studio']
years = S['by_year']


def block_voice() -> str:
    return f"""<!-- ABILITY_START -->
<section style="margin:26px 0;padding:18px 20px;background:#faf7f7;border-left:5px solid #c41e3a;border-radius:6px">
<h2 style="margin:.2em 0 .4em;border:0;padding:0">他强在哪：三条可验证的能力</h2>
<p style="margin:.2em 0 1em;color:#666;font-size:14px">口径：差距远大于测量误差，才算结论。三条都不是极值，是稳定表现。</p>
<table style="border-collapse:collapse;width:100%;font-size:14.5px">
<tr><td style="padding:8px 10px;border:1px solid #e5e5e5;width:120px"><b style="font-size:20px;color:#c41e3a">{S['all_shows_median_cents']}</b> 音分</td>
<td style="padding:8px 10px;border:1px solid #e5e5e5">长音<b>内部</b>的抖动（37 场中位）。一个半音是 100 音分——他一个长音只抖约 1/14 个半音。</td></tr>
<tr><td style="padding:8px 10px;border:1px solid #e5e5e5"><b style="font-size:20px;color:#c41e3a">{C['range']}</b> 半音</td>
<td style="padding:8px 10px;border:1px solid #e5e5e5">《{C['song']}》{C['n']} 个已核版本，同一目标段最低音的极差。换场次、换状态，落点还能重合。</td></tr>
<tr><td style="padding:8px 10px;border:1px solid #e5e5e5"><b style="font-size:20px;color:#c41e3a">{L['seconds']}</b> 秒</td>
<td style="padding:8px 10px;border:1px solid #e5e5e5">《{L['song']}》那句一气呵成的长度；气口只有 {L['breath_gap_s'][0]}–{L['breath_gap_s'][1]} 秒、比演唱低 {L['breath_gap_db'][0]}–{L['breath_gap_db'][1]} dB。</td></tr>
</table>
<p style="margin:.8em 0 0;color:#555;font-size:14px">换句话说：<b>他不只是"能唱低"——低到 B1 之后，声音还能稳住、还能听清。</b></p>
</section>
<!-- ABILITY_END -->"""


def block_live() -> str:
    yrows = ''.join(f"<tr><td style='padding:6px 10px;border:1px solid #e5e5e5'>{y}</td>"
                    f"<td style='padding:6px 10px;border:1px solid #e5e5e5;text-align:right'>{v}</td></tr>"
                    for y, v in sorted(years.items()))
    return f"""<!-- ABILITY_START -->
<section style="margin:26px 0;padding:18px 20px;background:#faf7f7;border-left:5px solid #c41e3a;border-radius:6px">
<h2 style="margin:.2em 0 .4em;border:0;padding:0">现场真正的强项：稳、复现、克制</h2>
<p style="margin:.2em 0 1em;color:#666;font-size:14px">现场不比"最低音"，比"每一场都能做到"。</p>
<table style="border-collapse:collapse;width:100%;font-size:14.5px">
<tr><td style="padding:8px 10px;border:1px solid #e5e5e5;width:150px"><b style="font-size:20px;color:#c41e3a">{S['all_shows_median_cents']}</b> 音分</td>
<td style="padding:8px 10px;border:1px solid #e5e5e5">37 场长音抖动的中位——现场、非修音。</td></tr>
<tr><td style="padding:8px 10px;border:1px solid #e5e5e5"><b style="font-size:20px;color:#c41e3a">{C['range']}</b> 半音</td>
<td style="padding:8px 10px;border:1px solid #e5e5e5">《{C['song']}》{C['n']} 个版本的落点极差：同一首歌，跨场几乎不变。</td></tr>
<tr><td style="padding:8px 10px;border:1px solid #e5e5e5"><b style="font-size:20px;color:#c41e3a">{abs(V['db'])}</b> 分贝</td>
<td style="padding:8px 10px;border:1px solid #e5e5e5">《{V['song']}》现场比录音室<b>更轻</b>（{V['centroid_studio']}→{V['centroid_live']}Hz 更暗），没有靠推音量。</td></tr>
</table>
<h3 style="margin:1.2em 0 .3em;font-size:15px">五年稳定性（音分，越小越稳）</h3>
<table style="border-collapse:collapse;width:auto;font-size:14px">{yrows}</table>
</section>
<!-- ABILITY_END -->"""


def inject(path: Path, block: str) -> bool:
    s = path.read_text(encoding='utf-8')
    if '<!-- ABILITY_START -->' in s:
        a = s.index('<!-- ABILITY_START -->')
        b = s.index('<!-- ABILITY_END -->') + len('<!-- ABILITY_END -->')
        s = s[:a] + block + s[b:]
    else:
        # 插到第一个 <h1> 之后
        i = s.find('</h1>')
        if i < 0:
            print('未找到 h1，跳过', path.name); return False
        s = s[:i+5] + '\n' + block + s[i+5:]
    path.write_text(s, encoding='utf-8')
    return True


ok1 = inject(ROOT / 'voice.html', block_voice())
ok2 = inject(ROOT / 'live.html', block_live())
print('注入 voice', ok1, '｜live', ok2)
