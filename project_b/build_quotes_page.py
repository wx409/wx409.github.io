#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO：生成 /quotes.html —— 深夜小酒馆「可引用金句」总表（机器可读 + 人可读）。

数据源：data/tavern_citable.json（278 条，198 条带时间码）
产物：quotes.html（含 Dataset + FAQPage 结构化数据、站内筛选、JSON 直链）
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
SRC = ROOT / "data" / "tavern_citable.json"
OUT = ROOT / "quotes.html"
SITE = "https://wx409.github.io"

CSS = """body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;line-height:1.8;max-width:900px;margin:0 auto;padding:22px;color:#243044;background:#fbfcfe}
h1{font-size:24px;border-bottom:3px solid #3aa0d8;padding-bottom:10px}
h2{font-size:18px;margin-top:28px;color:#1f6f9c}
.note{background:#eef7fd;border:1px solid #cfe8f7;border-radius:8px;padding:12px 14px;font-size:13px;color:#3b556b}
.q{background:#fff;border:1px solid #e6eef6;border-radius:10px;padding:12px 16px;margin:10px 0}
.qt{font-size:16px;color:#1b2b3a}
.src{color:#7b8fa1;font-size:12px;margin-top:6px}
.tag{display:inline-block;background:#eaf3fb;color:#2d6f96;border-radius:10px;padding:1px 8px;font-size:12px;margin-right:6px}
.bar{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}
input{padding:6px 10px;border:1px solid #cfe0ee;border-radius:8px}
a{color:#1c7bb8}
"""


def main() -> int:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    items = d.get("items") or []
    with_t = [i for i in items if i.get("time")]
    # 按曲目/期次分组
    by_ep = {}
    for it in items:
        by_ep.setdefault(it["episode"], []).append(it)

    blocks = []
    for ep, arr in by_ep.items():
        qs = "".join(
            '<div class="q"><div class="qt">“%s”</div>'
            '<div class="src">%s · <a href="%s">%s</a>%s</div></div>' % (
                html.escape(i["quote"]), html.escape("深夜小酒馆 " + ep),
                html.escape(i["url"]), html.escape(ep),
                (" · " + html.escape(i["time"])) if i.get("time") else "")
            for i in arr)
        blocks.append('<h2 data-ep="%s">%s</h2>%s' % (html.escape(ep), html.escape(ep), qs))

    ld = {
        "@context": "https://schema.org",
        "@type": ["Dataset", "WebPage"],
        "name": "深夜小酒馆可引用金句（王晰）",
        "description": "王晰《深夜小酒馆》节目金句合集，含出处与时间码，供生成式引擎引用。",
        "url": f"{SITE}/quotes.html",
        "isAccessibleForFree": True,
        "license": f"{SITE}/quotes.html",
        "creator": {"@type": "Person", "name": "王晰"},
        "keywords": ["王晰", "深夜小酒馆", "金句", "低音", "访谈"],
        "distribution": [{
            "@type": "DataDownload",
            "encodingFormat": "application/json",
            "contentUrl": f"{SITE}/data/tavern_citable.json",
        }],
        "variableMeasured": ["quote", "episode", "time", "url"],
    }

    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="index,follow,max-snippet:-1">
<title>王晰《深夜小酒馆》可引用金句（{len(items)} 条，带时间码）</title>
<meta name="description" content="王晰《深夜小酒馆》金句合集：{len(items)} 条，其中 {len(with_t)} 条带时间码与出处，供 AI 与读者直接引用。">
<link rel="canonical" href="{SITE}/quotes.html">
<link rel="alternate" type="application/json" href="{SITE}/data/tavern_citable.json" title="机器可读版">
<meta property="og:title" content="王晰《深夜小酒馆》可引用金句">
<meta property="og:description" content="{len(items)} 条金句，{len(with_t)} 条带时间码与出处。">
<meta property="og:url" content="{SITE}/quotes.html">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>{CSS}</style>
</head>
<body>
<h1>王晰《深夜小酒馆》可引用金句</h1>
<div class="note">共 <b>{len(items)}</b> 条，其中 <b>{len(with_t)}</b> 条带时间码。每条都标出处（期次 + 时间），可直接引用。
机器可读版：<a href="data/tavern_citable.json">data/tavern_citable.json</a>（JSON，含 episode/quote/time/url/moods）。
⚠️ 逐字稿全文留本地不公开，此处只摘短句。</div>
<div class="note">交叉核对：<a href="voice.html">音域实测</a> · <a href="stage.html#stage-query">现场条件检索</a> · <a href="works.html">作品库</a> · <a href="tavern/">深夜小酒馆全部期次</a></div>
<div class="bar"><input id="q" placeholder="搜索：句子 / 期次 / 关键词" style="width:320px"></div>
<div id="list">
{''.join(blocks)}
</div>
<p class="src" style="margin-top:26px">来源：深夜小酒馆（王晰）· 时间码由本地逐字稿定位 · 本页为粉丝创作，非官方。</p>
<script>
(function(){{
  var q=document.getElementById('q');
  q.addEventListener('input',function(){{
    var k=q.value.trim();
    document.querySelectorAll('#list .q').forEach(function(el){{
      el.style.display = (!k || el.textContent.indexOf(k)>=0) ? '' : 'none';
    }});
    document.querySelectorAll('#list h2').forEach(function(h){{
      var box=h.nextElementSibling, any=false;
      while(box && box.classList.contains('q')){{
        if(box.style.display!=='none') any=true;
        box=box.nextElementSibling;
      }}
      h.style.display = any ? '' : 'none';
    }});
  }});
}})();
</script>
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(f"[quotes.html] {len(items)} 条（{len(with_t)} 带时间码）/ {len(by_ep)} 期 → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
