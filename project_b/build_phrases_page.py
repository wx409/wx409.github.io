"""生成 phrases.html —— 词句骰子页（数据取自 data/dice_sets.json 与 data/phrase_bank.json）
纪律：不写死数字；玄学标“娱乐向，非占卜”；歌词类只出短句；缺套写“待补”并给原因。
"""
import json, html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
dice = json.loads((ROOT / "data" / "dice_sets.json").read_text(encoding="utf-8"))
bank = json.loads((ROOT / "data" / "phrase_bank.json").read_text(encoding="utf-8"))

sets = dice["sets"]
pending = dice.get("pending") or []
total_faces = sum(len(v.get("faces") or []) for v in sets.values())
total_phrases = bank.get("count", len(bank.get("items") or []))
by_type = bank.get("by_type") or {}

TABS = []
for key, v in sets.items():
    faces = [f for f in (v.get("faces") or []) if f]
    if not faces:
        continue
    TABS.append({"key": key, "name": v["name"], "faces": faces,
                 "note": v.get("disclaimer", "")})

tabs_json = json.dumps(TABS, ensure_ascii=False)

rows = []
for t in TABS:
    lis = "".join("<li>%s</li>" % html.escape(f) for f in t["faces"])
    rows.append("<section class='set'><h2>%s<span class='n'>%d 面</span></h2><ol>%s</ol><p class='note'>%s</p></section>"
                % (html.escape(t["name"]), len(t["faces"]), lis, html.escape(t["note"])))

pend_html = ""
if pending:
    items = "".join("<li><b>%s</b>：%s</li>" % (html.escape(p.get("name", "")), html.escape(p.get("reason", "")))
                    for p in pending)
    pend_html = "<h2>待补</h2><ul class='pending'>%s</ul>" % items

dist = "／".join("%s %d" % (k, v) for k, v in by_type.items())

ld = {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "词句｜骰子",
    "about": {"@type": "Person", "name": "王晰"},
    "description": "把王晰说过的话、歌名、采访与卦象引语做成可抽的骰子；每条带出处。",
    "isPartOf": {"@type": "WebSite", "url": "https://wx409.github.io/"},
    "url": "https://wx409.github.io/phrases.html",
}

page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>词句｜骰子</title>
<link rel="canonical" href="https://wx409.github.io/phrases.html">
<style>
body{{font:15px/1.7 -apple-system,Segoe UI,Microsoft YaHei,sans-serif;max-width:820px;margin:24px auto;padding:0 16px;color:#222}}
h1{{margin:0 0 4px}}h2{{font-size:17px;margin:26px 0 8px;border-left:4px solid #a8323d;padding-left:8px}}
.meta{{color:#666;font-size:.9em;margin:0 0 18px}}
.tabs{{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}}
.tabs button{{font:inherit;padding:8px 14px;border:1px solid #d8cfc0;background:#fbf8f3;border-radius:999px;cursor:pointer}}
.tabs button.on{{background:#a8323d;color:#fff;border-color:#a8323d}}
.die{{display:flex;align-items:center;justify-content:center;text-align:center;min-height:180px;
 padding:26px 22px;border:1px solid #e3dbcc;border-radius:14px;background:#fffdf8;font-size:22px;line-height:1.6}}
.src{{color:#777;font-size:.88em;margin:10px 0 0;text-align:center}}
.draw{{display:block;width:100%;font:inherit;font-size:16px;padding:12px;margin-top:12px;border:0;border-radius:10px;background:#a8323d;color:#fff;cursor:pointer}}
ol{{padding-left:22px}}li{{margin:4px 0}}
.set h2 .n{{font-size:12px;color:#999;font-weight:400;margin-left:8px}}
.note{{color:#816;font-size:.85em;background:#fbf4f6;border-radius:8px;padding:8px 10px}}
.pending{{color:#666}}
footer{{margin:34px 0 10px;color:#888;font-size:.85em}}
</style>
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
</head><body>
<!-- NAV_START --><!-- NAV_END -->
<h1>词句｜骰子</h1>
<p class="meta">把他说过的话、歌名、采访与卦象引语做成可以抽的骰子。共 <b>{total_phrases}</b> 条词句（{html.escape(dist)}），
现可抽 <b>{total_faces}</b> 面、<b>{len(TABS)}</b> 套；<b>每条都带出处</b>，抽到就能追。</p>

<div class="tabs" id="tabs"></div>
<div class="die" id="die">点下面的按钮抽一句</div>
<p class="src" id="src"></p>
<button class="draw" id="draw">抽 一 句</button>

{"".join(rows)}
{pend_html}

<h2>说明</h2>
<ul>
<li><b>玄学套</b>取自站内整理的卦象解析表，标“娱乐向，非占卜”。</li>
<li><b>歌名套</b>是歌名＋官方一句说明，不是歌词全文；歌词只做短句引用。</li>
<li><b>采访套</b>含标题与备注，部分不是逐字引语，已在来源中注明。</li>
<li>所有条目在 <code>data/phrase_bank.json</code>，可核对、可增补。</li>
</ul>

<footer>词句来自公开内容整理；玄学为娱乐向；歌词版权归原作者。</footer>
<!-- FOOTER_NAV_START --><!-- FOOTER_NAV_END -->
<script>
var SETS = {tabs_json};
var cur = 0;
function render() {{
  var t = SETS[cur], box = document.getElementById('tabs'), html = '';
  for (var i = 0; i < SETS.length; i++) {{
    html += '<button data-i="' + i + '" class="' + (i === cur ? 'on' : '') + '">' + SETS[i].name + '</button>';
  }}
  box.innerHTML = html;
  box.querySelectorAll('button').forEach(function (b) {{
    b.onclick = function () {{ cur = +b.dataset.i; render(); }};
  }});
  document.getElementById('die').textContent = '点下面的按钮抽一句';
  document.getElementById('src').textContent = '';
}}
function draw() {{
  var t = SETS[cur], f = t.faces[Math.floor(Math.random() * t.faces.length)];
  document.getElementById('die').textContent = f;
  document.getElementById('src').textContent = t.name + '｜' + t.note;
}}
document.getElementById('draw').onclick = draw;
render();
</script>
</body></html>
"""

(ROOT / "phrases.html").write_text(page, encoding="utf-8")
print("phrases.html 已生成｜词句 %d｜骰套 %d｜面 %d｜待补 %d" % (total_phrases, len(TABS), total_faces, len(pending)))
