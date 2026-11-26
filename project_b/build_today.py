#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_today.py —— 今日 B站新入库：数据摘要 + today.html + 首页条"""
from __future__ import annotations

import html
import json
from datetime import date
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
SRC = ROOT / "data" / "bili_daily.json"
OUT = ROOT / "today.html"
JSONOUT = ROOT / "data" / "today.json"


def esc(s):
    return html.escape(str(s or ""))


def clean_title(t):
    t = str(t or "")
    t = t.rsplit(".mp4", 1)[0]
    t = t.split("_", 1)[-1].strip() or t
    t = t.replace("王晰", "").strip()
    return t


def main():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    today = date.today().isoformat()
    fresh = d.get("date") == today
    items = (d.get("items") or []) if fresh else []
    measured = [x for x in items if x.get("measured")]
    measured.sort(key=lambda x: (x["measured"].get("low", {}).get("hz") or 999))
    day = d.get("date") or today
    status = "今日已更新" if fresh else "今日自动化未完成；显示的是 %s 的旧档案" % day
    if not fresh:
        headline = "今天的新入库还没跑完。"
        bullets = ["不拿旧内容冒充今天；最后成功：%s。" % day,
                   "下次检查：12:10 自动补跑，失败会发站内告警。"]
    elif not items:
        headline = "今天没有新的 B站视频入库。"
        bullets = ["没有新视频，不等于没有内容：旧档案还在，可以先听一首。"]
    else:
        headline = "今天补到 %d 条 B站视频，%d 条做了声学测量。" % (len(items), len(measured))
        bullets = []
        if measured:
            lo = measured[0]
            bullets.append("最低音出现在 %s：%s %sHz。" % (
                clean_title(lo["title"]), lo["measured"]["low"].get("note"), lo["measured"]["low"].get("hz")))
            live = [x for x in measured if "直拍" in x["title"] or "点歌" in x["title"]]
            if live:
                lv = min(live, key=lambda x: x["measured"]["low"].get("hz") or 999)
                bullets.append("现场类最低：%s %sHz（《%s》）。" % (
                    lv["measured"]["low"].get("note"), lv["measured"]["low"].get("hz"), clean_title(lv["title"])))
            bullets.append("稳定音不是越低越好：这次现场直拍的稳定最低多在 F2–B2，完整乐队直拍不适合拿来刷最低音。")
        quotes = []
        for x in items:
            qs = [q for q in (x.get("quotes") or []) if 8 <= len(q) <= 80 and any(k in q for k in ("低音", "唱", "稳", "嗓子"))]
            if qs and qs[0] not in quotes:
                quotes.append(qs[0])
        if quotes:
            bullets.append("访谈/转写里提到：“%s”（转写未逐字校对）" % quotes[0][:70])

    cards = "".join(
        '<div class="card"><div class="t">%s</div><div class="meta">%s · 稳定最低 %s %sHz · 跨度 %s 八度 · 稳定性 %s 音分</div>%s</div>'
        % (esc(clean_title(x["title"])), esc(x["bvid"]),
           esc(x["measured"]["low"].get("note")), esc(x["measured"]["low"].get("hz")),
           esc(x["measured"].get("span")), esc(x["measured"].get("stability")),
           "".join('<div class="q">“%s”</div>' % esc(q) for q in (x.get("quotes") or [])[:1]))
        for x in measured)

    page = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>今天，网站新收了什么｜王晰数字档案</title>
<meta name="description" content="每天更新：B站新入库视频、声学测量结果与访谈里的唱法线索。不是通稿，是今天新发生的事。">
<meta name="robots" content="index, follow"><meta name="llms" content="1"><link rel="canonical" href="https://wx409.github.io/today.html">
<meta property="og:type" content="website"><meta property="og:title" content="今天，网站新收了什么">
<meta property="og:image" content="https://wx409.github.io/assets/share/og_moments.png">
<style>body{margin:0;background:#faf9f7;color:#1f2328;font:16px/1.8 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:860px;margin:0 auto;padding:28px 20px 60px}h1{font-size:28px;margin:8px 0 4px}.sub{color:#666}
h2{font-size:20px;margin:26px 0 8px;border-left:4px solid #a8323d;padding-left:10px}
.card{background:#fff;border:1px solid #e6e2dc;border-radius:10px;padding:12px 14px;margin:8px 0}
.t{font-weight:600}.meta{color:#777;font-size:13px;margin-top:3px}.q{color:#a8323d;font-size:13px;margin-top:6px}
.tip{background:#fffdf8;border:1px solid rgba(184,145,46,.35);border-radius:10px;padding:10px 14px;font-size:14px;color:#6b5320}
a{color:#a8323d;text-decoration:none}</style></head><body><main>
<h1>今天，网站新收了什么</h1>
<p class="sub">%s ｜ %s ｜ 自动汇总 B站官方空间、转写与声学初测</p>
<div class="tip"><b>%s</b><br>%s</div>
<h2>声学初测</h2>%s
<h2>怎么读</h2>
<p class="sub">稳定最低音按 ≥0.15s、HNR≥5dB、极值音本身≥0.2s 过滤；原始 F0 更低不等于“能唱到”。完整乐队直拍受编曲/混音影响，不用于刷最低音纪录。</p>
<p class="sub">完整数据：<a href="/dashboard/">数据大屏</a> · <a href="/voice.html">B1 是什么概念</a> · <a href="/vocal.html">音域实测</a></p>
</main></body></html>""" % (esc(day), esc(status), esc(headline), "<br>".join(esc(x) for x in bullets), cards or "<p class='sub'>今天没有可测量的歌曲视频。</p>")

    OUT.write_text(page, encoding="utf-8")
    summary = {"date": day, "fresh": fresh, "status": status,
               "new_count": len(items), "measured_count": len(measured),
               "headline": headline, "bullets": bullets,
               "updated_at": d.get("generated_at") or ""}
    JSONOUT.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print("today", day, "| items", len(items), "| measured", len(measured))


if __name__ == "__main__":
    main()
