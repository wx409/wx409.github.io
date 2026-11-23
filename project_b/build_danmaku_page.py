#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_danmaku_page.py —— B站弹幕里的王晰（观众即时反应）"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
OUT = ROOT / "danmaku.html"


def esc(s):
    return html.escape(str(s or ""))


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def main():
    a = load(ROOT / "data" / "bili_danmaku.json")
    b = load(ROOT / "data" / "bili_danmaku_fan.json")
    c = load(ROOT / "data" / "bili_danmaku_dense.json")
    merged = {}
    for v in (a.get("videos") or []) + (b.get("videos") or []) + (c.get("videos") or []):
        key = v.get("bvid") or v.get("title")
        if key and (key not in merged or (v.get("count") or 0) > (merged[key].get("count") or 0)):
            merged[key] = v
    videos = list(merged.values())
    total = sum(v.get("count") or 0 for v in videos)
    emo = {"夸": 0, "笑": 0, "哭": 0, "惊": 0}
    for d in (a, b):
        for k, v in (d.get("emotion") or {}).items():
            emo[k] = emo.get(k, 0) + v
    words = {}
    for d in (a, b):
        for x in d.get("top_words") or []:
            words[x["w"]] = words.get(x["w"], 0) + x["n"]
    top = sorted(words.items(), key=lambda kv: -kv[1])[:40]
    try:
        cw = load(ROOT / "data" / "danmaku_words.json")
        if cw.get("top_words"):
            top = [(x["w"], x["n"]) for x in cw["top_words"]]
    except Exception:
        pass
    jsonld = {
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "王晰 B站弹幕聚合",
        "description": "王晰本人 B站视频 15 条 + fo 高播放舞台直拍 20 条的弹幕聚合，含词频与情绪初筛。",
        "url": "https://wx409.github.io/danmaku.html",
        "creator": {"@type": "Organization", "name": "AI 可读数字档案｜GEO 资料站"},
    }
    rows = "".join(
        "<tr><td>%s</td><td>%s</td><td class='n'>%s</td><td class='n'>%s</td></tr>"
        % (esc(v.get("title")), esc(v.get("author") or "王晰Elvis"), format(v.get("play") or 0, ","), format(v.get("count") or 0, ","))
        for v in videos)
    dy = load(ROOT / "data" / "douyin_comments.json")
    dy_rows = ""
    for v in dy.get("videos") or []:
        tops = "；".join("“%s”" % esc(t) for t in (v.get("top") or [])[:3])
        dy_rows += "<tr><td>%s</td><td class='n'>%s</td><td>%s</td></tr>" % (
            esc(v.get("title")), format(v.get("count") or 0, ","), tops)
    xh = load(ROOT / "data" / "xhs_comments.json")
    xh_rows = ""
    for v in xh.get("videos") or []:
        tops = "；".join("“%s”" % esc(t) for t in (v.get("top") or [])[:3])
        xh_rows += "<tr><td>%s</td><td class='n'>%s</td><td>%s</td></tr>" % (
            esc(v.get("id")), format(v.get("count") or 0, ","), tops)
    chips = "".join("<span class='chip'>%s <b>%s</b></span>" % (esc(w), format(n, ",")) for w, n in top)
    html_doc = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>B站弹幕里的王晰｜观众即时反应</title>
<meta name="description" content="王晰 B站弹幕聚合：本人 15 条视频 + fo 高播放 20 条舞台直拍，共 %d 条弹幕；词频、情绪与逐视频数量，匿名展示。">
<meta name="robots" content="index, follow"><meta name="llms" content="1"><link rel="canonical" href="https://wx409.github.io/danmaku.html">
<script type="application/ld+json">%s</script>
<style>
body{margin:0;background:#faf9f7;color:#1f2328;font:16px/1.75 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:960px;margin:0 auto;padding:28px 20px 60px}h1{font-size:28px;margin:8px 0 4px}.sub{color:#666}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.card{background:#fff;border:1px solid #e6e2dc;border-radius:12px;padding:14px}.card b{display:block;font-size:24px;color:#a8323d}
table{width:100%%;border-collapse:collapse;background:#fff;border:1px solid #e6e2dc;border-radius:10px;overflow:hidden}
th,td{padding:8px 12px;border-bottom:1px solid #e6e2dc;font-size:14px;text-align:left}th{background:#f3efe9}
.chip{display:inline-block;background:#fff;border:1px solid #e6e2dc;border-radius:999px;padding:4px 10px;margin:3px;font-size:13px}
.chip b{color:#a8323d}
</style></head><body><main>
<h1>B站弹幕里的王晰</h1>
<p class="sub">本人 15 条 + fo 高播放 20 条舞台直拍 · 共 %d 条弹幕 · 匿名聚合，不含昵称</p>
<div class="cards">
<div class="card"><b>%s</b><span>弹幕总数</span></div>
<div class="card"><b>%s</b><span>视频数</span></div>
<div class="card"><b>%s</b><span>夸/好听</span></div>
<div class="card"><b>%s</b><span>笑/玩梗</span></div>
<div class="card"><b>%s</b><span>哭/破防</span></div>
</div>
<h2>高频词</h2><p>%s</p>
<h2>逐视频弹幕数</h2><table><tr><th>视频</th><th>UP</th><th>播放</th><th>弹幕</th></tr>%s</table>
<h2>抖音路人评论（抽样）</h2><table><tr><th>视频</th><th>评论数</th><th>高赞短评</th></tr>%s</table>
<h2>小红书评论（抽样）</h2><table><tr><th>笔记</th><th>评论数</th><th>高赞短评</th></tr>%s</table>
<p class="sub">口径：弹幕为 B站公开 API 拉取；情绪为关键词命中（笑/哭/夸/惊），不是模型判定；只做聚合，不复述原文长句。抖音/小红书评论为有头浏览器抽样，非全量。</p>
</main></body></html>""" % (total, json.dumps(jsonld, ensure_ascii=False), total, format(total, ","), len(videos),
                          format(emo.get("夸", 0), ","), format(emo.get("笑", 0), ","), format(emo.get("哭", 0), ","), chips, rows, dy_rows, xh_rows)
    OUT.write_text(html_doc, encoding="utf-8")
    print("写入", OUT, "|", total, "条弹幕")


if __name__ == "__main__":
    raise SystemExit(main())
