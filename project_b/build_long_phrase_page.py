#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 live-long-phrase.html：最长连续发声（已验证样本 + 方法说明）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
v = json.loads((ROOT / 'data' / 'research' / 'live_long_phrase_verified.json').read_text(encoding='utf-8'))['rows']
extra = json.loads((ROOT / 'temp' / 'long_phrase_extra.json').read_text(encoding='utf-8'))

rows = []
for r in extra:
    rows.append((r['show'], r['song'], r['dur'], r['median_hz'], '六轨/录音笔'))
for r in v:
    rows.append((r['show'], r['song'], r['dur'], None, '六轨复核'))
rows.sort(key=lambda x: -x[2])

tr = ''.join(
    f"<tr><td>{s}</td><td>{song}</td><td class='n'>{d:.2f}</td>"
    f"<td class='n'>{hz if hz else '—'}</td><td>{src}</td></tr>"
    for s, song, d, hz, src in rows[:12])

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="robots" content="index, follow">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>王晰最长连续发声实测｜一口气能唱多久</title>
<meta name="description" content="用六轨分离+双引擎实测王晰现场最长连续发声：已验证最长 23.4 秒；《想游泳的星》首唱 14.3 秒不换气，气口仅比中位低 12–20 dB。">
<link rel="canonical" href="https://wx409.github.io/live-long-phrase.html">
<link rel="stylesheet" href="assets/brand.css">
<style>
body{{font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;max-width:900px;margin:0 auto;padding:22px 18px 60px;line-height:1.8;color:#222}}
h1{{font-size:1.55rem;border-bottom:3px solid #c41e3a;padding-bottom:10px}}
h2{{font-size:1.15rem;margin-top:2em;border-left:4px solid #c41e3a;padding-left:10px}}
table{{border-collapse:collapse;width:100%;margin:.8em 0;font-size:.92rem}}
th,td{{border:1px solid #e4e4e4;padding:6px 9px;text-align:left}} th{{background:#faf7f7}}
.n{{text-align:right;font-variant-numeric:tabular-nums}}
.src{{color:#666;font-size:12.5px}} .box{{background:#fafafa;border-left:4px solid #c41e3a;padding:10px 14px;margin:1em 0}}
</style></head><body>
<h1>一口气能唱多久：王晰连续发声实测</h1>
<p class="src">方法：demucs 六轨分离 → 能量（中位−12dB）与周期性双条件 → 缺口 ≤0.25 秒合并。素材为现场录音，非官方修音。</p>

<h2>一、结论</h2>
<div class="box">
<p><b>已验证最长 23.4 秒</b>（2024 肆益巡演《海然海然×嘎达梅林》，录音笔直出）。</p>
<p><b>《想游泳的星》首唱那句"15 秒"实测 14.3 秒</b>，成立；网上传的"23 秒"是同段的误判（CREPE 穿过换气）。</p>
<p><b>他的换气点几乎听不出来</b>——两处气口只比演唱中位低 12–20 dB、时长 0.67–1.03 秒，被伴奏和混响填住。</p>
</div>

<h2>二、已验证样本</h2>
<table><tr><th>场次</th><th>曲目</th><th>连续发声（秒）</th><th>中位音高（Hz）</th><th>来源</th></tr>{tr}</table>
<p class="src">数据：<a href="/data/research/live_long_phrase_verified.json">live_long_phrase_verified.json</a>（六轨复核）｜<a href="/data/research/xyy_long_phrase.json">xyy_long_phrase.json</a>（想游泳的星细节）</p>

<h2>三、为什么"37 场自动排行"没有发布</h2>
<ul>
<li>两轨人声轨里混着贝斯与和声，能量几乎不断——自动会算出 100 秒以上的假长句；</li>
<li>CREPE 遇到气口仍会追踪残留共振，把两段连成一段（"23 秒"就是这么来的）；</li>
<li>目前只对排在前面的候选做了六轨复核，<b>全量排行需要逐条复核</b>，不在本轮范围。</li>
</ul>
<p><b>所以这里只发布已复核的样本，不发布未复核的榜单。</b></p>

<h2>四、剪辑可用素材</h2>
<ol>
<li><b>23.4 秒</b>：《海然海然×嘎达梅林》录音笔版，一口气的长度。</li>
<li><b>14.3 秒</b>：《想游泳的星》首唱——"15 秒"的准确版。</li>
<li><b>12–20 dB</b>：气口只压低这么多，所以听不出来；配能量包络图做视觉锤。</li>
<li><b>0.67–1.03 秒</b>：每一口气的长度，比一次普通呼吸还短。</li>
</ol>

<h2>五、局限</h2>
<ul>
<li>0.25 秒缺口阈值可能把极快换气算进连唱；已复核样本均逐条看过能量包络；</li>
<li>现场录音含观众噪声，未做跨歌手比较；</li>
<li>"连续发声"不等于"气息能力"，它只是一项可测的表现指标。</li>
</ul>
<p class="src">延伸：<a href="/live-intonation.html">37 场音准漂移</a>｜<a href="/voice.html">音域实测</a>｜<a href="/works.html">作品与实测</a></p>
</body></html>
"""
(ROOT / 'live-long-phrase.html').write_text(html, encoding='utf-8')
print('已生成 live-long-phrase.html', len(html), '字节')
