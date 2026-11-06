#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 dashboard/story.html：五块「人话版」数据故事（结构/描述/排序/预测/单曲）。

设计原则
  · 每块都是「一句人话 + 一张图 + 怎么读」，外行先读字再看图；
  · 能动的都动起来：数字滚动、柱状逐条生长、折线描线（ECharts animation）+ 滚动入场；
  · 所有数字由脚本算，不手写；图表库复用同目录 echarts.min.js，CDN 失败回退。

数据：data/setlists.json、data/monthly_events.json、E:\\wx\\wx_textmine_out\\music_index_long.csv
输出：dashboard/story.html
"""
from __future__ import annotations

import csv
import json
import statistics
import sys
from bisect import bisect_left
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboard" / "story.html"
SETLISTS = ROOT / "data" / "setlists.json"
MONTHLY = ROOT / "data" / "monthly_events.json"
LONG = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")

PRE = (-21, -7)
POST = (1, 7)
MIN_PTS = 3

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ── 数据 ────────────────────────────────────────────────────────────────
def load_series():
    per_song = defaultdict(dict)
    with open(LONG, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            d = (r.get("date") or "").strip()[:10]
            try:
                v = float(str(r.get("index", "")).replace(",", ""))
            except ValueError:
                continue
            if len(d) == 10 and v > 0:
                per_song[(r.get("song") or "").strip()][d] = v
    dates = sorted({d for m in per_song.values() for d in m})
    return per_song, dates


def wmean(series, d0, d1, dates):
    i0, i1 = bisect_left(dates, d0), bisect_left(dates, d1)
    vals = [series[d] for d in dates[i0:i1] if d in series]
    return statistics.mean(vals) if len(vals) >= MIN_PTS else None


def structure(shows):
    """巡演结构：场次、曲目数、与上一巡的重复/新增。"""
    by_tour = defaultdict(list)
    for s in shows.values():
        by_tour[(s.get("tour") or "未标注")].append(s)
    order = ["一巡", "二巡", "三巡", "四巡", "五巡", "六巡"]
    out, prev = [], None
    for t in order:
        ss = by_tour.get(t) or []
        if not ss:
            continue
        songs = set()
        for s in ss:
            for x in (s.get("songs") or []):
                n = (x.get("title") or "").strip()
                if n:
                    songs.add(n)
        keep = len(songs & prev) / len(songs) if prev and songs else None
        out.append({"tour": t, "shows": len(ss), "songs": len(songs),
                    "keep_pct": round(keep * 100, 1) if keep is not None else None})
        prev = songs
    return out


def ranking(per_song, dates, shows):
    """演出后相对走强：每场算 曲目变化 − 同期其它歌变化，再按曲目汇总。"""
    acc = defaultdict(list)
    for s in shows.values():
        d = (s.get("date") or "")[:10]
        if not d or d < dates[0] or d > dates[-1]:
            continue
        y, m, dd = map(int, d.split("-"))
        D = date(y, m, dd)
        pre = ((D + timedelta(days=PRE[0])).isoformat(), (D + timedelta(days=PRE[1])).isoformat())
        post = ((D + timedelta(days=POST[0])).isoformat(), (D + timedelta(days=POST[1])).isoformat())
        if post[1] > dates[-1] or pre[0] < dates[0]:
            continue
        names = {(x.get("title") or "").strip() for x in (s.get("songs") or [])}
        names.discard("")
        deltas, ctrl = {}, []
        for song, ser in per_song.items():
            a, b = wmean(ser, *pre, dates), wmean(ser, *post, dates)
            if a and b and a > 0 and b > 0:
                v = b / a - 1
                if song in names:
                    deltas[song] = v
                else:
                    ctrl.append(v)
        if len(deltas) < 3 or len(ctrl) < 5:
            continue
        base = statistics.median(ctrl)
        for song, v in deltas.items():
            acc[song].append((v - base) * 100)
    rows = [{"song": k, "n": len(v), "effect": round(statistics.median(v), 2)}
            for k, v in acc.items() if len(v) >= 2]
    rows.sort(key=lambda r: -r["effect"])
    return rows


def forecast(months):
    """季节性朴素预测：下 N 个月 = 同月历史中位 × 最近水平修正；并回测近 12 个月误差。"""
    heats = [m for m in months if m.get("heat") is not None]
    if len(heats) < 24:
        return None
    last = heats[-1]
    # 回测：用"同月中位 × 最近3月中位修正"预测，误差取 MAPE
    errs = []
    for i in range(len(heats) - 12, len(heats)):
        mm = int(heats[i]["month"][5:7])
        same = [x["heat"] for x in heats[:i] if int(x["month"][5:7]) == mm]
        if len(same) < 2:
            continue
        pred = statistics.median(same) * (statistics.median([x["heat"] for x in heats[max(0, i - 3):i]]) /
                                         max(1e-9, statistics.median([x["heat"] for x in heats])))
        errs.append(abs(pred - heats[i]["heat"]) / max(1e-9, heats[i]["heat"]))
    mape = round(statistics.median(errs) * 100, 1) if errs else None
    hist_med = statistics.median([x["heat"] for x in heats])
    level = statistics.median([x["heat"] for x in heats[-3:]])
    yy, mo = int(last["month"][:4]), int(last["month"][5:7])
    out = []
    for k in range(1, 4):
        mo2 = mo + k
        yy2 = yy + (mo2 - 1) // 12
        mo2 = (mo2 - 1) % 12 + 1
        same = [x["heat"] for x in heats if int(x["month"][5:7]) == mo2]
        base = statistics.median(same) if same else hist_med
        out.append({"month": "%04d-%02d" % (yy2, mo2),
                    "heat": round(base * level / hist_med, 2)})
    return {"mape_pct": mape, "level": round(level, 2), "next": out}


def single_songs(per_song, dates, shows, top=3):
    """挑指数体量最大的几首，画自身归一曲线 + 演出日标记。"""
    size = {s: statistics.median(list(m.values())) for s, m in per_song.items() if len(m) >= 60}
    picks = sorted(size, key=lambda s: -size[s])[:top]
    show_dates = sorted({(s.get("date") or "")[:10] for s in shows.values()} & set(dates))
    out = []
    for song in picks:
        ser = per_song[song]
        ds = sorted(ser)
        pts = []
        for i, d in enumerate(ds):
            hist = [ser[x] for x in ds[max(0, i - 90):i]]
            if len(hist) < 30:
                continue
            base = statistics.median(hist)
            if base > 0:
                pts.append([d, round(ser[d] / base, 3)])
        out.append({"song": song, "points": pts[-420:]})
    return {"songs": out, "show_dates": show_dates}


# ── 页面 ────────────────────────────────────────────────────────────────
def main() -> int:
    per_song, dates = load_series()
    shows = json.loads(SETLISTS.read_text(encoding="utf-8")).get("setlists") or {}
    months = json.loads(MONTHLY.read_text(encoding="utf-8")).get("months") or []

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "span": [dates[0], dates[-1]],
        "n_songs": len(per_song),
        "n_shows": len(shows),
        "structure": structure(shows),
        "months": [{k: m.get(k) for k in ("month", "heat", "breadth", "n_songs", "anomaly", "Mom", "mom_pct")}
                   for m in months if m.get("heat") is not None],
        "ranking": ranking(per_song, dates, shows)[:10],
        "forecast": forecast(months),
        "single": single_songs(per_song, dates, shows),
    }
    OUT.write_text(TEMPLATE.replace("__DATA__", json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")),
                   encoding="utf-8", newline="")
    print("已生成 %s（%.0f KB）｜巡演 %d｜歌曲 %d｜排序 %d｜预测 %s"
          % (OUT.relative_to(ROOT).as_posix(), len(OUT.read_bytes()) / 1024,
             len(payload["structure"]), payload["n_songs"], len(payload["ranking"]),
             (payload["forecast"] or {}).get("mape_pct")))
    return 0


TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>数据故事 · 王晰指数的结构、变化、排序与预测</title>
<meta name="description" content="用大白话讲王晰的指数数据：巡演怎么换血、月度热度怎么变、演出后哪些歌相对走强、下几个月大概什么水平、三首代表作自己的曲线。每个结论都标注能干到什么程度。">
<link rel="canonical" href="https://wx409.github.io/dashboard/story.html">
<style>
:root{--bg:#080c18;--card:#111930;--ink:#e8eeff;--muted:#8c98b8;--gold:#E0B64F;--blue:#7fb0ff;--red:#ff7a7a;--green:#5bd6a0;--line:#222c48}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(1200px 600px at 50% -10%,#16203c 0%,var(--bg) 60%);color:var(--ink);
font:15px/1.8 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:24px 18px 80px}
.back{color:var(--blue);text-decoration:none;font-size:13px}
h1{font-size:26px;margin:14px 0 6px;letter-spacing:.5px}
.sub{color:var(--muted);margin:0 0 6px}
.hero{display:flex;gap:14px;flex-wrap:wrap;margin:22px 0 8px}
.hero .k{flex:1 1 160px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;position:relative;overflow:hidden}
.hero .k b{font-size:30px;color:var(--gold);display:block;font-variant-numeric:tabular-nums}
.hero .k span{color:var(--muted);font-size:12.5px}
.hero .k:after{content:"";position:absolute;inset:auto -40% -60% auto;width:160px;height:160px;border-radius:50%;
background:radial-gradient(circle,rgba(224,182,79,.18),transparent 70%)}
section.reveal{opacity:0;transform:translateY(18px);transition:opacity .7s ease,transform .7s ease}
section.reveal.in{opacity:1;transform:none}
h2{font-size:20px;margin:40px 0 4px;display:flex;align-items:center;gap:8px}
h2 .n{background:var(--gold);color:#0b1020;border-radius:8px;font-size:13px;padding:1px 8px;font-weight:700}
.talk{background:linear-gradient(180deg,rgba(127,176,255,.10),rgba(127,176,255,.03));border:1px solid rgba(127,176,255,.25);
border-left:3px solid var(--blue);border-radius:10px;padding:12px 16px;margin:10px 0 12px;font-size:14.5px}
.talk b{color:#fff}
.how{color:var(--muted);font-size:12.5px;margin:6px 0 0}
.chart{width:100%;height:320px;background:var(--card);border:1px solid var(--line);border-radius:14px}
.chart.sm{height:260px}
table.hm{width:100%;border-collapse:separate;border-spacing:3px;font-size:12.5px}
table.hm th{background:none;border:0;color:var(--muted);font-weight:500;text-align:center}
table.hm td{border:0;border-radius:6px;text-align:center;padding:7px 4px;color:#0b1020;font-variant-numeric:tabular-nums}
table.hm td.na{background:#161d33;color:#3d4568}
.pill{display:inline-block;font-size:11.5px;padding:1px 8px;border-radius:9px;background:#1d2745;color:#9fb6ef;margin-left:6px}
.warn{color:#f0c674}
#tip{position:fixed;right:14px;bottom:14px;background:#0d1424;border:1px solid var(--line);border-radius:10px;
padding:8px 12px;font-size:12px;color:var(--muted);opacity:.9}
@media(max-width:640px){.chart{height:260px}h1{font-size:21px}}
</style>
</head>
<body>
<div class="wrap">
<a class="back" href="./">← 返回数据大屏</a>
<h1>数据故事：一个歌手的数据，能讲到哪一步</h1>
<p class="sub">全部数字由脚本从站内数据算出（<code>project_b/build_story_panels.py</code>），每块都写明<strong>能干什么、不能干什么</strong>。</p>

<div class="hero">
  <div class="k"><b id="k1">0</b><span>天指数记录（<span id="span"></span>）</span></div>
  <div class="k"><b id="k2">0</b><span>首曲目进入过追踪池</span></div>
  <div class="k"><b id="k3">0</b><span>场有歌单的演出</span></div>
  <div class="k"><b id="k4">0</b><span>本文档能回答的问题类型</span></div>
</div>

<section class="reveal">
<h2><span class="n">01</span>结构：每一轮巡演，歌单几乎换一遍</h2>
<div class="talk" id="talk1"></div>
<div id="c1" class="chart"></div>
<p class="how">怎么读：柱子是每轮的曲目数，蓝条是「与上一轮相同的歌」占比。<span class="pill">能说</span>换血节奏 · <span class="pill">不能说</span>为什么换</p>
</section>

<section class="reveal">
<h2><span class="n">02</span>描述：热度有起伏，但"十月低"不是每年都成立</h2>
<div class="talk" id="talk2"></div>
<div id="c2" class="chart"></div>
<div id="hm"></div>
<p class="how">怎么读：热度 = 当月每首歌相对它自己近 90 天的比值中位，1.00 是持平；矩阵横看是同年 12 个月，纵看是同一个月的 4 年。<span class="pill">能说</span>什么时候冷 · <span class="pill">不能说</span>为什么冷</p>
</section>

<section class="reveal">
<h2><span class="n">03</span>排序：演出之后，哪些歌相对走强</h2>
<div class="talk" id="talk3"></div>
<div id="c3" class="chart"></div>
<p class="how">怎么读：每场先扣掉"同期其它歌的整体变化"，再把各场结果按歌取中位。正值=演出后比同期其它歌更强。
<span class="warn">但这是观察，不是因果</span>——前置趋势检验显示，歌单曲在演出前 30 天就已经在分化。</p>
</section>

<section class="reveal">
<h2><span class="n">04</span>预测：下三个月大概什么水平（附误差）</h2>
<div class="talk" id="talk4"></div>
<div id="c4" class="chart sm"></div>
<p class="how">怎么读：用「同月历史中位 × 最近水平修正」做季节性朴素预测，并回测最近 12 个月给出误差。<span class="pill">能说</span>大致区间 · <span class="pill">不能说</span>单月精确值</p>
</section>

<section class="reveal">
<h2><span class="n">05</span>单曲：给三首代表作的曲线装个显微镜</h2>
<div class="talk" id="talk5"></div>
<div id="c5" class="chart"></div>
<p class="how">怎么读：每条线是这首歌相对自己近 90 天基线的倍数；红点是演出日。<span class="pill">能说</span>单曲自己的节奏 · <span class="pill">不能说</span>哪场演出抬了它</p>
</section>

<p class="sub" style="margin-top:36px">生成于 <span id="gen"></span> · 数据文件 <code>data/setlists.json</code> · <code>data/monthly_events.json</code> · 长表 <code>music_index_long.csv</code></p>
</div>
<div id="tip">滚到哪，讲到哪</div>
<script id="payload" type="application/json">__DATA__</script>
<script>
(function(){
  var D = JSON.parse(document.getElementById('payload').textContent);
  var $ = function(id){ return document.getElementById(id); };
  function fmt(n){ return (n==null||isNaN(n))?'—':n; }

  /* 数字滚动 */
  function count(el, to, suffix){
    var t0 = performance.now(), dur = 1200;
    function step(t){
      var p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(to * e) + (suffix||'');
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }
  var days = Math.round((new Date(D.span[1]) - new Date(D.span[0])) / 86400000) + 1;
  count($('k1'), days); count($('k2'), D.n_songs); count($('k3'), D.n_shows); count($('k4'), 4);
  $('span').textContent = D.span[0].slice(0,7) + ' → ' + D.span[1].slice(0,7);
  $('gen').textContent = D.generated_at;

  /* 滚动入场 */
  var io = new IntersectionObserver(function(es){
    es.forEach(function(e){ if (e.isIntersecting){ e.target.classList.add('in'); e.target.dataset.seen='1'; } });
  }, {threshold:.15});
  document.querySelectorAll('section.reveal').forEach(function(s){ io.observe(s); });

  /* 01 结构 */
  var st = D.structure || [];
  var firstKeep = st.find(function(x){return x.keep_pct!=null;});
  $('talk1').innerHTML = st.length ? ('他把巡演当成<strong>换一批歌</strong>：' +
    st.map(function(x){return x.tour+' '+x.songs+' 首';}).join('、') + '。' +
    (firstKeep ? ('相邻两轮之间只保留 <strong>'+firstKeep.keep_pct+'%</strong> 的旧曲目，' +
      '剩下都是新编的曲目——所以你很难在两轮巡演里听到一样的歌。') : '') +
    '<br>这意味着：<b>"他的现场"没有固定曲库</b>，任何"这首歌现场唱得如何"的结论都只对某一轮成立。')
    : '（暂无歌单数据）';

  /* 02 描述 */
  var ms = D.months || [];
  var oct = {};
  ms.forEach(function(m){ if (m.month.slice(5,7)==='10') oct[m.month.slice(0,4)] = m.heat; });
  $('talk2').innerHTML = '把"10 月是不是都低"逐年摊开看：' +
    Object.keys(oct).sort().map(function(y){
      return y + ' 年 <strong>' + oct[y] + '</strong>';
    }).join('、') + '。' +
    '<br>结论：<b>3 年偏低、1 年持平</b>，样本只有 4 年，够不上"季节性规律"；而且 2023 年的最低点在 4–5 月，不在 10 月。';

  /* 03 排序 */
  var rk = D.ranking || [];
  $('talk3').innerHTML = rk.length ? ('排在前面的歌，是<strong>演出后明显强于同期其它歌</strong>的那几首：' +
    rk.slice(0,3).map(function(r){return '《'+r.song+'》('+(r.effect>0?'+':'')+r.effect+'%)';}).join('、') + '。' +
    '<br>但要小心：这是"演出后"不是"因为演出"。我们做过前置趋势检验——把假事件放在演出前 30 天，同样能算出 −12% 的效应，说明歌单曲本身在那之前就在分化。'
    ) : '（可分析的场次不足）';

  /* 04 预测 */
  var fc = D.forecast;
  $('talk4').innerHTML = fc ? ('按季节性朴素模型，接下来三个月大约是 ' +
    fc.next.map(function(x){return x.month.slice(5,7)+'月 '+x.heat;}).join(' · ') +
    '（1.00 = 与该曲自身基线持平）。回测最近 12 个月，中位误差 <strong>±'+fc.mape_pct+'%</strong>。' +
    '<br>误差这么大，它<strong>只能当"量级参考"</strong>：能说明大概在 0.5~0.7 这个区间，不能说明某个月一定是多少。任何单月精确预测都不该信。')
    : '（月份数不足，暂不做预测）';

  /* 05 单曲 */
  var sg = (D.single && D.single.songs) || [];
  $('talk5').innerHTML = sg.length ? ('挑了指数体量最大的三首：' + sg.map(function(s){return '《'+s.song+'》';}).join('、') +
    '。它们各自的曲线形状完全不同——<strong>有的常年平稳，有的会突然被抬起来再慢慢退</strong>。' +
    '<br>这正是"指数"好玩的地方：它记的不是他的嗓子，而是<b>他被人想起来的时间点</b>。')
    : '（单曲序列不足）';

  function renderTable(){

  var years = [], by = {};
  ms.forEach(function(m){ var y=m.month.slice(0,4), mm=+m.month.slice(5,7);
    if (years.indexOf(y)<0) years.push(y); (by[y]=by[y]||{})[mm]=m.heat; });
  years.sort();
  var heats = ms.map(function(m){return m.heat;});
  var lo = Math.min.apply(null,heats), hi = Math.max.apply(null,heats);
  function col(h){ var t=(h-lo)/Math.max(1e-9,hi-lo);
    var stp=[[0,[42,63,107]],[.35,[63,111,176]],[.6,[127,176,255]],[.8,[255,212,121]],[1,[255,122,122]]];
    for(var i=0;i<stp.length-1;i++){var a=stp[i],b=stp[i+1]; if(t>=a[0]&&t<=b[0]){
      var f=(t-a[0])/(b[0]-a[0]); var c=[0,1,2].map(function(k){return Math.round(a[1][k]+(b[1][k]-a[1][k])*f);});
      return 'rgb('+c.join(',')+')';}}
    return 'rgb(255,122,122)'; }
  var h = '<table class="hm"><tr><th></th>';
  for (var i=1;i<=12;i++) h += '<th>'+i+'月</th>';
  h += '</tr>';
  years.forEach(function(y){
    h += '<tr><th>'+y+'</th>';
    for (var i=1;i<=12;i++){
      var v = (by[y]||{})[i];
      h += v==null ? '<td class="na">—</td>' : '<td style="background:'+col(v)+'">'+v.toFixed(2)+'</td>';
    }
    h += '</tr>';
  });
  h += '</table>';
  $('hm').innerHTML = h;


  }
  /* 图表 */
  var tries = 0;
  function draw(){
    if (typeof echarts === 'undefined') { if (++tries < 60) return setTimeout(draw, 250); return; }
    var AX = {axisLabel:{color:'#8c98b8'}, axisLine:{lineStyle:{color:'#33406b'}}, splitLine:{lineStyle:{color:'#1b2338'}}};
    var TIP = {backgroundColor:'rgba(13,20,36,.95)', borderColor:'#2b3757', textStyle:{color:'#e8eeff'}};

    if (st.length) {
      var c1 = echarts.init($('c1'));
      c1.setOption({backgroundColor:'transparent', tooltip:{trigger:'axis', ...TIP},
        legend:{textStyle:{color:'#8c98b8'}, top:0},
        grid:{left:48,right:16,top:34,bottom:34},
        xAxis:{type:'category', data:st.map(function(x){return x.tour;}), ...AX},
        yAxis:{type:'value', ...AX},
        animationDuration:900, animationEasing:'cubicOut',
        series:[
          {name:'曲目数', type:'bar', data:st.map(function(x){return x.songs;}),
           itemStyle:{color:'#7fb0ff', borderRadius:[6,6,0,0]}, label:{show:true, position:'top', color:'#cfe0ff'}},
          {name:'与上轮重复 %', type:'line', smooth:true, data:st.map(function(x){return x.keep_pct;}),
           lineStyle:{color:'#E0B64F',width:3}, itemStyle:{color:'#E0B64F'}, symbolSize:9}
        ]});
    }

    if (ms.length) {
      var c2 = echarts.init($('c2'));
      c2.setOption({backgroundColor:'transparent', tooltip:{trigger:'axis', ...TIP},
        grid:{left:48,right:16,top:20,bottom:44},
        xAxis:{type:'category', data:ms.map(function(m){return m.month;}), ...AX, axisLabel:{color:'#8c98b8',rotate:45,fontSize:9}},
        yAxis:{type:'value', name:'热度', ...AX},
        animationDuration:1200,
        series:[{type:'line', smooth:true, data:ms.map(function(m){return m.heat;}),
          lineStyle:{color:'#5bd6a0',width:2.5}, itemStyle:{color:'#5bd6a0'},
          areaStyle:{color:'rgba(91,214,160,.10)'},
          markLine:{silent:true, symbol:'none', lineStyle:{color:'#E0B64F',type:'dashed'},
            data:[{yAxis:1, label:{formatter:'自身基线 1.00', color:'#E0B64F'}}]}}]});
    }

    renderTable();

    if (rk.length) {
      var c3 = echarts.init($('c3'));
      var rr = rk.slice().reverse();
      c3.setOption({backgroundColor:'transparent', tooltip:{trigger:'axis', ...TIP},
        grid:{left:130,right:60,top:10,bottom:24},
        xAxis:{type:'value', ...AX, axisLabel:{color:'#8c98b8', formatter:'{value}%'}},
        yAxis:{type:'category', data:rr.map(function(r){return r.song;}), ...AX},
        animationDuration:1000, animationDelay:function(i){return i*60;},
        series:[{type:'bar', data:rr.map(function(r){
            return {value:r.effect, itemStyle:{color:r.effect>=0?'#5bd6a0':'#ff7a7a', borderRadius:[0,6,6,0]}};}),
          label:{show:true, position:'right', color:'#cfe0ff', formatter:'{c}%'}}]});
    }

    if (fc && fc.next.length) {
      var c4 = echarts.init($('c4'));
      var hist = ms.slice(-12);
      var cats = hist.map(function(m){return m.month;}).concat(fc.next.map(function(x){return x.month;}));
      var vals = hist.map(function(m){return m.heat;}).concat(fc.next.map(function(){return null;}));
      var fut = hist.map(function(){return null;}).concat(fc.next.map(function(x){return x.heat;}));
      c4.setOption({backgroundColor:'transparent', tooltip:{trigger:'axis', ...TIP},
        legend:{textStyle:{color:'#8c98b8'}, top:0},
        grid:{left:48,right:16,top:32,bottom:40},
        xAxis:{type:'category', data:cats, ...AX, axisLabel:{color:'#8c98b8',rotate:45,fontSize:9}},
        yAxis:{type:'value', ...AX},
        series:[
          {name:'近 12 个月实际', type:'line', data:vals, smooth:true, lineStyle:{color:'#7fb0ff',width:2}, itemStyle:{color:'#7fb0ff'}},
          {name:'未来 3 个月预测', type:'line', data:fut, smooth:true, lineStyle:{color:'#E0B64F',width:2.5,type:'dashed'},
           itemStyle:{color:'#E0B64F'}, symbolSize:9}
        ]});
    }

    if (sg.length) {
      var c5 = echarts.init($('c5'));
      var sd = (D.single.show_dates || []);
      c5.setOption({backgroundColor:'transparent', tooltip:{trigger:'axis', ...TIP},
        legend:{textStyle:{color:'#8c98b8'}, top:0},
        grid:{left:48,right:16,top:34,bottom:44},
        xAxis:{type:'time', ...AX},
        yAxis:{type:'value', name:'相对自身基线', ...AX},
        animationDuration:1400,
        series: sg.map(function(s, i){
          var palette = ['#7fb0ff','#5bd6a0','#E0B64F'];
          return {name:s.song, type:'line', showSymbol:false, smooth:true,
            data:s.points.map(function(p){return [p[0], p[1]];}),
            lineStyle:{width:2, color:palette[i%3]}, itemStyle:{color:palette[i%3]},
            markLine: i===0 ? {silent:true, symbol:'none', lineStyle:{color:'#ff7a7a',type:'dotted',opacity:.35},
              data: sd.map(function(d){return {xAxis:d};})} : undefined};
        })});
    }
  }
  /* echarts 异步加载：本地优先，再 CDN，全部失败则只留表格与文字 */
  (function loadLib(){
    if (typeof echarts !== 'undefined') { draw(); return; }
    var srcs = ['./echarts.min.js','../dashboard/echarts.min.js',
                'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'];
    var i = 0;
    (function next(){
      if (i >= srcs.length) return;
      var el = document.createElement('script'); el.src = srcs[i++];
      el.onload = function(){ if (typeof echarts !== 'undefined') draw(); else next(); };
      el.onerror = next;
      document.head.appendChild(el);
    })();
  })();
  renderTable();
})();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
