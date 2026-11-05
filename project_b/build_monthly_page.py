#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 data/monthly_events.json 渲染成 dashboard/monthly.html（月度事件脉络）。

页面：ECharts 折线（月度指数）+ 异常月标记 + 归因表（同月/前1月事件）。
数据内联（48 个月 ~40KB），不额外发请求；图表库复用同目录 echarts.min.js，CDN 失败自动回退。
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "monthly_events.json"
OUT = ROOT / "dashboard" / "monthly.html"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>月度事件脉络 · 每月变化与异常月归因｜王晰数据大屏</title>
<meta name="description" content="王晰指数月度脉络：按月看追踪曲目池日均变化，标注异常月并列出同月/前一月的巡演、晚会、发行事件作为候选解释。口径与全站一致，数字由脚本派生。">
<link rel="canonical" href="https://wx409.github.io/dashboard/monthly.html">
<meta property="og:title" content="月度事件脉络 · 每月变化与异常月归因">
<meta property="og:description" content="按月看指数变化，异常月自动标出并列出同期巡演/晚会/发行事件（候选解释，非因果）。">
<style>
:root{--bg:#0b1020;--card:#141a30;--ink:#e6ebff;--muted:#8c98b8;--gold:#E0B64F;--red:#ff7a7a;--green:#5bd6a0;--line:#26304d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.75 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:22px 16px 60px}
h1{font-size:22px;margin:0 0 6px}
h2{font-size:17px;margin:26px 0 10px;color:var(--gold)}
.lead{color:var(--muted);margin:6px 0 14px}
.back{display:inline-block;margin-bottom:12px;color:#7fb0ff;text-decoration:none;font-size:13px}
.note{background:rgba(224,182,79,.08);border:1px solid rgba(224,182,79,.35);border-radius:10px;padding:10px 14px;font-size:13px;color:#f0e2bd;margin:12px 0}
#chart{width:100%;height:380px;background:var(--card);border:1px solid var(--line);border-radius:12px}
.kpis{display:flex;gap:12px;flex-wrap:wrap;margin:14px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;min-width:150px}
.kpi b{display:block;font-size:20px;color:var(--gold)}
.kpi span{color:var(--muted);font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#1b2340;color:#c9d4f2;font-weight:600;white-space:nowrap}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr.anom td{background:rgba(255,122,122,.06)}
.tag{display:inline-block;font-size:11px;padding:0 6px;border-radius:8px;margin-right:4px;background:#23305a;color:#9fb6ef}
.tag.tour{background:#2a3f6b;color:#a8c6ff}
.tag.rel{background:#3a2f52;color:#d9b8ff}
.ev{color:#c9d4f2}
@media(max-width:640px){table{display:block;overflow-x:auto}th,td{white-space:nowrap}#chart{height:300px}}
</style>
</head>
<body>
<div class="wrap">
<a class="back" href="./">← 返回数据大屏</a>
<h1>月度事件脉络 · 每月变化与异常月归因</h1>
<p class="lead">原来按「单场演出后逐日 CAR」看效应，现阶段演出密度低、窗口内常常只有一个观测。
这里改成按月：<strong>先看变化，再解释</strong>——异常月自动标出，并列出同月与前一月的巡演 / 演出晚会 / 新歌发行作为<strong>候选解释</strong>。</p>

<div class="note"><strong>口径</strong>：指数 = 追踪曲目池<b>日均</b>（每日先对当日有数据的曲目取均值，再按月平均）；当月有效天数 &lt; __MIN_DAYS__ 天的月份标「覆盖不足」，不参与异常判定。
<strong>异常判定</strong>：__WINDOW__。<strong>归因边界</strong>：月度粒度无法拆分同月多事件，所列事件是解释线索，不是因果结论。</div>

<div class="kpis" id="kpis"></div>
<div id="chart"></div>

<h2>异常月与同期事件</h2>
<div id="anomTable"></div>

<h2>全部月份</h2>
<div id="allTable"></div>
<p class="lead" style="margin-top:10px">生成于 __GEN__ · 数据文件 <code>data/monthly_events.json</code> · 生成脚本 <code>project_b/build_monthly_page.py</code></p>
</div>
<script id="payload" type="application/json">__DATA__</script>
<script>
(function(){
  var d = JSON.parse(document.getElementById('payload').textContent);
  var months = d.months || [];
  function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
  function fmt(v,n){ return (v==null||isNaN(v)) ? '—' : Number(v).toFixed(n==null?1:n); }
  function kindTag(k){ var c = k==='巡演'?'tour':(k==='发行'?'rel':''); return '<span class="tag '+c+'">'+esc(k)+'</span>'; }

  var s = d.summary || {};
  document.getElementById('kpis').innerHTML =
    '<div class="kpi"><b>'+s.n_months+'</b><span>个月份</span></div>' +
    '<div class="kpi"><b>'+s.n_anomaly+'</b><span>异常月（z≥2.5 或 环比≥20%）</span></div>' +
    '<div class="kpi"><b>'+s.n_events+'</b><span>登记事件（巡演/演出晚会/发行）</span></div>' +
    '<div class="kpi"><b>'+s.n_low_coverage+'</b><span>覆盖不足月份</span></div>';

  var xs = months.map(function(m){return m.month;});
  var ys = months.map(function(m){return m.index;});
  var pts = months.filter(function(m){return m.anomaly;}).map(function(m){
    return {name:m.month, value:[m.month, m.index], coord:[m.month, m.index],
            itemStyle:{color:'#ff7a7a'}};
  });

  function render(){
    var el = document.getElementById('chart');
    var chart = echarts.init(el);
    chart.setOption({
      backgroundColor:'transparent',
      grid:{left:56,right:24,top:30,bottom:46},
      tooltip:{trigger:'axis', formatter:function(ps){
        var i = ps[0].dataIndex, m = months[i];
        var evs = (m.events||[]).slice(0,4).map(function(e){return '· '+esc(e.title).slice(0,40);}).join('<br>');
        return '<b>'+m.month+'</b><br>指数 '+fmt(m.index)+'（'+m.n_days+' 天）<br>'+
               '环比 '+(m.mom_pct==null?'—':(m.mom_pct>0?'+':'')+m.mom_pct+'%')+
               ' · 趋势偏离 '+(m.dev_pct==null?'—':m.dev_pct+'%')+
               (m.events&&m.events.length?('<br>'+evs):'');
      }},
      xAxis:{type:'category', data:xs, axisLabel:{color:'#8c98b8', rotate:45, fontSize:10}, axisLine:{lineStyle:{color:'#33406b'}}},
      yAxis:{type:'value', name:'指数', nameTextStyle:{color:'#8c98b8'}, axisLabel:{color:'#8c98b8'}, splitLine:{lineStyle:{color:'#1e2740'}}},
      series:[{
        type:'line', data:ys, smooth:true, symbolSize:5,
        lineStyle:{color:'#7fb0ff', width:2}, itemStyle:{color:'#7fb0ff'},
        areaStyle:{color:'rgba(127,176,255,.12)'},
        markPoint:{symbol:'circle', symbolSize:9, label:{show:false}, data:pts}
      }]
    });
    window.addEventListener('resize', function(){ chart.resize(); });
  }
  function loadEcharts(){
    if (typeof echarts !== 'undefined') { render(); return; }
    var srcs = ['./echarts.min.js','../dashboard/echarts.min.js',
                'https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js'];
    var i = 0;
    (function next(){
      if (i >= srcs.length) { document.getElementById('chart').innerHTML =
        '<div style="padding:20px;color:#8c98b8">图表库未加载；下方表格包含全部数据。</div>'; return; }
      var s = document.createElement('script'); s.src = srcs[i++];
      s.onload = function(){ if (typeof echarts !== 'undefined') render(); else next(); };
      s.onerror = next;
      document.head.appendChild(s);
    })();
  }

  function rowHtml(m, withEvents){
    var cls = m.anomaly ? ' class="anom"' : '';
    var h = '<tr'+cls+'><td>'+esc(m.month)+'</td>'+
      '<td class="num">'+fmt(m.index)+'</td>'+
      '<td class="num">'+m.n_days+'</td>'+
      '<td class="num">'+(m.mom_pct==null?'—':(m.mom_pct>0?'+':'')+m.mom_pct+'%')+'</td>'+
      '<td class="num">'+(m.dev_pct==null?'—':m.dev_pct+'%')+'</td>'+
      '<td class="num">'+(m.z==null?'—':m.z)+'</td>'+
      '<td class="num">'+m.n_events+'</td>';
    if (withEvents){
      var evs = (m.events||[]).map(function(e){return kindTag(e.kind)+esc(e.title);}).join('<br>') || '—';
      h += '<td class="ev">'+evs+'</td>';
    }
    return h+'</tr>';
  }

  var anom = months.filter(function(m){return m.anomaly;});
  var at = '<table><tr><th>月份</th><th>指数</th><th>天数</th><th>环比</th><th>趋势偏离</th><th>z</th><th>事件</th><th>同月事件（候选解释）</th></tr>';
  anom.forEach(function(m){
    at += rowHtml(m, false).replace('</tr>', '<td class="ev">'+
      ((m.events||[]).map(function(e){return kindTag(e.kind)+esc(e.title);}).join('<br>') || '—')+
      (m.attribution && m.attribution.prev_month && m.attribution.prev_month.length
        ? '<div style="margin-top:4px;color:#8c98b8;font-size:12px">前 1 月：'+
          m.attribution.prev_month.slice(0,3).map(function(e){return esc(e.title).slice(0,28);}).join('；')+'</div>' : '')+
      '</td></tr>');
  });
  document.getElementById('anomTable').innerHTML = at + '</table>' +
    '<p class="lead" style="margin-top:8px">同月事件 = 该月登记的巡演 / 演出晚会 / 发行；前 1 月事件用于捕捉「宣发提前」。多个事件同月时无法拆分贡献。</p>';

  var all = '<table><tr><th>月份</th><th>指数</th><th>天数</th><th>环比</th><th>趋势偏离</th><th>z</th><th>事件数</th></tr>';
  months.forEach(function(m){ all += rowHtml(m, false); });
  document.getElementById('allTable').innerHTML = all + '</table>';

  loadEcharts();
})();
</script>
</body>
</html>
"""


def main() -> int:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    html = (TEMPLATE
            .replace("__DATA__", json.dumps(d, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__GEN__", d.get("generated_at", ""))
            .replace("__MIN_DAYS__", str(d.get("min_days", 15)))
            .replace("__WINDOW__", d.get("window", "")))
    OUT.write_text(html, encoding="utf-8", newline="")
    kb = len(html.encode()) / 1024
    print("已生成 %s（%.0f KB｜%d 个月｜异常 %d）" % (
        OUT.relative_to(ROOT).as_posix(), kb,
        len(d.get("months") or []), (d.get("summary") or {}).get("n_anomaly", 0)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
