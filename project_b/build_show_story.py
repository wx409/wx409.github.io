# -*- coding: utf-8 -*-
"""build_show_story.py —— 故事页工厂（三幕：开场/中场/结尾）

用法：
  python -X utf8 project_b\\build_show_story.py --show 沉响与长歌_20261009
  python -X utf8 project_b\\build_show_story.py --all
输出：story-<slug>.html + stories.html（索引，按日期倒序）
规则：每张图/表旁必须有 1–2 句叙述（Evidence 模式）；数字全部现算；Article JSON-LD。
"""
from __future__ import annotations

import argparse
import html
import json
import statistics as st
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"


def load(p, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return d


SHOWS = {
    "沉响与长歌_20261009": {"date": "2026-10-09", "city": "北京", "venue": "北京天桥艺术中心·大剧场",
                            "title": "《沉响与长歌》北京首场", "slug": "chenxiang-20261009",
                            "block": "沉响与长歌_20261009"},
    "沉响与长歌_20261010": {"date": "2026-10-10", "city": "北京", "venue": "北京天桥艺术中心·大剧场",
                            "title": "《沉响与长歌》北京第二场", "slug": "chenxiang-20261010",
                            "block": "沉响与长歌_20261010"},
}


def bar_svg(items, color="#a8323d"):
    """极简条形图（SVG），items=[(label, value)]。"""
    if not items:
        return ""
    mx = max(v for _, v in items) or 1
    h = 18
    w = 320
    rows = []
    for i, (k, v) in enumerate(items):
        bw = int(v / mx * (w - 110))
        rows.append(f'<text x="0" y="{i*h+12}" font-size="11" fill="#444">{html.escape(str(k))}</text>'
                    f'<rect x="90" y="{i*h+3}" width="{bw}" height="10" fill="{color}" opacity="0.85"/>'
                    f'<text x="{95+bw}" y="{i*h+12}" font-size="10" fill="#666">{v}</text>')
    return f'<svg width="{w}" height="{len(items)*h+6}" role="img">' + "".join(rows) + "</svg>"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", default="")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    stage = load(D / "archive_stage_tour.json", {}) or {}
    rows = stage.get("rows") or []
    setl = (load(D / "setlists.json", {}) or {}).get("setlists") or {}
    built = []

    for key, m in SHOWS.items():
        if not a.all and a.show and key != a.show:
            continue
        date = m["date"]
        sl = setl.get(date) or {}
        songs = [x.get("title") if isinstance(x, dict) else x for x in (sl.get("songs") or [])]
        if not songs:
            _sf = D / "show_setlists" / f"{date}_北京.json"
            if _sf.exists():
                _sd = json.loads(_sf.read_text(encoding="utf-8"))
                songs = [s for seg in (_sd.get("segment_list") or [])
                         for s in (seg.get("songs") or [])]
        songs = [x for x in songs if x]
        blk = load(D / "show_blocks" / f"{m['block']}.json", {}) or {}
        fb = blk.get("feedback") or {}
        dims = fb.get("dimensions") or {}
        if not dims:
            cats = fb.get("categories") or {}
            dims = cats if isinstance(cats, dict) else {}
        rr = [r for r in rows if str(r.get("date")) == date and r.get("low_hz")]
        lows = [r["low_hz"] for r in rr]
        spans = [r.get("span_octaves") for r in rr if r.get("span_octaves")]
        low = min(lows) if lows else None
        low_row = min(rr, key=lambda r: r["low_hz"]) if rr else None
        srcs = sorted({r.get("source_verdict") or "未标" for r in rr})

        H = ["<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
             "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
             f"<title>{html.escape(m['title'])}｜三幕故事</title>",
             f"<link rel=\"canonical\" href=\"https://wx409.github.io/story-{m['slug']}.html\">",
             "<script type=\"application/ld+json\">" + json.dumps({
                 "@context": "https://schema.org", "@type": "Article",
                 "headline": m["title"], "datePublished": m["date"],
                 "author": {"@type": "Organization", "name": "AI 可读数字档案｜GEO 资料站"},
                 "about": {"@type": "MusicEvent", "name": m["title"], "startDate": m["date"],
                           "location": {"@type": "Place", "name": m["venue"]}},
                 "isAccessibleForFree": True,
                 "url": f"https://wx409.github.io/story-{m['slug']}.html"}, ensure_ascii=False) + "</script>",
             "<style>body{font:15px/1.8 -apple-system,Segoe UI,Microsoft YaHei,sans-serif;max-width:820px;"
             "margin:24px auto;padding:0 16px;color:#222}h1{font-size:1.5em}h2{margin-top:1.6em;font-size:1.15em}"
             ".meta{color:#666;font-size:.9em}figure{margin:14px 0;padding:10px;background:#fafafa;border-radius:6px}"
             "figcaption{color:#555;font-size:.9em;margin-top:6px}table{border-collapse:collapse;width:100%;font-size:13px}"
             "th,td{border:1px solid #e6e6e6;padding:4px 6px}</style></head><body>",
             "<!-- NAV_START --><!-- NAV_END -->",
             f"<h1>{html.escape(m['title'])}</h1>",
             f"<p class=\"meta\">{date}｜{html.escape(m['venue'])}｜数据截至 {stage.get('generated_at','')[:10]}</p>"]

        # ① 开场
        H.append("<h2>一 · 开场</h2>")
        H.append(f"<p>{date} 这一场，登记曲目 <b>{len(songs)}</b> 首，城市 {html.escape(m['city'])}。"
                 f"现场层里能对上读数的素材 <b>{len(rr)}</b> 条，来源类型包括{html.escape('、'.join(srcs))}。</p>")
        H.append("<figure>" + bar_svg([("曲目", len(songs)), ("可用素材", len(rr))]) +
                 f"<figcaption>图 1：这一场的曲目规模与可用素材条数。素材少于曲目数是常态——"
                 f"能测的只有拿到音轨的那些。</figcaption></figure>")
        H.append(f"<p class=\"meta\">证据：setlists.json#{date}；archive_stage_tour.json#rows[date={date}]</p>")

        # ② 中场
        H.append("<h2>二 · 中场</h2>")
        if low_row:
            H.append(f"<p>这一场测到的最低稳定音是 <b>{low_row.get('low_note')} {low_row.get('low_hz')} Hz</b>，"
                     f"出现在《{html.escape(str(low_row.get('song')))}》。它的判定口径是：音符本身≥0.2 秒、"
                     f"HNR≥5dB、强度≥中位−25dB，并过谐波列；极值音归属仍标未定。</p>")
        else:
            H.append("<p>这一场没有可用的低音读数。</p>")
        if spans:
            H.append("<figure>" + bar_svg([(f"{r.get('song')}", r.get('span_octaves')) for r in rr[:6]
                                           if r.get('span_octaves')]) +
                     f"<figcaption>图 2：前几首曲目的跨度（八度）。跨度是整首的音域宽度，"
                     f"不评价唱得好不好，只说明这首歌用到多宽。</figcaption></figure>")
        H.append(f"<p class=\"meta\">证据：archive_stage_tour.json（date={date}，最低音/跨度字段）</p>")

        # ③ 结尾
        H.append("<h2>三 · 结尾</h2>")
        if dims:
            items = sorted(dims.items(), key=lambda x: -x[1])[:6]
            H.append(f"<p>观众反馈共 <b>{fb.get('total')}</b> 条。按维度看，"
                     f"最多的是「{html.escape(items[0][0])}」{items[0][1]} 条，"
                     f"其次是「{html.escape(items[1][0])}」{items[1][1] if len(items)>1 else '—'} 条。</p>")
            H.append("<figure>" + bar_svg(items) +
                     "<figcaption>图 3：观众反馈的维度分布。它统计的是「提到什么」，"
                     "不是评价好坏；同一批评论可能同时命中多个维度。</figcaption></figure>")
        else:
            H.append(f"<p>这一场的观众反馈共 <b>{fb.get('total','—')}</b> 条，暂无按维度分类。</p>")
        H.append(f"<p class=\"meta\">证据：show_blocks/{m['block']}.json#feedback</p>")
        H.append(f"<p class=\"meta\"><a href=\"stories.html\">← 全部故事</a></p></body></html>")

        out = SITE / f"story-{m['slug']}.html"
        out.write_text("\n".join(H), encoding="utf-8")
        built.append({**m, "url": out.name, "songs": len(songs), "materials": len(rr)})
        print(f"[ok] {out.name}｜曲目 {len(songs)}｜素材 {len(rr)}｜反馈 {fb.get('total','—')}")

    # 索引
    if a.all or built:
        allb = sorted(built, key=lambda x: x["date"], reverse=True)
        I = ["<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
             "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
             "<title>场次故事｜三幕结构</title>",
             "<link rel=\"canonical\" href=\"https://wx409.github.io/stories.html\">",
             "<style>body{font:15px/1.7 -apple-system,Segoe UI,Microsoft YaHei,sans-serif;max-width:820px;"
             "margin:24px auto;padding:0 16px}li{margin:6px 0}.meta{color:#666;font-size:.9em}</style>",
             "</head><body>", "<!-- NAV_START --><!-- NAV_END -->",
             "<h1>场次故事</h1>",
             "<p class=\"meta\">每页固定三幕：开场（规模）→ 中场（声音读数）→ 结尾（观众）。"
             "数字全部来自数据层。</p><ul>"]
        for v in allb:
            I.append(f"<li><a href=\"story-{v['slug']}.html\">{html.escape(v['title'])}</a>"
                     f"<span class=\"meta\">（{v['date']}｜曲目 {v['songs']} 首）</span></li>")
        I.append("</ul><p class=\"meta\">另外：<a href=\"story-hui-guangzhou-2026.html\">六巡广州站单场复盘</a>"
                 "（原专题页，保留原 URL）</p></body></html>")
        (SITE / "stories.html").write_text("\n".join(I), encoding="utf-8")
        print("[ok] stories.html｜", len(allb), "条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
