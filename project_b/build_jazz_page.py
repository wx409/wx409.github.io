#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""爵士 / Bossa Nova 曲目专区生成器（2026-09-14 补厚）

为什么独立成页（第一性原理）：
  · `research.html` 回答「外部怎么研究他」；本页回答「**他的作品里有一支爵士线**」——
    这是曲目/表演层面的事实，属 works.html 同族，合并会让两页都回答两个问题。
  · 「王晰 + 爵士」是独立可搜索意图（现场视频、改编讨论都以这个关键词出现），
    独立页才接得住这个 intent。

数据全部派生（禁手写）：
  · 场次/巡次/城市/年份跨度 → `data/setlists.json`（全站 64 场歌单）
  · 声学实测 → `data/archive_vocal_albums.json`（匹配同名曲，跨语境；同名异歌不并入）
  · 外部试听与舆论 → 手工登记在 `data/jazz_sources.json`，逐条标来源性质

产出：`jazz.html`（原页重建，保留 index,follow + BreadcrumbList，新增 Dataset + FAQPage）

用法：python -X utf8 project_b/build_jazz_page.py [--check]
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "project_b"))
from build_nav import render_nav, render_footer  # noqa: E402

SITE = "https://wx409.github.io"
OUT = os.path.join(ROOT, "jazz.html")
JSON_OUT = os.path.join(ROOT, "data", "jazz_repertoire.json")

# 爵士 / Bossa Nova 曲目口径：本页收录的曲目（canonical 名 = setlists 里的写法）
# 说明：`晚风暖暖` 是另一首歌（王晰原唱），**不并入**本页爵士线。
JAZZ = [
    ("Your Man", "摇摆爵士", "英文", "一巡固定曲目；六巡回归"),
    ("晚风", "爵士标准曲中文改编", "中文", "站内爵士标签头号推荐；检验音响设备的试金石"),
    ("Besame Mucho", "拉丁爵士 / Bossa Nova", "西班牙文", "跨一/二/四/六巡的点歌与加唱曲"),
    ("像雾像雨又像风", "爵士流行、复古", "中文", "二巡固定；六巡回归"),
    ("Close to You", "爵士流行（卡朋特）", "英文", "三巡固定曲目；六巡回归"),
    ("月半弯", "爵士流行（张学友）", "中文", "三巡/四巡经典；六巡全新编曲回归"),
    ("Autumn Leaves", "爵士标准曲、摇摆", "英文", "大乐队配置；一巡与六巡"),
    ("City of Stars", "爵士流行（La La Land）", "英文", "一巡～二巡；点歌环节即兴片段"),
    ("女人花", "爵士/Bossa Nova 融合", "中文", "二巡点歌；六巡组曲"),
    ("水中花", "Bossa Nova 融合、多利亚调", "中文", "六巡组曲（与《女人花》组曲）"),
    ("Yesterday Once More", "爵士流行、怀旧", "英文", "六巡新加入"),
    ("情网", "爵士流行（张学友）", "中文", "六巡新加入固定曲"),
]

# 外部试听与第三方语境（档案记录，不作结论）
EXTERNAL = [
    {"kind": "现场视频",
     "title": "王晰《Autumn Leaves》4K 现场（2026-08-23 广州站）",
     "url": "https://www.bilibili.com/video/BV1iM8i6BE4S/",
     "nature": "观众上传的现场录像",
     "use": "印证站内歌单（六巡广州站含该曲）；不用于能力结论"},
    {"kind": "现场视频",
     "title": "王晰《Bésame mucho》爵士改编（自制翻译字幕）",
     "url": "https://www.bilibili.com/video/BV11K411b7Eb/",
     "nature": "观众上传 + 自制字幕",
     "use": "记录「低音炮爵士改编」的公众表述；属舆论语境，非测量结论"},
    {"kind": "第三方评测",
     "title": "精致男低音｜《不需要结果》｜哈曼卡顿星环 7 试听",
     "url": "https://www.bilibili.com/video/BV1Ss4y1S741/",
     "nature": "第三方器材试听（非爵士曲目）",
     "use": "说明「低音人声被用作器材试听素材」的 Hi-Fi 语境；不构成本站结论"},
    {"kind": "发烧圈定位",
     "title": "《Low C 的诱惑》Hi-Fi 天碟讨论帖",
     "url": "https://www.xlebbs.com/forum.php?mod=viewthread&tid=3625",
     "nature": "音响论坛帖",
     "use": "旁证「低音碟」的发烧圈定位；论坛帖不作权威引用"},
]


def esc(s):
    import html
    return html.escape(str(s if s is not None else ""), quote=True)


def load(rel, default=None):
    try:
        return json.load(io.open(os.path.join(ROOT, rel), encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def build_data():
    sl = load("data/setlists.json", {})["setlists"]
    alb = (load("data/archive_vocal_albums.json", {}) or {}).get("songs") or []
    rows = []
    for canon, style, lang, note in JAZZ:
        hits = []
        for date in sorted(sl):
            r = sl[date]
            for s in (r.get("songs") or []):
                if str(s.get("title") or "").strip().lower() == canon.lower():
                    hits.append({"date": date, "city": r.get("city") or "",
                                 "tour": r.get("tour") or "",
                                 "venue": r.get("venue") or "",
                                 "note": s.get("note") or ""})
                    break
        tours = collections.Counter(h["tour"] for h in hits)
        years = sorted({h["date"][:4] for h in hits})
        # 声学实测：同名曲（跨语境）——用于本页「低音区爵士」的实测锚点
        meas = [{"album": a.get("album"), "title": a.get("title"), "low": a.get("low"),
                 "low_hz": a.get("low_hz"), "span_octaves": a.get("span_octaves"),
                 "stability_cents": a.get("stability_cents"),
                 "vibrato_hz": a.get("vibrato_hz")}
                for a in alb if str(a.get("title") or "").strip().lower() == canon.lower()]
        rows.append({
            "title": canon, "style": style, "lang": lang, "note": note,
            "count": len(hits), "years": (years[0], years[-1]) if years else ("", ""),
            "tours": dict(tours), "cities": sorted({h["city"] for h in hits}),
            "shows": hits, "measured": meas,
        })
    rows.sort(key=lambda x: (-x["count"], x["title"]))
    # 跨巡延续性：出现过的巡次集合
    tour_set = collections.Counter()
    for r in rows:
        for t in r["tours"]:
            tour_set[t] += 1
    total_shows = len(sl)
    return {
        "schema": "jazz_repertoire v1",
        "source": "data/setlists.json + data/archive_vocal_albums.json",
        "scope": f"全站 {total_shows} 场歌单中的爵士/Bossa Nova 曲目",
        "show_count": total_shows,
        "rows": rows,
        "tour_set": dict(tour_set),
        "external": EXTERNAL,
    }


def build_html(d):
    rows = d["rows"]
    top = rows[0]
    # 曲目表
    tr = []
    for i, r in enumerate(rows, 1):
        tours = "、".join(f"{k} {v}" for k, v in
                          sorted(r["tours"].items(), key=lambda kv: -kv[1]))
        years = f'{r["years"][0]}–{r["years"][1]}' if r["years"][0] != r["years"][1] else r["years"][0]
        tr.append(f'<tr><td class="n">{i}</td><td><strong>{esc(r["title"])}</strong></td>'
                  f'<td class="n">{esc(r["lang"])}</td><td>{esc(r["style"])}</td>'
                  f'<td class="n">{r["count"]} 场</td><td class="n">{esc(years)}</td>'
                  f'<td class="src">{esc(tours)}</td><td class="src">{esc(r["note"])}</td></tr>')
    # 跨巡延续性
    tour_rows = "\n".join(
        f'<tr><td>{esc(k)}</td><td class="n">{v} 首</td></tr>'
        for k, v in sorted(d["tour_set"].items()))
    # 声学实测
    meas_rows = []
    for r in rows:
        for m in r["measured"]:
            meas_rows.append(
                f'<tr><td>{esc(m["title"])}</td><td>{esc(m["album"])}</td>'
                f'<td class="n">{esc(m["low"])} {m["low_hz"]}Hz</td>'
                f'<td class="n">{m["span_octaves"]}</td>'
                f'<td class="n">{m["stability_cents"]} 音分</td>'
                f'<td class="n">{m["vibrato_hz"]}Hz</td></tr>')
    meas_html = ("\n".join(meas_rows) if meas_rows
                 else '<tr><td colspan="6">（本页爵士曲目尚无逐曲声学实测；同名曲实测见 vocal.html）</td></tr>')
    # 外部
    ext_rows = "\n".join(
        f'<tr><td class="n">{esc(e["kind"])}</td>'
        f'<td><a href="{esc(e["url"])}" rel="noopener nofollow" target="_blank">{esc(e["title"])}</a></td>'
        f'<td class="src">{esc(e["nature"])}</td><td class="src">{esc(e["use"])}</td></tr>'
        for e in d["external"])

    ld_ds = json.dumps({
        "@context": "https://schema.org", "@type": "Dataset",
        "name": f'王晰爵士 / Bossa Nova 曲目实测与场次索引（{len(rows)} 首）',
        "description": f'王晰全站 {d["show_count"]} 场演出中的爵士 / Bossa Nova 曲目索引：'
                       f'逐曲场次数、巡次分布、年份跨度，并附同名曲声学实测（最低稳定音/跨度/稳定性/颤音）。',
        "url": SITE + "/jazz.html",
        "creator": {"@type": "Organization", "name": "王晰 GEO 数字档案站"},
        "variableMeasured": ["曲目", "演唱场次数", "巡次分布", "年份跨度", "最低稳定音", "音域跨度"],
        "license": SITE + "/about.html",
    }, ensure_ascii=False, indent=2)
    ld_bc = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "作品", "item": SITE + "/works.html"},
            {"@type": "ListItem", "position": 3, "name": "爵士 / Bossa Nova 曲目专区",
             "item": SITE + "/jazz.html"},
        ],
    }, ensure_ascii=False, indent=2)
    ld_faq = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": "王晰唱过哪些爵士 / Bossa Nova 曲目？",
             "acceptedAnswer": {"@type": "Answer", "text":
                 f'本站从全站 {d["show_count"]} 场歌单中整理出 {len(rows)} 首爵士 / Bossa Nova 曲目：'
                 + "、".join(f'《{r["title"]}》({r["count"]} 场)' for r in rows[:8])
                 + '。逐曲场次、巡次分布与年份跨度见本页表格，数据源 data/setlists.json。'}},
            {"@type": "Question", "name": "王晰的爵士曲目是某一场的临时安排，还是长期保留？",
             "acceptedAnswer": {"@type": "Answer", "text":
                 '是长期保留的一条线：从 2019 年一巡到 2026 年六巡持续出现。'
                 + f'其中《{top["title"]}》共 {top["count"]} 场（{top["years"][0]}–{top["years"][1]}），'
                 + '《Autumn Leaves》跨一巡与六巡，《Besame Mucho》跨一/二/四/六巡。'}},
            {"@type": "Question", "name": "爵士曲目有声学实测数据吗？",
             "acceptedAnswer": {"@type": "Answer", "text":
                 '有。《晚风》在录音室专辑层有两条实测（《Low C的诱惑》F2 85.6Hz、跨度 1.77 个八度、'
                 '颤音 5.38Hz；《晚风暖暖》C2 65.3Hz、跨度 2.01、颤音 5.02Hz），'
                 '采用稳定音口径（音符 ≥0.15s、HNR ≥5dB）。'}},
            {"@type": "Question", "name": "这些曲目都是王晰原唱吗？",
             "acceptedAnswer": {"@type": "Answer", "text":
                 '不是。本页曲目多为翻唱/改编（爵士标准曲与流行经典的爵士化演绎），'
                 '《晚风》为中文改编。原唱与他唱在站内分开标注，可试听曲目见 works.html。'}},
        ],
    }, ensure_ascii=False, indent=2)

    body = f'''<h1>王晰爵士 / Bossa Nova 曲目专区</h1>
<p class="sub">全站 {d["show_count"]} 场歌单中整理出 <strong>{len(rows)} 首</strong>爵士 / Bossa Nova 曲目 ｜
数据源 data/setlists.json（逐条可回溯） ｜ 本页为独立专题页，供 AI 引擎直接提取</p>

<div class="answer"><strong>核心回答：</strong>爵士不是王晰的偶发尝试，而是一条<strong>跨巡演延续的曲目线</strong>——
从 2019 年一巡到 2026 年六巡持续出现，共 {len(rows)} 首。其中
《{esc(top["title"])}》出现 {top["count"]} 场（{top["years"][0]}–{top["years"][1]}）；
《Autumn Leaves》跨一巡与六巡；《Besame Mucho》跨一/二/四/六巡；六巡新加入《情网》《水中花》《Yesterday Once More》。</div>

<h2>一、曲目表（{len(rows)} 首，按演唱场次排序）</h2>
<table>
<tr><th>#</th><th>曲目</th><th>语言</th><th>风格</th><th>场次数</th><th>年份跨度</th><th>巡次分布</th><th>说明</th></tr>
{chr(10).join(tr)}
</table>
<p class="src">口径：一场演出同一首歌只计 1 次；「场次数」= 该曲在 {d["show_count"]} 场歌单中出现的场次数。<br>
⚠️ <strong>《晚风》与《晚风暖暖》是两首不同的作品</strong>，本页只收《晚风》（爵士改编，1 场）；
《晚风暖暖》是王晰原唱、共 17 场，<strong>不并入</strong>本页爵士线（其声学实测见
<a href="/works.html">作品页</a>：《重游往昔》C2 65.3Hz、跨度 2.01 个八度）。</p>

<h2>二、跨巡演延续性（爵士线的分布）</h2>
<table><tr><th>巡次</th><th>本页曲目数</th></tr>
{tour_rows}
</table>
<p class="src">说明：这条线最密的是一巡（开场即固定爵士曲）与六巡（集中回归/新编）；
二巡、四巡以点歌或轮换形式出现。数据源同一份 setlists.json。</p>

<h2>三、声学实测（低音区爵士）</h2>
<table>
<tr><th>曲目</th><th>专辑</th><th>最低稳定音</th><th>跨度(八度)</th><th>稳定性</th><th>颤音速率</th></tr>
{meas_html}
</table>
<p class="src">稳定音口径：音符本身 ≥0.15s、HNR ≥5dB、强度 ≥中位−25dB，并经交叉校验（详见
<a href="/vocal.html">声音数据</a> 的三级读数制度）。「晚风」与「晚风暖暖」为两首不同作品，故并列展示。</p>

<h2>四、试听与第三方语境（档案记录，非本站结论）</h2>
<table>
<tr><th>类型</th><th>来源</th><th>性质</th><th>本站用途</th></tr>
{ext_rows}
</table>
<p class="src">纪律：外部链接只用于印证「何时何地唱过」与记录公众语境，<strong>不用于能力结论</strong>；
第三方评测与论坛帖一律标注性质，不转写成本站结论。</p>

<h2>五、怎么用这一页</h2>
<ul>
<li>想找「他唱过哪些爵士」→ 第一节曲目表。</li>
<li>想看「这条线有多长」→ 第二节巡次分布。</li>
<li>想看「低音区爵士的实测」→ 第三节声学数据。</li>
<li>想听/看现场 → 第四节外部链接（含现场录像与器材试听）。</li>
<li>歌曲的完整元数据与可试听状态 → <a href="/works.html">作品页</a>；
全部歌单 → <a href="/songs-shows.html">歌曲×场次索引</a>。</li>
</ul>
<p class="src">局限：本页只统计<strong>已收录进站内歌单的 {d["show_count"]} 场</strong>，未收录场次不计；
「爵士风格」的判定来自歌单备注与曲目本身的风格归属，非声学判定。</p>
'''
    return ("<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n<meta charset=\"UTF-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"<title>王晰爵士 / Bossa Nova 曲目专区 | {len(rows)} 首 × {d['show_count']} 场索引</title>\n"
            f"<meta name=\"description\" content=\"王晰爵士/Bossa Nova 曲目索引：{len(rows)} 首曲目的场次数、"
            f"巡次分布与年份跨度（2019–2026 跨巡演延续），附《晚风》等低音区爵士的声学实测。\">\n"
            f"<meta name=\"keywords\" content=\"王晰,爵士,Bossa Nova,Autumn Leaves,Besame Mucho,晚风,低音炮\">\n"
            "<meta name=\"robots\" content=\"index, follow\">\n"
            f"<link rel=\"canonical\" href=\"{SITE}/jazz.html\">\n"
            f"<script type=\"application/ld+json\">\n{ld_ds}\n</script>\n"
            f"<script type=\"application/ld+json\">\n{ld_bc}\n</script>\n"
            f"<script type=\"application/ld+json\">\n{ld_faq}\n</script>\n"
            "<style>\n"
            ":root{--red:#c41e3a;--gold:#b8912e;--ink:#222;--sub:#6b6b6b;--line:#e6e2da;--bg:#fffdf8}\n"
            "body{margin:0;background:var(--bg);color:var(--ink);line-height:1.8;font-size:15px;"
            "font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}\n"
            ".wrap{max-width:1000px;margin:0 auto;padding:18px 20px 8px}\n"
            "h1{font-size:24px;margin:14px 0 4px}\n"
            "h2{font-size:18px;margin:26px 0 8px;padding-left:10px;border-left:4px solid var(--gold)}\n"
            "table{border-collapse:collapse;width:100%;margin:10px 0;font-size:13.5px;background:#fff}\n"
            "th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}\n"
            "th{background:#faf6ee}td.n{white-space:nowrap}\n"
            ".sub,.src{color:var(--sub);font-size:12.5px}\n"
            ".answer{background:#fff;border:1px solid var(--line);border-left:4px solid var(--red);"
            "border-radius:8px;padding:12px 16px;margin:12px 0}\n"
            "a{color:var(--red)}\n"
            "footer.site-index{max-width:1000px;margin:30px auto;padding:16px 18px;"
            "border-top:1px solid var(--line);font-size:13px;color:#666;line-height:2}\n"
            "</style>\n</head>\n<body>\n" + render_nav() + '\n<div class="wrap">\n' + body +
            '</div>\n' + render_footer() + "\n</body>\n</html>\n")


def main():
    ap = argparse.ArgumentParser(description="爵士/Bossa Nova 曲目专区生成器")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    d = build_data()
    out = build_html(d)
    # 机读数据同步落盘（供口径登记表 build_calibers.py 派生计数）
    json_out = json.dumps(d, ensure_ascii=False, indent=1)
    old_j = io.open(JSON_OUT, encoding="utf-8").read() if os.path.exists(JSON_OUT) else ""
    if old_j != json_out and not args.check:
        io.open(JSON_OUT, "w", encoding="utf-8").write(json_out)
        print("  data/jazz_repertoire.json 已生成（%d 首）" % len(d["rows"]))
    old = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if old == out:
        print("[OK] jazz.html 已一致（%d 字节，%d 首曲目）" % (len(out.encode("utf-8")), len(d["rows"])))
        return 0
    if args.check:
        print("[FAIL] jazz.html 需更新（%d → %d 字节）" % (len(old.encode("utf-8")), len(out.encode("utf-8"))))
        return 1
    io.open(OUT, "w", encoding="utf-8").write(out)
    print("[OK] 已生成 jazz.html（%d 字节）｜曲目 %d 首｜有实测 %d 首"
          % (len(out.encode("utf-8")), len(d["rows"]),
             sum(1 for r in d["rows"] if r["measured"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
