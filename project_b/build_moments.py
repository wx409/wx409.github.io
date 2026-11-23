#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_moments.py —— 瞬间库：半夜的话 / 现场的尖叫 / 路人的梗"""
from __future__ import annotations

import html
import json
import random
import sys
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
sys.path.insert(0, str(ROOT / "project_b"))
from banned_words import is_banned  # noqa

OUT = ROOT / "data" / "moments.json"
PAGE = ROOT / "moments.html"
RAW = Path(r"E:\wx\私有工具\bili_danmaku_fan")
RAW2 = Path(r"E:\wx\私有工具\bili_danmaku_dense")


def esc(s):
    return html.escape(str(s or ""))


def load(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def pick_quotes(items):
    kws = ("低音", "唱", "稳", "怕", "累", "孤独", "谢谢", "晚安", "舞台", "歌")
    out, seen = [], set()
    for x in items:
        q = (x.get("quote") or "").strip()
        if not (8 <= len(q) <= 42) or q in seen or is_banned(q):
            continue
        score = sum(1 for k in kws if k in q) + len(x.get("moods") or [])
        out.append((score, x))
        seen.add(q)
    out.sort(key=lambda t: -t[0])
    return [x for _, x in out[:12]]


def pick_danmaku(videos, timeline=None):
    tlmap = {x.get("bvid"): x for x in ((timeline or {}).get("videos") or [])}
    bad = ("考古", "没想到", "翻车", "reaction", "后台", "花絮", "采访", "综艺", "黄子", "尚雯婕", "张韶涵", "李琦", "鞠红川", "开车", "盘点", "合集", "直播", "预告", "三份工")
    good = ("现场", "live", "Live", "低音", "清唱", "官摄", "舞台", "巡演", "多听有益", "让她降落", "青藏高原", "City of Stars", "宝贝", "小毛驴", "女儿情", "雾里")
    cand = [v for v in videos if "王晰" in (v.get("title") or "") and not any(k in (v.get("title") or "") for k in bad)
            and any(k in (v.get("title") or "") for k in good)]
    rows = []
    for v in (cand or videos)[:8]:
        bv = v.get("bvid")
        lines = []
        for d in (RAW, RAW2):
            f = d / (bv + ".json")
            if f.exists():
                try:
                    j = json.loads(f.read_text(encoding="utf-8"))
                    lines = [x for x in (j.get("danmaku") or [])
                             if 4 <= len(x) <= 30 and not is_banned(x)]
                except Exception:
                    pass
                break
        random.seed(7 + len(rows))
        samples = random.sample(lines, min(3, len(lines))) if lines else []
        peak = (tlmap.get(bv) or {}).get("peaks") or []
        if peak:
            rows.append({"bvid": bv, "title": v.get("title"), "author": v.get("author"),
                         "count": peak[0].get("count") or (v.get("count") or 0),
                         "peak_t": peak[0].get("t"),
                         "samples": peak[0].get("samples") or samples})
        else:
            rows.append({"bvid": bv, "title": v.get("title"), "author": v.get("author"),
                         "count": v.get("count") or v.get("danmaku_count"), "samples": samples})
    return rows


def pick_memes(videos):
    bad = ("新年", "直播", "预告", "变装", "拍手", "光影", "乐华", "几巡", "女装", "让她降落", "摸摸毛", "噩梦", "百字明咒")
    good = ("低音", "声音", "好听", "现场", "开口", "唱", "稳", "鸡皮疙瘩", "耳朵", "震", "大提琴", "磁性", "妖僧", "功德", "按摩", "扭", "性感", "纯欲", "唐装", "西安")
    scored = []
    for v in videos:
        t = v.get("title") or ""
        if any(k in t for k in bad):
            continue
        cs = " ".join(v.get("top") or [])
        sc = sum(3 for k in good if k in cs) + (v.get("count") or 0) / 100.0
        if sc <= 0:
            continue
        scored.append((sc, v))
    scored.sort(key=lambda x: -x[0])
    return [v for _, v in scored[:8]]


def main():
    tav = load(ROOT / "data" / "tavern_citable.json")
    fan = load(ROOT / "data" / "bili_danmaku_fan.json")
    dy = load(ROOT / "data" / "douyin_comments.json")
    quotes = pick_quotes(tav.get("items") or [])
    screams = pick_danmaku(fan.get("videos") or [], load(ROOT / "data" / "danmaku_timeline.json"))
    memes = pick_memes(dy.get("videos") or [])
    for i, x in enumerate(quotes, 1):
        x["id"] = "q%02d" % i
    for i, x in enumerate(screams, 1):
        x["id"] = "s%02d" % i
    for i, x in enumerate(memes, 1):
        x["id"] = "m%02d" % i
    doc = {"generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
           "quotes": quotes, "screams": screams, "memes": memes}
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    try:
        picks = json.loads((ROOT / "data" / "moments_picks.json").read_text(encoding="utf-8")).get("picks") or []
    except Exception:
        picks = []
    by_id = {x["id"]: ("quote", x) for x in quotes}
    by_id.update({x["id"]: ("scream", x) for x in screams})
    by_id.update({x["id"]: ("meme", x) for x in memes})
    pick_cards = []
    for pid in picks:
        kind, x = by_id.get(pid, (None, None))
        if not kind:
            continue
        if kind == "quote":
            pick_cards.append('<div class="card"><div class="q">“%s”</div><div class="meta">★ 本周精选 · %s · %s</div></div>' % (esc(x["quote"]), esc(x.get("episode")), esc(x.get("time"))))
        elif kind == "scream":
            pick_cards.append('<div class="card"><div class="t">%s</div><div class="meta">★ 本周精选 · 弹幕峰值 %s 条</div></div>' % (esc(x["title"]), format(x.get("count") or 0, ",")))
        else:
            pick_cards.append('<div class="card"><div class="t">%s</div><div class="meta">★ 本周精选 · 评论 %s 条</div></div>' % (esc(x["title"]), format(x.get("count") or 0, ",")))
    picks_html = ('<h2>★ 本周精选</h2><div class="grid">%s</div>' % "".join(pick_cards)) if pick_cards else ""

    qhtml = "".join(
        '<div class="card"><img loading="lazy" src="/assets/share/quotes/q%02d.png" alt="王晰金句卡" '
        'style="width:100%%;border-radius:10px;margin-bottom:8px">'
        '<div class="q">“%s”</div><div class="meta">%s · %s · <a href="%s">原文</a></div></div>'
        % (i, esc(x["quote"]), esc(x.get("episode")), esc(x.get("time")), esc(x.get("url")))
        for i, x in enumerate(quotes, 1))
    shtml = ""
    for v in screams:
        pt = v.get("peak_t")
        when = ("%d:%02d" % (pt // 60, pt % 60)) if pt is not None else ""
        href = "https://www.bilibili.com/video/%s%s" % (v["bvid"], ("?t=%d" % pt) if pt is not None else "")
        meta = "%s · 弹幕峰值 %s 条%s" % (esc(v["author"]), format(v["count"] or 0, ","),
                                         (" @ " + when) if when else "")
        shtml += ('<div class="card"><div class="t">%s</div><div class="meta">%s</div>'
                  '<div class="sample">%s</div><a href="%s" target="_blank">从这一秒看</a></div>'
                  % (esc(v["title"]), meta, "".join("“%s” " % esc(s) for s in v["samples"]), href))
    mhtml = "".join(
        '<div class="card"><div class="t">%s</div><div class="meta">评论 %s 条</div>'
        '<div class="sample">%s</div><a href="https://www.douyin.com/video/%s" target="_blank">看原视频</a></div>'
        % (esc(v["title"]), format(v["count"] or 0, ","),
           "".join("“%s” " % esc(t) for t in (v.get("top") or [])[:3]), esc(v["id"])) for v in memes)

    ldjson = json.dumps({
        "@context": "https://schema.org", "@type": "CollectionPage",
        "name": "值得转发的王晰｜瞬间库",
        "description": "王晰的小酒馆金句、B站弹幕峰值与抖音路人评论，每条带出处或原视频。",
        "url": "https://wx409.github.io/moments.html",
        "about": {"@type": "Person", "name": "王晰"},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(quotes) + len(screams) + len(memes)},
    }, ensure_ascii=False)

    page = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>值得转发的王晰｜瞬间库</title>
<meta name="description" content="王晰值得转发的瞬间：小酒馆里半夜说的话、B站现场的观众弹幕、抖音路人的玩梗评论。每条带出处/时间码/原视频，供同担做内容时直接取用。">
<meta property="og:type" content="website">
<meta property="og:title" content="值得转发的王晰｜瞬间库">
<meta property="og:description" content="金句、现场弹幕峰值、路人梗；每条带出处，同担可直接取用。">
<meta property="og:image" content="https://wx409.github.io/assets/share/og_moments.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="robots" content="index, follow"><meta name="llms" content="1"><link rel="canonical" href="https://wx409.github.io/moments.html">
<script type="application/ld+json">%s</script>
<style>body{margin:0;background:#faf9f7;color:#1f2328;font:16px/1.75 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}
main{max-width:1000px;margin:0 auto;padding:28px 20px 60px}h1{font-size:30px;margin:8px 0 4px}.sub{color:#666;margin:0 0 20px}
h2{font-size:21px;margin:34px 0 12px;border-left:4px solid #a8323d;padding-left:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.card{background:#fff;border:1px solid #e6e2dc;border-radius:12px;padding:14px 16px}
.q{font-size:17px;line-height:1.8;color:#1f2328}.t{font-weight:600;font-size:15px;line-height:1.5}
.meta{color:#888;font-size:12.5px;margin-top:6px}.sample{color:#555;font-size:13.5px;margin:8px 0}
a{color:#a8323d;text-decoration:none}.tip{background:#fffdf8;border:1px solid rgba(184,145,46,.35);border-radius:10px;padding:12px 16px;font-size:14px;color:#6b5320}
</style></head><body><main>
<h1>值得转发的王晰</h1>
<p class="sub">不给结论，给素材：每条都带出处、时间码或原视频，同担可直接取用。</p>
<div class="tip">用法：挑一条 → 复制原话/标题 → 按平台改写成 15 秒脚本或图文 → 回链原视频/本站。不要剪掉出处，不要伪造引语。</div>
__PICKS__
<h2>一、半夜的话（小酒馆）</h2><div class="grid">%s</div>
<h2>二、现场的尖叫（B站弹幕）</h2><div class="grid">%s</div>
<h2>三、路人的梗（抖音评论）</h2><div class="grid">%s</div>
<p class="sub" style="margin-top:30px">数据：tavern_citable / bili_danmaku_fan / douyin_comments｜更新 %s｜只做聚合与短引用，原视频/原文以链接为准。</p>
</main></body></html>""" % (ldjson, qhtml, shtml, mhtml, esc(doc["generated_at"]))
    PAGE.write_text(page.replace("__PICKS__", picks_html), encoding="utf-8")
    print("写入", PAGE, "| quotes", len(quotes), "| screams", len(screams), "| memes", len(memes))


if __name__ == "__main__":
    main()
