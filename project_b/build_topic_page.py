# -*- coding: utf-8 -*-
"""颤音指纹专题页生成器 → topic-vibrato.html

为什么挑这一题（用户 2026-09-24「我不懂，你判断」）：
  ① 证据等级最高（A 级）：颤音速率是**低频调制**，修音改的是音高慢变轨迹 → 速率基本不受修音影响；
  ② 方法稳健：同一管线、同一算法，八年八个专辑横向可比（不像"最低音"受次谐波与归属风险影响）；
  ③ 唯一性：华语流行男低音的八年声纹稳定性，同类站点没有可比数据；
  ④ 可传播：一句话能说清（"一台八年校准误差 0.27Hz 的乐器"），且**不夸大**（只陈述稳定性事实）。
  另两题的短板：音域两端依赖未经人耳确认的 A#1；自有 vs 翻唱样本 21:121 严重不对称 → 都留作后续。

用法：python -X utf8 project_b\\build_topic_page.py
"""
from __future__ import annotations

import json
import statistics as st
from datetime import date
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
OUT = SITE / "topic-vibrato.html"
OUT_MD = Path(r"E:\wx\论文素材_王晰作传\专题_颤音指纹.md")
TODAY = date.today().isoformat()


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


songs = load(D / "archive_vocal_albums.json").get("songs", [])
tour = load(D / "archive_stage_tour.json")
by_alb = {}
for s in songs:
    if s.get("vibrato_hz"):
        by_alb.setdefault(s["album"], []).append(s["vibrato_hz"])
alb_rows = sorted(((a, len(v), st.median(v)) for a, v in by_alb.items()), key=lambda x: x[2])
vib_all = st.median([s["vibrato_hz"] for s in songs if s.get("vibrato_hz")])
vib_ext = st.median([s["vibrato_cents"] for s in songs if s.get("vibrato_cents")])
alb_meds = [r[2] for r in alb_rows]
drift = max(alb_meds) - min(alb_meds)
tv = [(t["tour"], t.get("vibrato_rate_hz_median")) for t in tour.get("by_tour", []) if t.get("vibrato_rate_hz_median")]
tv_min, tv_max = min(x[1] for x in tv), max(x[1] for x in tv)

rows_html = "".join(
    f"<tr><td>{a}</td><td>{n}</td><td class='n'>{m:.2f}</td></tr>" for a, n, m in alb_rows)
tv_html = "".join(f"<tr><td>{t}</td><td class='n'>{v:.2f}</td></tr>" for t, v in tv)

ld = {
    "@context": "https://schema.org",
    "@type": "ResearchProject",
    "name": "王晰颤音指纹：八年录音室全量的颤音速率稳定性",
    "url": "https://wx409.github.io/topic-vibrato.html",
    "description": (f"对 72 首录音室曲目逐一测颤音速率（Hz），八张专辑中位 {min(alb_meds):.2f}–{max(alb_meds):.2f}Hz，"
                    f"整体中位 {vib_all:.2f}Hz、漂移仅 {drift:.2f}Hz；六轮巡演中位 {tv_min:.2f}–{tv_max:.2f}Hz。"
                    "颤音速率属低频调制，修音对其影响有限，故组内纵向可比。"),
    "dateModified": TODAY,
    "citation": "https://wx409.github.io/acoustic-report.html",
    "isBasedOn": {"@type": "Dataset", "name": "archive_vocal_albums.json",
                  "url": "https://wx409.github.io/data/archive_vocal_albums.json"},
    "keywords": ["王晰", "颤音", "颤音速率", "声纹", "音色指纹", "人声分离", "F0"],
}

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>王晰颤音指纹｜八年八张专辑，颤音速率只漂 {drift:.2f}Hz</title>
<meta name="description" content="72 首录音室曲目全量实测：颤音速率整体中位 {vib_all:.2f}Hz，八张专辑中位 {min(alb_meds):.2f}–{max(alb_meds):.2f}Hz（漂移 {drift:.2f}Hz）；六轮巡演 {tv_min:.2f}–{tv_max:.2f}Hz。含方法、原始数字、反面证据与限定。">
<link rel="canonical" href="https://wx409.github.io/topic-vibrato.html">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<script src="dashboard/echarts.min.js"></script>
<style>
body{{margin:0;background:#fbf9f6;color:#241f1c;font:16px/1.8 -apple-system,"Segoe UI",system-ui,sans-serif}}
.wrap{{max-width:900px;margin:0 auto;padding:28px 20px 60px}}
h1{{font-size:26px;line-height:1.4;margin:0 0 6px}}
.sub{{color:#7a6e63;font-size:14px;margin:0 0 18px}}
h2{{font-size:19px;margin:30px 0 10px;border-left:4px solid #c41e3a;padding-left:10px}}
.card{{background:#fff;border:1px solid #eee4d8;border-radius:10px;padding:14px 18px;margin:14px 0}}
.kpi{{display:flex;flex-wrap:wrap;gap:12px;margin:14px 0}}
.kpi>div{{flex:1 1 150px;background:#fff;border:1px solid #eee4d8;border-radius:10px;padding:12px}}
.kpi b{{display:block;font-size:22px;color:#c41e3a}}
.kpi span{{font-size:12px;color:#7a6e63}}
table{{width:100%;border-collapse:collapse;background:#fff;font-size:14px;margin:10px 0}}
th,td{{border:1px solid #eee4d8;padding:6px 8px;text-align:left}}
th{{background:#faf5ef}}
td.n{{font-variant-numeric:tabular-nums;font-weight:600}}
ul{{padding-left:22px}} li{{margin:4px 0}}
.tag{{display:inline-block;background:#fdeef1;color:#a31832;border-radius:999px;padding:1px 9px;font-size:12px;margin-right:6px}}
footer{{margin-top:34px;color:#7a6e63;font-size:13px}}
code{{background:#f4efe8;padding:1px 5px;border-radius:4px;font-size:13px}}
</style></head><body><div class="wrap">
<h1>王晰颤音指纹：八年八张专辑，颤音速率只漂 {drift:.2f}Hz</h1>
<p class="sub">录音室全量 72 曲实测 · 生成于 {TODAY} · 数据可复算</p>

<div class="kpi">
<div><b>{vib_all:.2f} Hz</b><span>录音室颤音速率整体中位</span></div>
<div><b>{drift:.2f} Hz</b><span>八张专辑之间的漂移</span></div>
<div><b>{vib_ext:.0f} 音分</b><span>颤音幅度中位</span></div>
<div><b>{tv_min:.2f}–{tv_max:.2f} Hz</b><span>六轮巡演中位区间</span></div>
</div>

<h2>一、现象</h2>
<div class="card">
<p>把 72 首录音室曲目的<b>颤音速率</b>（每秒调制次数）逐曲测出来，按专辑取中位：
八张专辑的中位全部落在 <b>{min(alb_meds):.2f}–{max(alb_meds):.2f} Hz</b>，整体中位 <b>{vib_all:.2f} Hz</b>，
专辑之间的漂移只有 <b>{drift:.2f} Hz</b>。六轮巡演各轮的中位为 <b>{tv_min:.2f}–{tv_max:.2f} Hz</b>，
比录音室系统性慢 0.2–0.3 Hz（现场更松弛或速度更慢），但<b>轮与轮之间几乎不动</b>。</p>
<p>颤音速率反映的是<b>神经—肌肉振荡频率</b>，是声带很难长期稳定的指标。八年间几乎不漂，
意味着它稳定到<b>可以作为声纹指纹</b>使用。</p>
</div>

<h2>二、方法（可复算）</h2>
<div class="card">
<p>QQ 音乐 320k → <code>demucs htdemucs</code> 人声分离 → 自研 numpy YIN 逐帧 F0
（fmin 55 / fmax 1100 / frame 2048 / hop 512 / sr 22050）→ 音符切分（≥80ms、抖动 &lt;0.6 半音）
→ 逐音符调制分析得到颤音速率（Hz）与幅度（音分）→ 按曲取中位、再按专辑取中位。</p>
<p>生成器：<code>project_b/build_topic_page.py</code>；数据：<code>data/archive_vocal_albums.json</code>、
<code>data/archive_stage_tour.json</code>。</p>
</div>

<h2>三、原始数字</h2>
<div class="card"><h3 style="font-size:15px;margin:6px 0">八张专辑的颤音速率中位（Hz）</h3>
<table><tr><th>专辑</th><th>曲数</th><th>颤音速率中位</th></tr>{rows_html}</table>
<h3 style="font-size:15px;margin:14px 0 6px">六轮巡演（现场层）</h3>
<table><tr><th>巡次</th><th>颤音速率中位</th></tr>{tv_html}</table>
</div>
<div class="card" id="chart" style="height:320px"></div>
<script>
var echarts_alb = {json.dumps([r[0] for r in alb_rows], ensure_ascii=False)};
var echarts_val = {json.dumps([round(r[2], 3) for r in alb_rows])};
var c = echarts.init(document.getElementById('chart'));
c.setOption({{
  title:{{text:'八张专辑颤音速率中位（Hz）',left:'center',textStyle:{{fontSize:14}}}},
  grid:{{left:60,right:30,top:50,bottom:70}},
  xAxis:{{type:'category',data:echarts_alb,axisLabel:{{rotate:25,fontSize:11}}}},
  yAxis:{{type:'value',min:4.8,max:5.5,name:'Hz'}},
  tooltip:{{trigger:'axis'}},
  series:[{{type:'line',data:echarts_val,symbolSize:8,lineStyle:{{width:3,color:'#c41e3a'}},
           itemStyle:{{color:'#c41e3a'}},markLine:{{data:[{{yAxis:{vib_all:.2f},name:'整体中位'}}],
           lineStyle:{{type:'dashed',color:'#7a6e63'}},label:{{formatter:'整体中位 {vib_all:.2f}Hz'}}}}}}]
}});
window.addEventListener('resize',function(){{c.resize();}});
</script>

<h2>四、反面证据与限定（必须一起传播）</h2>
<div class="card">
<ul>
<li><span class="tag">分层</span><b>颤音速率属「组内可纵比、跨组谨慎」层</b>：修音改变的是音高慢变轨迹，
而颤音速率是 ~5Hz 的快速调制，<b>基本不受修音影响</b>；但<b>幅度可能受轻微影响</b>，故幅度类比较需谨慎。</li>
<li><span class="tag">现场/录音室</span>现场比录音室系统性慢 0.2–0.3Hz。这是<b>演出状态差异</b>（速度、松弛度、场馆），
<b>不是能力下降</b>——不可据此说"现场退步"。</li>
<li><span class="tag">样本</span>72 曲按专辑分组后，各专辑曲数不等（3–12 首），个别专辑样本较小；
中位稳健但非严格随机抽样。</li>
<li><span class="tag">不构成评价</span>本页只陈述<b>稳定性事实</b>（速率稳、漂移小），
<b>不构成"唱得好/不好"的评价</b>——颤音风格快慢属审美范畴（古典歌剧常见 5–7Hz；他是偏流行低吟的审美）。</li>
</ul>
</div>

<h2>五、可直接引用的句子</h2>
<div class="card">
<ul>
<li>「<b>一台八年校准误差 {drift:.2f}Hz 的乐器。</b>」</li>
<li>「八张专辑、72 首录音室曲目，颤音速率中位始终在 {min(alb_meds):.2f}–{max(alb_meds):.2f}Hz 之间——
声带是很难长期稳定的器官，这组数字说明的是<b>稳定性本身</b>。」</li>
<li>「现场比录音室慢 0.2–0.3Hz：同一台乐器，在不同房间里换了呼吸方式。」</li>
</ul>
</div>

<footer>
口径与完整台账见 <a href="/acoustic-report.html">《王晰声学全量报告》</a>（本站声学数据单一权威源）；
数字字典 <a href="/data/calibers.md">data/calibers.md</a>。
本站为非营利性个人学习研究站点，音频素材来自公开平台，如权利人认为不妥请联系删除（侵删）。
</footer>
</div></body></html>
"""
OUT.write_text(html, encoding="utf-8")

md = [f"# 专题：颤音指纹（{TODAY}）", "",
      f"- 录音室整体中位 **{vib_all:.2f} Hz**｜八张专辑中位 **{min(alb_meds):.2f}–{max(alb_meds):.2f} Hz**（漂移 **{drift:.2f} Hz**）",
      f"- 六轮巡演中位 **{tv_min:.2f}–{tv_max:.2f} Hz**（比录音室慢 0.2–0.3Hz）｜幅度中位 **{vib_ext:.0f} 音分**", "",
      "| 专辑 | 曲数 | 颤音速率中位 |", "|---|---|---|"]
md += [f"| {a} | {n} | {m:.2f} |" for a, n, m in alb_rows]
md += ["", "| 巡次 | 中位 |", "|---|---|"] + [f"| {t} | {v:.2f} |" for t, v in tv]
OUT_MD.write_text("\n".join(md), encoding="utf-8")
print(f"✅ 生成 {OUT.name}（{len(html)/1024:.0f} KB）｜专辑 {len(alb_rows)}｜巡演 {len(tv)}")
print(f"→ {OUT_MD}")
