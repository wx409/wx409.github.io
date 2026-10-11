# -*- coding: utf-8 -*-
"""分享作战页生成器 → share.html（五区）+ 数据种子。

五区：① 卡片库 ② 句式库 ③ 平台模板 ④ 使用纪律 ⑤ 作战地图
另：`share.html?card=<id>` → 单卡竖屏截图视图。
数据种子（不存在时创建，存在则保留用户手填内容）：
  data/share/keywords.json     三层关键词（brand 初始化=17 问答 + TOP10 歌名；category/scene 留空槽位）
  data/share/templates.json    小红书五件套 / 抖音听觉断点 / 官方音源铁规矩 / 使用纪律六条
  data/share/single_songs.json TOP10 单曲（主排序 count 降序 → 次排序覆盖巡次数降序）
  data/share/daily_brief.json  速报卡 + 品类词槽位
用法：python -X utf8 project_b\\build_share_page.py
"""
from __future__ import annotations

import io
import json
import sys
from datetime import date
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
SH = D / "share"
CARDS = SH / "cards"
RENDER = SH / "rendered"
OUT = SITE / "share.html"
TODAY = date.today().isoformat()

DISCIPLINE = [
    "① **数字只引口径**：任何数字必须带 calibers id 与范围；同一页不混用不同范围。",
    "② **稳定音 vs 触达音**：主数字只用过门槛的稳定音；触达音/待核一律进 caliber-lock 块（三不许）。",
    "③ **官方音源铁规矩**：挂官方音源才计入歌曲热度；不得引导搬运官摄。",
    "④ **音视频不入站**：本站不提供、不嵌入、不转存任何音视频；抖音「片段位」只是纯文字占位，"
    "发布者自备素材。",
    "⑤ **不夸大**：禁用绝对化排行式表述（无权威论断支撑的那一类）；具体禁用词清单与替代写法见 `data/calibers.md` 用语规范。另：「两个半八度」为口语、不准确，不得引用。",
    "⑥ **经验性认知标注**：本页为本站基于公开材料的经验性整理，**非官方发布**；"
    "引用前请核对 `data/calibers.md`。",
]

TEMPLATES = {
    "小红书五件套": {
        "标题": "不超过 20 字，含一个数字或反差（例：「八年只差 0.02Hz」）",
        "封面文案": "一句钩子，竖屏大字，不超过 12 字",
        "正文": "三段：现象 → 数据（带口径） → 一句人话总结",
        "标签": "#王晰 + #低音炮 + 一个内容标签（如 #声乐实测）",
        "互动引导": "以「想听哪首？」「你从哪首认识他？」收尾，不导流、不带货",
    },
    "抖音听觉断点": {
        "片段位（纯文字占位）": "写清「第几秒到第几秒听什么」，**不含音视频文件/链接/嵌入**",
        "口播": "一句数字 + 一句感受，不超过 15 秒",
        "must_note": "发布者自备素材，本站不提供音视频；请使用官方音源，勿搬运官摄",
    },
    "官方音源铁规矩": "只有挂官方音源的二创才计入「歌曲热度」统计；搬运官摄的行为本站不背书、不引导。",
    "页首总标注": "经验性认知（非官方）——本站为个人数字档案，非官方发布渠道。",
}


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def esc(s):
    return (str(s if s is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def seed_data():
    SH.mkdir(parents=True, exist_ok=True)
    qa = load(D / "qa_bank.json").get("items", [])
    cards = [load(f) for f in sorted(CARDS.glob("card_*.json"))]
    # ── keywords.json：brand 初始化；category/scene 留空槽位 ──
    kw_path = SH / "keywords.json"
    if not kw_path.exists():
        ssi = load(D / "songs_shows_index.json")
        top10 = sorted(ssi.get("songs", []), key=lambda x: (-x.get("count", 0),
                                                           -len({s.get("tour") for s in x.get("shows", [])})))[:10]
        brand = ([x.get("q") or x.get("question") for x in qa][:17]
                 + [s.get("title") for s in top10])
        kw_path.write_text(json.dumps({
            "schema": 1, "generated_at": TODAY,
            "note": "三层挖词表。brand 层已由脚本初始化（17 问答 + TOP10 歌名）；"
                    "**category / scene 两层留空槽位，待人工填写**（每层分别为 30 / 50 词）。",
            "layers": {
                "brand": {"target": 20, "filled_by": "脚本（qa_bank + songs_shows_index）", "words": brand},
                "category": {"target": 30, "filled_by": "人工", "words": [],
                             "howto": "品类词：声乐/低音/男低音/颤音/音域/舞台/巡演/现场/合唱/音乐剧…"},
                "scene": {"target": 50, "filled_by": "人工", "words": [],
                          "howto": "场景词：通勤/深夜/助眠/健身/下雨天/加班/开车/写作业/咖啡馆…"},
            },
            "dig_guide": ["① 先用 brand 层跑搜索，看哪些词有量；② 再把高量词拆成品类/场景两层；"
                          "③ 每 2 周复核一次词表热度，淘汰零量词。"]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print("  种子：data/share/keywords.json（brand 已填，category/scene 留空槽位）")
    if not (SH / "templates.json").exists():
        (SH / "templates.json").write_text(json.dumps(
            {"schema": 1, "generated_at": TODAY, "templates": TEMPLATES,
             "discipline": DISCIPLINE}, ensure_ascii=False, indent=1), encoding="utf-8")
    else:
        # 纪律文案属代码常量（会随用语规范更新）→ 每次刷新，避免旧文案残留禁用词
        _cur = load(SH / "templates.json")
        _cur["discipline"] = DISCIPLINE
        _cur["generated_at"] = TODAY
        (SH / "templates.json").write_text(json.dumps(_cur, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  种子：data/share/templates.json")
    # ── single_songs.json：TOP10（主排序 count → 次排序覆盖巡次数）──
    ss_path = SH / "single_songs.json"
    if not ss_path.exists():
        ssi = load(D / "songs_shows_index.json")

        def _names(obj, keys=("name", "title", "song")):
            out = set()
            for it in (obj or []):
                if not isinstance(it, dict):
                    continue
                for k in keys:
                    v = it.get(k)
                    if v:
                        out.add(str(v).strip())
                        break
            return out

        vocal = (_names(load(D / "archive_vocal_albums.json").get("songs", []))
                 | _names(load(D / "archive_vocal.json").get("songs", [])))
        arch = _names(load(D / "song_archive.json").get("songs", []))
        rows = []
        for s in ssi.get("songs", []):
            if not s.get("shows"):
                continue
            tours = sorted({x.get("tour") for x in s["shows"] if x.get("tour")})
            measured = s.get("title") in vocal
            in_arch = s.get("title") in arch
            if not (measured or in_arch):
                continue
            rows.append({"title": s.get("title"), "count": s.get("count"),
                         "tours": len(tours), "tour_list": tours,
                         "gate": "实测" if measured else "作品百科收录"})
        rows.sort(key=lambda x: (-(x["count"] or 0), -x["tours"]))
        ss_path.write_text(json.dumps({
            "schema": 1, "generated_at": TODAY,
            "rule": "主排序 songs_shows_index.count 降序 → 次排序「覆盖巡次数」降序；"
                    "门槛＝任一 archive_*.json 有实测 或 被作品百科收录；自有/翻唱均可",
            "count_rule_note": "覆盖巡次数 = len({sh['tour'] for sh in shows})（每首歌 shows[] 每条自带 tour）",
            "top10": rows[:10], "all_count": len(rows)},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  种子：data/share/single_songs.json（候选 {len(rows)} 首 → TOP10）")
    # ── daily_brief.json ──
    db_path = SH / "daily_brief.json"
    if not db_path.exists():
        db_path.write_text(json.dumps({
            "schema": 1, "generated_at": TODAY,
            "brief_card": {"title": "今日速报（模板）",
                           "fields": ["指数覆盖天数", "最近一次更新", "本期新上榜", "一句结论"],
                           "note": "数值一律从 dashboard/dashboard_data.json 取，禁止手写"},
            "category_slots": {"target": 30, "filled_by": "人工", "words": []},
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  种子：data/share/daily_brief.json")
    return cards


def main():
    cards = seed_data()
    kw = load(SH / "keywords.json")
    pool = load(SH / "song_pool.json")
    tpl = load(SH / "templates.json")
    singles = load(SH / "single_songs.json")
    sel = ""
    # ?card=<id> 竖屏视图：只渲染一张卡（截图用）
    body = "".join((RENDER / f"card_{c['id']}.html").read_text(encoding="utf-8") for c in cards)
    rows = "".join(
        f"<tr><td>{i+1}</td><td>{esc(s['title'])}</td><td>{s['count']}</td><td>{s['tours']}</td>"
        f"<td>{esc('、'.join(s['tour_list'][:4]))}</td><td>{esc(s['gate'])}</td></tr>"
        for i, s in enumerate(singles.get("top10", [])))
    kw_rows = "".join(
        f"<tr><td>{esc(k)}</td><td>{v.get('target')}</td><td>{len(v.get('words') or [])}</td>"
        f"<td>{esc(v.get('filled_by'))}</td></tr>" for k, v in (kw.get("layers") or {}).items())
    pool_html = "".join(
        f"<div class='card'><h3>{esc(x['song'])}<span class='pill'>{esc(x['by'])}</span></h3>"
        f"<p>{esc(x['conclusion'])}（有记录演唱 {x['confirmed_sing_count']} 次）</p>"
        + "<ul>" + "".join(f"<li>{esc(e['when'])}｜{esc(e['kind'])}</li>" for e in x["evidence"]) + "</ul>"
        + f"<p class='meta'>来源：{esc(x['source'])}</p></div>"
        for x in (pool.get("items") or [])) or "<p class='meta'>（暂无）</p>"
    tpl_html = "".join(
        f"<h4>{esc(k)}</h4><ul>" + "".join(f"<li><b>{esc(kk)}</b>：{esc(vv)}</li>" for kk, vv in v.items())
        + "</ul>" for k, v in (tpl.get("templates") or {}).items() if isinstance(v, dict))
    disc = "".join(f"<li>{d}</li>" for d in (tpl.get("discipline") or DISCIPLINE))
    js = json.dumps({"@context": "https://schema.org", "@type": "CollectionPage",
                     "name": "分享作战室", "url": "https://wx409.github.io/share.html",
                     "isPartOf": {"@type": "WebSite", "name": "王晰数字图书馆",
                                  "url": "https://wx409.github.io/"},
                     "hasPart": [{"@type": "CreativeWork", "name": c["title"],
                                  "about": c["subtitle"]} for c in cards]}, ensure_ascii=False, indent=1)
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>分享作战室｜6 张卡 + 平台模板 + 使用纪律｜王晰数字图书馆</title>
<meta name="description" content="王晰数字图书馆分享作战室：6 张专题卡（颤音指纹/低音下限/低音动态/长声/情境自觉/巡演规模）、单曲 TOP10、三层挖词表、小红书与抖音模板、使用纪律六条。经验性认知（非官方）。">
<link rel="canonical" href="https://wx409.github.io/share.html">
<script type="application/ld+json">{js}</script>
<style>
body{{max-width:960px;margin:0 auto;padding:18px;font:15px/1.75 -apple-system,"Microsoft YaHei",sans-serif;color:#2b2320;background:#faf6ef}}
h2{{margin:30px 0 8px;border-bottom:2px solid #e6d9c4;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%;font-size:13.5px}} td,th{{border:1px solid #e6d9c4;padding:5px 7px;text-align:left}}
.card{{background:#fff;border:1px solid #eadfcc;border-radius:10px;padding:12px 14px;margin:12px 0}}
.pill{{font-size:11px;background:#eee3d3;color:#7a6a55;border-radius:10px;padding:2px 8px;margin-left:8px}}
.sub{{color:#8a7f6d;margin:2px 0 8px}} .foot{{color:#8a7f6d;font-size:12.5px;border-top:1px dashed #e2d8c7;padding-top:6px}}
.lock{{background:#fff4f0;border-left:3px solid #d98b6a;padding:8px 12px;margin:10px 0;font-size:13.5px}}
.plat{{background:#f3f6ef;border-left:3px solid #8aa87a;padding:8px 12px;margin:10px 0;font-size:13.5px}}
.meta{{color:#8a7f6d;font-size:12.5px}} .big{{font-size:34px;font-weight:700}}
.warn{{background:#fffbe8;border-left:3px solid #d9c46a;padding:8px 12px}}
</style></head><body>
<!-- NAV_START --><!-- NAV_END -->
<h1>🧰 分享作战室</h1>
<p class="meta">生成 {TODAY}｜<b>经验性认知（非官方）</b>：本页为本站基于公开材料的经验性整理，非官方发布｜
数字一律派生自 <code>data/</code>，口径见 <code>data/calibers.md</code></p>
<div class="warn">本页<strong>不进主导航</strong>，仅在 <a href="community.html">社群页</a> 强链；仅供站主自用与授权合作者参考。</div>

<h2>① 卡片库（6 张）</h2>
<p class="meta">每卡两视图：本页为阅读视图；竖屏截图视图 = <code>share.html?card=&lt;id&gt;</code>（例：?card=vibrato）</p>
{body}

<h2>② 句式库 · 单曲 TOP10</h2>
<p class="meta">{esc(singles.get('rule'))}｜{esc(singles.get('count_rule_note'))}</p>
<table><tr><th>#</th><th>曲目</th><th>场次提及</th><th>覆盖巡次数</th><th>巡次</th><th>门槛</th></tr>{rows}</table>

<h2>②b 点歌池常驻曲</h2>
{pool_html}
<h2>③ 平台模板</h2>
{tpl_html}
<p class="meta">抖音「片段位」为纯文字占位，<b>不含音视频文件/链接/嵌入</b>；发布者自备素材，本站不提供音视频。</p>

<h2>④ 使用纪律（六条）</h2>
<ol>{disc}</ol>

<h2>⑤ 作战地图 · 三层挖词表</h2>
<table><tr><th>层</th><th>目标词数</th><th>已有</th><th>填充方</th></tr>{kw_rows}</table>
<p class="meta">挖词指引：{esc(' / '.join((kw.get('dig_guide') or [])))}</p>
</body></html>
"""
    # ?card=<id> 竖屏视图（静态文件便于直接截图，也支持 query）
    q = ""
    if "?" in q:
        pass
    OUT.write_text(html, encoding="utf-8")
    for c in cards:
        frag = (RENDER / f"card_{c['id']}.html").read_text(encoding="utf-8")
        (SITE / f"share-{c['id']}.html").write_text(
            f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(c['title'])}（分享卡）｜王晰数字图书馆</title>
<meta name="robots" content="noindex,follow">
<style>body{{max-width:420px;margin:0 auto;padding:16px;font:15px/1.7 -apple-system,"Microsoft YaHei",sans-serif;background:#faf6ef;color:#2b2320}}
.card{{background:#fff;border-radius:12px;padding:14px}} .big{{font-size:34px;font-weight:700}} .foot{{color:#8a7f6d;font-size:12px}}
.lock{{background:#fff4f0;border-left:3px solid #d98b6a;padding:8px;margin:8px 0;font-size:13px}}</style></head>
<body>{frag}</body></html>""", encoding="utf-8")
    print(f"[ok] {OUT.name}（5 区）+ {len(cards)} 张竖屏分享卡 share-*.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
