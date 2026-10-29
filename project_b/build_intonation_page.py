#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 live-intonation.html：37 场现场音准漂移分析（含剪辑素材）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from statistics import median

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
d = json.loads((ROOT / 'data' / 'research' / 'live_intonation.json').read_text(encoding='utf-8'))
shows = d['shows']
rec = json.loads((ROOT / 'data' / 'research' / 'recorder_clips.json').read_text(encoding='utf-8'))

by_year = {}
for s in shows:
    by_year.setdefault(s['year'], []).append(s)
rows = []
for y in sorted(by_year):
    a = by_year[y]
    mus = [x['intonation_med'] for x in a]
    st = [x['stability_med'] for x in a]
    rows.append((y, len(a), sum(x['n'] for x in a), median(mus), min(mus), max(mus), median(st)))
tr = ''.join(f"<tr><td>{y}</td><td class='n'>{n}</td><td class='n'>{songs}</td>"
             f"<td class='n'>{med:.1f}</td><td class='n'>{lo:.1f}–{hi:.1f}</td>"
             f"<td class='n'>{st:.1f}</td></tr>"
             for y, n, songs, med, lo, hi, st in rows)

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="robots" content="index, follow">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>王晰 37 场现场音准漂移｜五年里他更准了吗</title>
<meta name="description" content="用 37 场现场、795 首曲目实测：王晰的音准偏差五年基本持平（19.4–21.2 音分），场间极差 1.9–4.7 音分。含素材取舍说明与剪辑用数字。">
<link rel="canonical" href="https://wx409.github.io/live-intonation.html">
<link rel="stylesheet" href="assets/brand.css">
<style>
body{{font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;max-width:900px;margin:0 auto;padding:22px 18px 60px;line-height:1.8;color:#222}}
h1{{font-size:1.6rem;border-bottom:3px solid #c41e3a;padding-bottom:10px}}
h2{{font-size:1.2rem;margin-top:2em;border-left:4px solid #c41e3a;padding-left:10px}}
table{{border-collapse:collapse;width:100%;margin:.8em 0;font-size:.93rem}}
th,td{{border:1px solid #e4e4e4;padding:6px 9px;text-align:left}}
th{{background:#faf7f7}} .n{{text-align:right;font-variant-numeric:tabular-nums}}
.src{{color:#666;font-size:12.5px}} .box{{background:#fafafa;border-left:4px solid #c41e3a;padding:10px 14px;margin:1em 0}}
img{{max-width:100%;border:1px solid #eee;border-radius:6px}}
</style></head><body>
<h1>王晰 37 场现场：音准漂移实测</h1>
<p class="src">37 场（2019–2024）｜795 首曲目｜素材为现场观众录音，非官方修音；口径与前文一致（稳定音、12 平均律偏差）。</p>

<h2>一、直接给结论</h2>
<div class="box">
<p><b>他没变准，也没变不准。</b>2019 到 2024，音准偏差中位在 <b>19.4–21.2 音分</b>之间，最大波动 <b>不足 2 音分</b>——这个幅度小于一个半音的 1/50。</p>
<p><b>单场之间比年份之间更值得看。</b>同一年里，场与场的极差只有 <b>1.9–4.7 音分</b>，说明状态稳定是常态，不是某一场的偶然。</p>
<p><b>真正的变量不在音准，在曲目和场地。</b>2024 年跨度从 2.68 升到 3.05 八度，是歌单变宽，不是嗓子变了。</p>
</div>

<h2>二、分年数据</h2>
<table><tr><th>年份</th><th>场次</th><th>曲目</th><th>音准偏差中位（音分）</th><th>场间范围</th><th>稳定性中位（音分）</th></tr>{tr}</table>
<p class="src">数据：<a href="/data/research/live_intonation.json">data/research/live_intonation.json</a>。音准偏差＝音符中心相对 12 平均律的偏移；数值小不代表更好，代表更贴近十二平均律。</p>

<img src="/dashboard/live_intonation_37.png" alt="王晰 37 场现场音准偏差分布（按年份）">

<h2>三、用了哪些素材、没用什么、为什么</h2>
<table>
<tr><th>来源</th><th>用途</th><th>取舍理由</th></tr>
<tr><td>小卡带 37 场（B 站转录）</td><td><b>全量统计</b></td><td>唯一覆盖 2019–2024、每场完整歌单的素材，能算场级中位数</td></tr>
<tr><td>录音笔 3 条（3w 设备等）</td><td><b>高质量单曲参照</b></td><td>音质明显更好（99% 带宽 7099Hz vs 同场 3211Hz、零削波），但只覆盖个别曲目，不能替代场级统计</td></tr>
<tr><td>2023-12-31 上海（两版都有）</td><td><b>用录音笔版做音质对照，用小卡带版做场级统计</b></td><td>录音笔只有单曲片段，场级仍用小卡带全歌单；两者不混算</td></tr>
<tr><td>Zoom H5 个人录音</td><td><b>未纳入</b></td><td>本机未检索到对应文件；找到后可整场替换，属"更高一级素材"</td></tr>
<tr><td>《想游泳的星》reaction 剪辑</td><td><b>未纳入</b></td><td>解说与拼接混入，无法作为测量素材（另用原片做了长句分析）</td></tr>
</table>

<h2>四、录音笔素材的读数（单曲参照）</h2>
<table><tr><th>曲目</th><th>最低音</th><th>音准偏差</th><th>稳定性</th><th>跨度</th></tr>
{''.join(f"<tr><td>{r['title'][:26]}</td><td class='n'>{r['low']}</td><td class='n'>{r['intonation']}</td><td class='n'>{r['stability']}</td><td class='n'>{r['span']}</td></tr>" for r in rec)}
</table>

<h2>五、剪辑可用素材（分镜建议）</h2>
<ol>
<li><b>开场数字</b>：37 场、795 首、五年——"这不是一场的状态，是五年的账本"。</li>
<li><b>一条曲线</b>：2019→2024 音准中位 19.4→20.4 音分，画成近乎水平线，配一句"他没变准，也没变松"。</li>
<li><b>场间稳定</b>：同一年里场与场差 1.9–4.7 音分，"比很多人一首歌里的抖动还小"。</li>
<li><b>素材对照</b>：同一场两个版本，录音笔带宽 7099Hz、小卡带 3211Hz——用频谱图做视觉锤。</li>
<li><b>长句彩蛋</b>：《想游泳的星》首唱有 <b>15.2 秒</b>不换气，中位 221Hz，双引擎差 0.3%。</li>
</ol>

<h2>六、方法与局限</h2>
<ul>
<li>素材是现场观众录音，含观众噪声、场地混响；不做跨歌手比较。</li>
<li>音准偏差受曲目调性、编曲影响，年度比较只作趋势参考，不作能力断言。</li>
<li>37 场里 2024 年只有 4 场，年度均值权重不均。</li>
<li>所有读数经 demucs 人声分离 + 自研 YIN；极低音读数已按三级读数制度剔除。</li>
</ul>
<p class="src">返回：<a href="/works.html">作品与实测</a>｜<a href="/voice.html">音域实测</a>｜<a href="/dashboard/">数据大屏</a></p>
</body></html>
"""
(ROOT / 'live-intonation.html').write_text(html, encoding='utf-8')
print('已生成 live-intonation.html', len(html), '字节')
