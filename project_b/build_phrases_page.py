"""生成 phrases.html —— 词句全库（检索 + 骰子 + SVG 卡片导出）"""
import json
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
dice = json.loads((ROOT / "data" / "dice_sets.json").read_text(encoding="utf-8"))
bank = json.loads((ROOT / "data" / "phrase_bank.json").read_text(encoding="utf-8"))

items = bank.get("items") or []
sets = dice.get("sets") or {}
by_type = bank.get("by_type") or {}
qstats = bank.get("quality_stats") or {}

TYPE_CN = {"interview": "采访/播客", "lyrics": "歌词", "mystic": "卦象", "song": "歌名说明", "talk": "现场说话"}
ORDER = ["interview", "lyrics", "talk", "mystic", "song"]

tabs_list = [{"key": k, "name": v["name"], "note": v.get("disclaimer", ""),
              "faces": [{"text": f["text"], "source": f.get("source", "")} for f in v.get("faces", [])]}
             for k, v in sets.items() if v.get("faces")]
tabs_json = json.dumps(tabs_list, ensure_ascii=False)

sections = []
for t in ORDER:
    rows = [it for it in items if it["type"] == t]
    if not rows:
        continue
    rows.sort(key=lambda x: (0 if x.get("quality") == "high" else 1, -len(x["text"])))
    lis = []
    for it in rows[:200]:
        q = it.get("quality", "")
        badge = {"high": "★★", "mid": "★"}.get(q, "")
        lis.append("<li data-q='%s'>%s<span class='src'>%s %s</span></li>"
                   % (q, html.escape(it["text"]),
                      ("<b>%s</b>" % badge) if badge else "", html.escape(it.get("source", ""))))
    sections.append("<section class='grp'><h2>%s<span class='n'>%d 条</span></h2><ol>%s</ol></section>"
                    % (TYPE_CN.get(t, t), len(rows), "".join(lis)))

total = bank.get("count", len(items))
high = qstats.get("high", 0)

ld = {"@context": "https://schema.org", "@type": "Dataset", "name": "王晰词句库",
      "description": "王晰说过的话、歌词片段、采访引语与卦象引语，共 %d 条，含出处。" % total,
      "url": "https://wx409.github.io/phrases.html",
      "creator": {"@type": "Person", "name": "王晰"},
      "isPartOf": {"@type": "WebSite", "url": "https://wx409.github.io/"}}

page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>词句库｜王晰（{total} 条，带出处）</title>
<link rel="canonical" href="https://wx409.github.io/phrases.html">
<style>
body{{font:15px/1.75 -apple-system,Segoe UI,Microsoft YaHei,sans-serif;max-width:860px;margin:24px auto;padding:0 16px;color:#222}}
h1{{margin:0 0 6px}}h2{{font-size:17px;margin:26px 0 8px;border-left:4px solid #a8323d;padding-left:8px}}
.meta{{color:#666;font-size:.92em;margin:0 0 16px}}
.tip{{margin:0 0 16px;padding:10px 14px;background:#fbf4f6;border-radius:10px;font-size:14px}}
.bar{{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}}
.bar input{{flex:1;min-width:180px;font:inherit;padding:9px 12px;border:1px solid #d8cfc0;border-radius:10px}}
#tabs{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}}
#tabs button{{font:inherit;padding:7px 14px;border:1px solid #d8cfc0;background:#fbf8f3;border-radius:999px;cursor:pointer}}
#tabs button.on{{background:#a8323d;color:#fff;border-color:#a8323d}}
.die{{display:flex;align-items:center;justify-content:center;text-align:center;min-height:150px;padding:24px 20px;
 border:1px solid #e3dbcc;border-radius:14px;background:#fffdf8;font-size:20px;line-height:1.6}}
.src{{display:block;color:#8a8a8a;font-size:.8em;margin-top:2px}}
.src b{{color:#a8323d}}
.dice-btns{{display:flex;gap:8px;margin-top:12px;flex-wrap:wrap}}
.dice-btns button{{font:inherit;padding:11px 16px;border-radius:10px;border:1px solid #d8cfc0;background:#fbf8f3;cursor:pointer}}
.dice-btns .main{{background:#a8323d;color:#fff;border-color:#a8323d;flex:1}}
ol{{padding-left:22px}}li{{margin:5px 0}}
.grp h2 .n{{font-size:12px;color:#999;font-weight:400;margin-left:8px}}
.hide{{display:none}}
</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head><body>
<!-- NAV_START --><!-- NAV_END -->
<h1>词句库</h1>
<p class="meta">共 <b>{total}</b> 条（★★ 为高质量层 {high} 条）｜
{html.escape("／".join("%s %d" % (TYPE_CN.get(k, k), v) for k, v in by_type.items()))}</p>
<p class="tip">骰子在《深夜小酒馆》里也能用 —— <a href="/tavern/#dice" style="color:#a8323d">去小酒馆抽一句</a>（含「今天那句」按日期固定）。</p>

<h2>抽一句</h2>
<div id="tabs"></div>
<div class="die" id="die">点下面的按钮抽一句</div>
<p id="dsrc" style="color:#8a8a8a;font-size:13px;text-align:center;min-height:1.4em"></p>
<div class="dice-btns">
  <button class="main" id="draw">抽 一 句</button>
  <button id="today">今天那句</button>
  <button id="copy">复制</button>
  <button id="svg">存成图片</button>
</div>

<h2>检索</h2>
<div class="bar"><input id="q" placeholder="输入关键词，如 低音、不说、时间（可搜文本与出处）"></div>
{''.join(sections)}

<footer style="margin:34px 0 10px;color:#888;font-size:.85em">
词句来自公开内容整理；★ 越高越适合引用；玄学为娱乐向；歌词版权归原作者。
</footer>
<!-- FOOTER_NAV_START --><!-- FOOTER_NAV_END -->
<script>
var SETS = {tabs_json};
var cur = 0;
function tabs(){{
  var box=document.getElementById('tabs'), h='';
  for(var i=0;i<SETS.length;i++) h+='<button data-i="'+i+'" class="'+(i===cur?'on':'')+'">'+SETS[i].name+'</button>';
  box.innerHTML=h;
  box.querySelectorAll('button').forEach(function(b){{b.onclick=function(){{cur=+b.dataset.i;tabs();}};}});
}}
function show(i){{
  var t=SETS[cur], f=t.faces[i%t.faces.length];
  document.getElementById('die').textContent=f.text;
  document.getElementById('dsrc').innerHTML='<b style="color:#a8323d">'+t.name+'</b>｜出处：'+(f.source||t.note||'');
}}
function daySeed(){{
  var d=new Date(), s=d.getFullYear()+'/'+(d.getMonth()+1)+'/'+d.getDate()
    +'|'+(d.getFullYear()*37+d.getMonth());
  var h=2166136261;
  for(var i=0;i<s.length;i++){{ h^=s.charCodeAt(i); h=Math.imul(h,16777619)>>>0; }}
  h^=h>>>13; h=Math.imul(h,0x5bd1e995)>>>0; h^=h>>>15;
  return h;
}}
document.getElementById('draw').onclick=function(){{show(Math.floor(Math.random()*9999));}};
document.getElementById('today').onclick=function(){{show(daySeed());}};
document.getElementById('copy').onclick=function(){{
  var t=document.getElementById('die').textContent+'\\n—— '+document.getElementById('dsrc').textContent;
  if(navigator.clipboard) navigator.clipboard.writeText(t).then(function(){{alert('已复制');}},function(){{alert('复制失败');}});
}};
document.getElementById('svg').onclick=function(){{
  var text=document.getElementById('die').textContent;
  var src=document.getElementById('dsrc').textContent;
  var chars=text.split(''), lines=[], line='';
  for(var i=0;i<chars.length;i++){{ line+=chars[i]; if(line.length>=16){{lines.push(line);line='';}} }}
  if(line) lines.push(line);
  var y=300;
  var tspans=lines.map(function(l){{ y+=52; return '<text x="400" y="'+y+'" font-size="40" fill="#2a2a2a" text-anchor="middle" font-family="Microsoft YaHei, sans-serif">'+l+'</text>'; }}).join('');
  var svg='<svg xmlns="http://www.w3.org/2000/svg" width="800" height="1100">'
    +'<rect width="800" height="1100" fill="#fffdf8"/>'
    +'<rect x="40" y="40" width="720" height="1020" fill="none" stroke="#e3dbcc" stroke-width="2"/>'
    +'<text x="400" y="150" font-size="28" fill="#a8323d" text-anchor="middle" font-family="Microsoft YaHei">王晰 · 词句</text>'
    + tspans
    +'<text x="400" y="1000" font-size="18" fill="#9a9a9a" text-anchor="middle" font-family="Microsoft YaHei">'+src.replace(/[<>&]/g,'')+'</text>'
    +'<text x="400" y="1045" font-size="16" fill="#c0b8aa" text-anchor="middle" font-family="Microsoft YaHei">wx409.github.io</text>'
    +'</svg>';
  var a=document.createElement('a');
  a.href='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
  a.download='wangxi-quote.svg';
  a.click();
}};
document.getElementById('q').oninput=function(){{
  var v=this.value.trim().toLowerCase();
  document.querySelectorAll('.grp').forEach(function(sec){{
    var shown=0;
    sec.querySelectorAll('li').forEach(function(li){{
      var hit=!v||li.textContent.toLowerCase().indexOf(v)>=0;
      li.classList.toggle('hide',!hit);
      if(hit) shown++;
    }});
    sec.classList.toggle('hide',shown===0);
  }});
}};
tabs();
</script>
</body></html>
"""
(ROOT / "phrases.html").write_text(page, encoding="utf-8")
print("phrases.html 已生成：%d 条｜分组 %d｜骰套 %d" % (total, len(sections), len(tabs_list)))
