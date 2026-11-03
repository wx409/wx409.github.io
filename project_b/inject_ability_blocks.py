#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「能力主线」区块注入 voice.html 与 live.html（幂等，靠标记替换）。"""
from __future__ import annotations

import json
import re
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




def add_context_column(html: str) -> str:
    """给「附一 最低稳定音」表加一列「语境」（录音室/现场/央视）。"""
    marker = '<th>曲目</th><th>最低稳定音'
    if marker not in html or '<th>语境</th>' in html:
        return html
    html = html.replace(marker, '<th>曲目</th><th>语境</th><th>最低稳定音', 1)
    # 逐行给数据行插入语境单元格（该表以「素材来源」列为第 6 格）
    def fix_row(m):
        row = m.group(0)
        if '<th>' in row:
            return row
        cells = re.findall(r'<td[^>]*>.*?</td>', row, re.S)
        if len(cells) < 4:
            return row
        texts = [re.sub('<[^>]+>', '', c) for c in cells]
        env = None
        for t in texts:
            tags = []
            if '央视' in t:
                tags.append('央视')
            if '现场' in t or '巡演' in t:
                tags.append('现场')
            if '录音室' in t:
                tags.append('录音室')
            if tags:
                env = ' / '.join(dict.fromkeys(tags))
                break
        if env is None:
            env = '录音室' if any(('全曲口径' in t or '人工复核' in t) for t in texts) else '—'
        return row.replace(cells[0], cells[0] + f'<td>{env}</td>', 1)

    # 只处理附一那张表：从 marker 到 </table>
    i = html.find('<th>曲目</th><th>语境</th>')
    j = html.find('</table>', i)
    if i < 0 or j < 0:
        return html
    seg = html[i:j]
    seg2 = re.sub(r'<tr[^>]*>.*?</tr>', fix_row, seg, flags=re.S)
    return html[:i] + seg2 + html[j:]




def block_voice_extra() -> str:
    return """<!-- EXTRA_START -->
<section style="margin:26px 0;padding:18px 20px;background:#f7f7fa;border-left:5px solid #555;border-radius:6px">
<h2 style="margin:.2em 0 .4em;border:0;padding:0">合唱不进榜单；声部不由作品音域判定</h2>
<p style="margin:.2em 0 .8em;color:#666;font-size:14px">两条口径说明，都是为了不拿别人的声音给他作证。</p>
<p><b>一、合唱曲单独处理。</b>录音室 155 首里有 <b>13 首合唱</b>（如《偏执》王晰/吴宣仪、《无荒》谭维维/王晰、《相思》王晰/弦子）。合唱读数<b>可能包含合作者或和声，不能自动归属于他</b>；因此合唱曲不进入任何能力榜，能力榜只统计独唱 <b>142 首</b>。</p>
<p><b>二、作品音域不能独立判定声部。</b>本曲库没有换声点、舒适音区与发声功能的测量；“暗音色”“低区厚度”是听感描述，不能单独确诊声部。
可以确认的是：作品中存在多首低于 E2 的记录（B1 61.5Hz 等，已复核），<b>低区演唱并非孤例</b>。
“bass-baritone（低男中音）”属于<b>有来源的外部评价或待讨论分类</b>，不是本曲库自行证明的结论。</p>
<p style="font-size:13px;color:#666">注：61.5Hz 比 82.4Hz 低约 5.06 个半音（B1→E2 为纯四度）。</p>
</section>
<!-- EXTRA_END -->"""


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
    if path.name == 'voice.html':
        s = add_context_column(s)
        if '<!-- EXTRA_START -->' not in s:
            k = s.find('<!-- ABILITY_END -->')
            if k > 0:
                s = s[:k + len('<!-- ABILITY_END -->')] + '\n' + block_voice_extra() + s[k + len('<!-- ABILITY_END -->'):]
    path.write_text(s, encoding='utf-8')
    return True


ok1 = inject(ROOT / 'voice.html', block_voice())
ok2 = inject(ROOT / 'live.html', block_live())
print('注入 voice', ok1, '｜live', ok2)
