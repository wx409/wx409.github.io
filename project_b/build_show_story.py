# -*- coding: utf-8 -*-
"""build_show_story.py v2 —— 全量故事页工厂（64 场体检 → 门槛 → 三幕页 + 索引两区）

门槛：曲目 ≥10 且（现场素材 ≥1 或 有反馈）→ 可生成；否则进「待补」，不生成空壳页。
slug：`story-<city拼音>-<YYYYMMDD>.html`；已上线的沉响两页沿用原 slug。
每页三幕；缺数据的一幕如实写「本场未采集」。页底互链：同城其它场次 / 同巡其它场（各 ≤5）。
"""
from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
KEEP_SLUG = {"2026-10-09": "chenxiang-20261009", "2026-10-10": "chenxiang-20261010"}
PINYIN = {"北京": "beijing", "上海": "shanghai", "广州": "guangzhou", "深圳": "shenzhen",
          "杭州": "hangzhou", "南京": "nanjing", "武汉": "wuhan", "长沙": "changsha",
          "成都": "chengdu", "重庆": "chongqing", "西安": "xian", "郑州": "zhengzhou",
          "厦门": "xiamen", "珠海": "zhuhai", "太原": "taiyuan", "海口": "haikou",
          "昆明": "kunming", "南昌": "nanchang", "青岛": "qingdao", "沈阳": "shenyang",
          "天津": "tianjin", "苏州": "suzhou", "宁波": "ningbo", "佛山": "foshan",
          "合肥": "hefei", "福州": "fuzhou", "贵阳": "guiyang", "南宁": "nanning"}


def load(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d


def slug_for(date: str, city: str) -> str:
    if date in KEEP_SLUG:
        return KEEP_SLUG[date]
    return f"{PINYIN.get(city, 'shows')}-{date.replace('-', '')}"


def bar_svg(items, color="#a8323d"):
    if not items:
        return ""
    mx = max(v for _, v in items) or 1
    h, w = 18, 320
    rows = []
    for i, (k, v) in enumerate(items):
        bw = int(v / mx * (w - 110))
        rows.append(f'<text x="0" y="{i*h+12}" font-size="11" fill="#444">{html.escape(str(k))}</text>'
                    f'<rect x="90" y="{i*h+3}" width="{bw}" height="10" fill="{color}" opacity="0.85"/>'
                    f'<text x="{95+bw}" y="{i*h+12}" font-size="10" fill="#666">{v}</text>')
    return f'<svg width="{w}" height="{len(items)*h+6}" role="img">' + "".join(rows) + "</svg>"


def main() -> int:
    setl = (load(D / "setlists.json", {}) or {}).get("setlists") or {}
    stage = load(D / "archive_stage_tour.json", {}) or {}
    rows = stage.get("rows") or []
    mat = Counter(str(r.get("date")) for r in rows if r.get("date"))
    by_date = defaultdict(list)
    for r in rows:
        by_date[str(r.get("date"))].append(r)
    fb = {}
    for f in (D / "show_blocks").glob("*.json"):
        m = re.search(r"(20\d{2})(\d{2})(\d{2})", f.name)
        if m:
            fb[f"{m.group(1)}-{m.group(2)}-{m.group(3)}"] = (load(f, {}) or {}).get("feedback") or {}
    shows = []
    for date, v in setl.items():
        songs = [x.get("title") if isinstance(x, dict) else x for x in (v.get("songs") or [])]
        songs = [x for x in songs if x]
        shows.append({"date": date, "city": v.get("city") or "", "tour": v.get("tour") or "",
                      "venue": v.get("venue") or "", "songs": songs,
                      "materials": mat.get(date, 0), "feedback": (fb.get(date) or {}).get("total") or 0})
    shows.sort(key=lambda x: x["date"])
    gate = lambda s: len(s["songs"]) >= 10 and (s["materials"] >= 1 or s["feedback"] >= 1)
    ok = [s for s in shows if gate(s)]
    pend = [s for s in shows if not gate(s)]

    built = []
    for s in ok:
        slug = slug_for(s["date"], s["city"])
        rr = by_date.get(s["date"]) or []
        spans = [r.get("span_octaves") for r in rr if r.get("span_octaves")]
        f = fb.get(s["date"]) or {}
        dims = f.get("dimensions") or {}
        _lows = [r for r in rr if r.get("low_hz")]
        low_row = min(_lows, key=lambda r: r["low_hz"]) if _lows else None
        title = f"{s['tour'] or '演出'}·{s['city']} {s['date']}"
        H = ["<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
             "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
             f"<title>{html.escape(title)}｜三幕故事</title>",
             f"<link rel=\"canonical\" href=\"https://wx409.github.io/story-{slug}.html\">",
             "<script type=\"application/ld+json\">" + json.dumps({
                 "@context": "https://schema.org", "@type": "Article", "headline": title,
                 "datePublished": s["date"],
                 "about": {"@type": "MusicEvent", "name": title, "startDate": s["date"],
                           "location": {"@type": "Place", "name": s["venue"] or s["city"]}},
                 "isAccessibleForFree": True,
                 "url": f"https://wx409.github.io/story-{slug}.html"}, ensure_ascii=False) + "</script>",
             "<style>body{font:15px/1.8 -apple-system,Segoe UI,Microsoft YaHei,sans-serif;max-width:820px;"
             "margin:24px auto;padding:0 16px}h2{margin-top:1.6em;font-size:1.15em}.meta{color:#666;font-size:.9em}"
             "figure{margin:14px 0;padding:10px;background:#fafafa;border-radius:6px}figcaption{color:#555;"
             "font-size:.9em;margin-top:6px}ul{margin:6px 0 6px 18px}</style></head><body>",
             "<!-- NAV_START --><!-- NAV_END -->",
             f"<h1>{html.escape(title)}</h1>",
             f"<p class=\"meta\">{s['date']}｜{html.escape(s['venue'] or s['city'])}｜数据截至 {stage.get('generated_at','')[:10]}</p>"]
        H.append("<h2>一 · 开场</h2>")
        H.append(f"<p>这一场登记曲目 <b>{len(s['songs'])}</b> 首，城市 {html.escape(s['city'])}。"
                 f"现场层里能对上读数的素材 <b>{s['materials']}</b> 条。</p>")
        H.append("<figure>" + bar_svg([("曲目", len(s["songs"])), ("可用素材", s["materials"])]) +
                 "<figcaption>图 1：曲目规模与可用素材条数。素材少于曲目数是常态——能测的只有拿到音轨的那些。</figcaption></figure>")
        H.append(f"<p class=\"meta\">证据：setlists.json#{s['date']}；archive_stage_tour.json#rows[date={s['date']}]</p>")
        H.append("<h2>二 · 中场</h2>")
        if low_row:
            H.append(f"<p>这一场测到的最低稳定音是 <b>{low_row.get('low_note')} {low_row.get('low_hz')} Hz</b>，"
                     f"出现在《{html.escape(str(low_row.get('song')))}》。口径：音符≥0.2s、HNR≥5dB、强度≥中位−25dB，"
                     "并过谐波列；极值音归属未定。</p>")
            if spans:
                H.append("<figure>" + bar_svg([(r.get("song"), r["span_octaves"]) for r in rr[:6]
                                               if r.get("span_octaves")]) +
                         "<figcaption>图 2：前几首曲目的跨度（八度）。跨度是整首的音域宽度，不评价唱得好不好。</figcaption></figure>")
        else:
            H.append("<p>本场未采集：没有可用的低音读数。</p>")
        H.append(f"<p class=\"meta\">证据：archive_stage_tour.json（date={s['date']}）</p>")
        H.append("<h2>三 · 结尾</h2>")
        if dims:
            items = sorted(dims.items(), key=lambda x: -x[1])[:6]
            H.append(f"<p>观众反馈共 <b>{f.get('total')}</b> 条，按维度最多的是"
                     f"「{html.escape(items[0][0])}」{items[0][1]} 条。</p>")
            H.append("<figure>" + bar_svg(items) +
                     "<figcaption>图 3：反馈维度分布。统计的是提到什么，不是评价好坏。</figcaption></figure>")
        else:
            H.append("<p>本场未采集：没有按维度分类的观众反馈。</p>")
        H.append(f"<p class=\"meta\">证据：show_blocks（{s['date']}）</p>")
        same_city = [x for x in ok if x["city"] == s["city"] and x["date"] != s["date"]][:5]
        same_tour = [x for x in ok if x["tour"] == s["tour"] and x["city"] != s["city"]][:5]
        H.append("<h2>同城其它场次 / 同巡其它场</h2><ul>")
        for x in same_city:
            H.append(f'<li>同城：<a href="story-{slug_for(x["date"], x["city"])}.html">{x["date"]} {html.escape(x["city"])}</a></li>')
        for x in same_tour:
            H.append(f'<li>同巡：<a href="story-{slug_for(x["date"], x["city"])}.html">{x["date"]} {html.escape(x["city"])}</a></li>')
        H.append('</ul><p class="meta"><a href="stories.html">← 全部故事</a></p></body></html>')
        (SITE / f"story-{slug}.html").write_text("\n".join(H), encoding="utf-8")
        built.append({**s, "slug": slug, "songs_n": len(s["songs"])})

    I = ["<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
         "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
         "<title>场次故事｜三幕结构</title>",
         "<link rel=\"canonical\" href=\"https://wx409.github.io/stories.html\">",
         "<style>body{font:15px/1.7 -apple-system,Segoe UI,Microsoft YaHei,sans-serif;max-width:860px;"
         "margin:24px auto;padding:0 16px}li{margin:5px 0}.meta{color:#666;font-size:.9em}</style>",
         "</head><body>", "<!-- NAV_START --><!-- NAV_END -->", "<h1>场次故事</h1>",
         f"<p class=\"meta\">三幕模板：开场（规模）→ 中场（读数）→ 结尾（观众）。"
         f"已生成 <b>{len(built)}</b> 场；待补 <b>{len(pend)}</b> 场。"
         "门槛：曲目 ≥10 且（现场素材 ≥1 或有反馈）；不达标的进待补，不生成空壳页。</p>",
         f"<h2>已生成（{len(built)} 场，按日期倒序）</h2><ul>"]
    for v in sorted(built, key=lambda x: x["date"], reverse=True):
        I.append(f'<li><a href="story-{v["slug"]}.html">{v["date"]} {html.escape(v["city"])}</a>'
                 f'<span class="meta">（{html.escape(v["tour"])}｜曲目 {v["songs_n"]}｜素材 {v["materials"]}'
                 + (f'｜反馈 {v["feedback"]}' if v["feedback"] else "") + '）</span></li>')
    I.append(f"</ul><h2>待补（{len(pend)} 场）</h2><ul>")
    for v in pend:
        miss = []
        if len(v["songs"]) < 10:
            miss.append("曲目 <10")
        if v["materials"] < 1:
            miss.append("无现场素材")
        if not v["feedback"]:
            miss.append("无观众反馈")
        I.append(f'<li>{v["date"]} {html.escape(v["city"])}<span class="meta">（缺：{"、".join(miss)}；'
                 '可补来源：B站分P / 现场录音 / 反馈抓取）</span></li>')
    I.append('</ul><p class="meta">另：<a href="story-hui-guangzhou-2026.html">六巡广州站单场复盘</a>（专题，保留原 URL）</p></body></html>')
    (SITE / "stories.html").write_text("\n".join(I), encoding="utf-8")
    print(f"[ok] 生成 {len(built)} 页｜待补 {len(pend)} 场")
    for v in pend[:6]:
        print("  待补", v["date"], v["city"], "曲目", len(v["songs"]), "素材", v["materials"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
