#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""学术研究页生成器：data/literature.json → academic.html（单一事实源，幂等）。

为什么用脚本而不是手改页面：
  文献索引会持续增补（王晰专题 / 低音与花腔 / 国际方法学 / 数据边界 / GEO），
  手改 HTML 必然出现「JSON-LD 与正文不同步」「样式漂移」「漏挂导航」三类问题。
  本脚本把文献数据与渲染分离：**新增文献只改 data/literature.json**，页面与结构化数据一次生成。

用法：
  python project_b/build_academic.py            # 生成 academic.html
  python project_b/build_academic.py --check    # 只校验是否需要更新（退出码 1 = 有漂移）
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "literature.json"
OUT = ROOT / "academic.html"

STYLE = """
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; line-height: 1.8; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }
        h1 { color: #1a1a1a; border-bottom: 3px solid #c41e3a; padding-bottom: 10px; }
        h2 { color: #2c2c2c; margin-top: 34px; border-left: 4px solid #c41e3a; padding-left: 12px; }
        h3 { font-size: 17px; }
        .nav { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .nav a { color: #c41e3a; margin-right: 20px; text-decoration: none; font-weight: 500; }
        .paper { background: #fafafa; padding: 20px; margin: 20px 0; border-radius: 8px; }
        .paper h3 { margin-top: 0; color: #1a1a1a; font-size: 18px; }
        .meta { color: #666; font-size: 14px; margin: 10px 0; }
        .abstract { background: #fff; padding: 15px; border-left: 3px solid #c41e3a; margin: 10px 0; font-size: 14px; }
        .tag { display: inline-block; background: #e9ecef; padding: 2px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px; }
        .sec-desc { color: #555; font-size: 14px; margin: 8px 0 4px; }
        .lit-list { background: #fafafa; padding: 14px 20px; border-radius: 8px; margin: 16px 0; }
        .lit-list li { margin: 12px 0; font-size: 14.5px; }
        .lit-list .t { font-weight: 600; color: #1a1a1a; }
        .lit-list .m { color: #666; font-size: 13px; }
        .lit-list .v { color: #444; font-size: 13.5px; display: block; margin-top: 3px; }
        .note { background: #fff8e6; border-left: 3px solid #c9a227; padding: 12px 16px; font-size: 13.5px; margin: 18px 0; border-radius: 4px; }
"""


def esc(s) -> str:
    return html.escape(str(s or ""))


def render_jsonld(doc: dict) -> str:
    graph = []
    for sec in doc["sections"]:
        for it in sec["items"]:
            if sec["style"] != "paper":
                continue
            node = {
                "@type": "ScholarlyArticle" if "论文" in "".join(it.get("tags", [])) else "Article",
                "headline": it["title"],
                "publisher": {"@type": "Organization", "name": it.get("venue", "")},
                "datePublished": it.get("year", ""),
                "description": (it.get("abstract") or it.get("value") or "")[:300],
            }
            authors = [a.strip() for a in str(it.get("authors", "")).split("、") if a.strip()]
            if authors:
                node["author"] = [{"@type": "Person", "name": a} for a in authors]
            ids = it.get("meta", "")
            if "DOI" in ids:
                import re
                m = re.search(r"DOI：([^\s｜|]+)", ids)
                if m:
                    node["identifier"] = m.group(1)
            graph.append(node)
    return json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, indent=2)


def render_paper_item(it: dict) -> str:
    h = ['    <div class="paper">']
    h.append(f'        <h3>{it["title"]}</h3>')
    meta_bits = []
    if it.get("tags"):
        meta_bits.append("".join(f'<span class="tag">{esc(t)}</span>' for t in it["tags"]))
    line = []
    if it.get("authors"):
        line.append(f'作者：{esc(it["authors"])}')
    if it.get("venue"):
        line.append(esc(it["venue"]))
    if it.get("year"):
        line.append(f'{esc(it["year"])}年')
    if it.get("pages"):
        line.append(esc(it["pages"]))
    meta_bits.append(" &nbsp;|&nbsp; ".join(line))
    h.append(f'        <div class="meta">{" ".join(meta_bits)}</div>')
    if it.get("abstract"):
        h.append(f'        <div class="abstract"><strong>摘要：</strong>{esc(it["abstract"])}</div>')
    if it.get("keywords"):
        h.append(f'        <p><strong>关键词：</strong>{esc(it["keywords"])}</p>')
    if it.get("value"):
        h.append(f'        <p><strong>核心学术价值：</strong>{it["value"]}</p>')
    if it.get("meta"):
        h.append(f'        <p class="meta">{it["meta"]}</p>')
    h.append("    </div>")
    return "\n".join(h)


def render_list_section(sec: dict) -> str:
    h = ['    <ul class="lit-list">']
    for it in sec["items"]:
        bits = []
        if it.get("authors"):
            bits.append(esc(it["authors"]))
        if it.get("venue"):
            bits.append(esc(it["venue"]))
        if it.get("year"):
            bits.append(esc(it["year"]))
        if it.get("meta"):
            bits.append(esc(it["meta"]))
        h.append("        <li>")
        h.append(f'            <span class="t">{it["title"]}</span>')
        h.append(f'            <span class="m">{" ｜ ".join(bits)}</span>')
        if it.get("value"):
            h.append(f'            <span class="v">{it["value"]}</span>')
        h.append("        </li>")
    h.append("    </ul>")
    return "\n".join(h)


def render_fan_section() -> str:
    """歌迷赏析（民间评论）——只登记元数据与声学互证，**不转载全文**（第三方著作权）。"""
    p = ROOT / "data" / "fan_essays.json"
    if not p.exists():
        return ""
    d = json.loads(p.read_text(encoding="utf-8"))
    items = d.get("items") or []
    if not items:
        return ""
    SRC_LABEL = {"setlist": "巡演歌单", "event": "演出活动表", "catalog": "全量曲库", "none": "未命中",
                 "songinfo": "歌曲信息汇总", "netease": "网易云目录", "medley": "组曲展开", "album": "整张专辑"}
    rows = []
    n_pub = 0
    for it in items:
        a = it.get("acoustic") or {}
        ac = (f'{esc(a.get("low_note"))} {a.get("low_hz")} Hz'
              + (f'（{a.get("versions")} 个版本）' if (a.get("versions") or 0) > 1 else "")) if a else "—"
        rs = (it.get("resolved") or {})
        src = SRC_LABEL.get(rs.get("source"), "—")
        if rs.get("kind") in ("album", "series"):
            src += f'（{"整张专辑" if rs["kind"] == "album" else "组曲/系列"}）'
        pub = esc(it.get("published") or "")
        if "已发表" in str(it.get("published") or ""):
            n_pub += 1
            pub = f'<strong style="color:#a8323d">{pub}</strong>'
            if it.get("platform"):
                pub += f'<br><span class="sub">＋ {esc(it["platform"])}</span>'
        rows.append(
            f'<tr><td>{it.get("no")}</td><td><strong>{esc(it.get("song"))}</strong></td>'
            f'<td>{esc(it.get("title"))}</td><td>{it.get("chars")} 字</td>'
            f'<td>{esc(it.get("written"))}</td><td>{esc(it.get("author"))}</td>'
            f'<td>{pub}</td><td>{src}</td><td>{ac}</td></tr>')
    c = d.get("counts") or {}
    rb = c.get("resolved_by") or {}
    return "\n".join([
        '    <h2 id="fan-essays">七、歌迷赏析（民间评论 · 曲目级文本分析）</h2>',
        f'    <p class="sec-desc">共 <strong>{c.get("total")} 篇 / {c.get("total_chars")} 字</strong>（撰写于 2024-07，2026-09-11 整理入档），'
        f'其中 <strong>{c.get("with_acoustic")} 篇</strong>可与本站声学实测（最低稳定音口径）逐曲互证。'
        '这批文本从听感与编配层面分析具体舞台版本（混响时值、音程跨度、胸腔共鸣、颤音、改编结构），'
        '与本站的逐帧 F0 实测构成「主观听感 × 客观读数」的对照样本。</p>',
        f'    <p class="sub">曲名解析沿用站内既有归一化与别名表，按「巡演歌单 → 演出活动表 → 全量曲库 → 歌曲信息汇总 → 网易云目录」查找：'
        f'歌单 {rb.get("setlist", 0)} 篇、活动表 {rb.get("event", 0)} 篇、全量曲库 {rb.get("catalog", 0)} 篇；'
        f'其余 {rb.get("none", 0)} 篇为整张专辑评述或组曲系列（已如实标注，不臆造匹配）。</p>',
        f'    <p class="sec-desc"><strong>其中 {n_pub} 篇已正式发表</strong>：刊于<strong>国家级核心期刊《乐器》</strong>'
        f'（2021 年第 3、4 期，见本页第一节文献著录），并在<strong>国家乐器信息中心微信平台</strong>推送 —— '
        f'即这批赏析已从「乐迷写作」进入「可引用的公开出版物」，对「王晰演唱具有学术评析价值」构成第三方书面证据。</p>',
        '    <table><tr><th>#</th><th>曲目</th><th>篇名</th><th>篇幅</th><th>撰写</th><th>作者</th>'
        '<th>发表 / 出处</th><th>曲名解析来源</th><th>本站声学互证（最低稳定音）</th></tr>',
        "\n".join(rows),
        "    </table>",
        f'    <p class="meta">著作权与授权：全文为作者本人作品，本站<strong>不转载全文、不提供下载</strong>；'
        f'发表状态与授权状态均标注「{esc((d.get("rights") or {}).get("status"))}」，由作者确认后更新。'
        f'{esc((d.get("rights") or {}).get("contact") or "")}</p>',
        '    <p class="meta">数据源 <code>data/fan_essays.json</code>（元数据索引）；全文仅本地留存，未进入公开仓库。'
        '互证列取该曲录音室或现场实测的最低稳定音（≥0.2s、HNR≥5dB 稳健口径）。</p>',
        "",
    ])


def build(doc: dict) -> str:
    jsonld = render_jsonld(doc)
    n_cn = sum(len(s["items"]) for s in doc["sections"] if s["style"] == "paper")
    n_intl = sum(len(s["items"]) for s in doc["sections"] if s["style"] == "list")
    parts = [
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        "    <title>王晰学术研究索引 | 低音与花腔文献、声部声学与国际方法学</title>",
        f'    <meta name="description" content="王晰演唱专题研究、男低音与中低音花腔技法、声部辨识与音域测量、人声分离与基频提取、数字传播因果识别、GEO 与知识图谱，以及歌迷赏析（民间评论）——共 {n_cn + n_intl} 条可核验文献索引 + 歌迷赏析索引，逐条附出处。">',
        "    <style>" + STYLE + "    </style>",
        '    <script type="application/ld+json">',
        jsonld,
        "    </script>",
        '    <link rel="stylesheet" href="assets/brand.css">',
        '    <link rel="canonical" href="https://wx409.github.io/academic.html">',
        '    <meta property="og:image" content="https://wx409.github.io/cover.png">',
        '    <meta name="twitter:image" content="https://wx409.github.io/cover.png">',
        '    <meta property="og:type" content="website">',
        "</head>",
        "<body>",
        "<!-- NAV_START --><!-- NAV_END -->",
        "",
        "    <h1>学术研究｜王晰演唱技法、低音与花腔文献索引</h1>",
        f'    <p>本页为可核验的文献索引，共 <strong>{n_cn + n_intl} 条</strong>，分七部分：王晰演唱专题、男低音／中低音与花腔、声部辨识与音域测量、基频提取与人声分离、数字传播与因果识别、GEO 与知识图谱，以及<strong>歌迷赏析（民间评论）</strong>。中文条目来自 CNKI／万方／维普公开著录页，国际条目均附 DOI 或 arXiv 编号；<strong>元数据未能核实者已明确标注「待核」</strong>。歌迷赏析部分只登记篇名、篇幅与声学互证，不转载全文。</p>',
        '    <div class="note">📌 相关页面：<a href="/voice.html">音域实测（10 曲人声分离 F0 实测）</a> · <a href="/qa.html">问答库</a> · <a href="/data/calibers.md">口径登记表</a>。本站的实证结论与文献方法的对应关系，见下各节说明。</div>',
        "",
    ]
    for sec in doc["sections"]:
        parts.append(f'    <h2 id="{sec["id"]}">{sec["title"]}</h2>')
        if sec.get("desc"):
            parts.append(f'    <p class="sec-desc">{sec["desc"]}</p>')
        if sec["style"] == "paper":
            for it in sec["items"]:
                parts.append(render_paper_item(it))
        else:
            parts.append(render_list_section(sec))
        parts.append("")

    fan = render_fan_section()
    if fan:
        parts.append(fan)
    parts.append("    <h2>研究价值总结</h2>")
    parts.append("    <ul>")
    for s in doc.get("summary", []):
        parts.append(f"        <li>{s}</li>")
    parts.append("    </ul>")
    parts.append(f'    <p class="meta">文献索引最后更新：{esc(doc.get("generated_at"))}（数据源 <code>data/literature.json</code>，由 <code>project_b/build_academic.py</code> 自动渲染）。</p>')
    parts.append("")
    parts.append('    <p style="margin-top: 40px; color: #999; font-size: 12px;">本页仅作学术索引，论文版权归原作者、期刊与数据库所有。如需引用请通过正规学术渠道获取原文。中文条目的摘要文字照录数据库公开著录页，未作改写。</p>')
    parts.append('<script src="/qa_engine.js"></script>')
    parts.append("<!-- FOOTER_NAV_START --><!-- FOOTER_NAV_END -->")
    parts.append("</body>")
    parts.append("</html>")
    parts.append("")
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser(description="学术研究页生成器")
    ap.add_argument("--check", action="store_true", help="只检查是否需要更新")
    args = ap.parse_args()

    doc = json.loads(SRC.read_text(encoding="utf-8"))
    new = build(doc)
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    # 忽略导航/底部索引内容（由 build_nav.py 管理）再比较
    def strip_nav(t: str) -> str:
        import re
        t = re.sub(r"<!-- NAV_START -->.*?<!-- NAV_END -->", "NAV", t, flags=re.S)
        t = re.sub(r"<!-- FOOTER_NAV_START -->.*?<!-- FOOTER_NAV_END -->", "FOOT", t, flags=re.S)
        return t
    changed = strip_nav(new) != strip_nav(old)
    n = sum(len(s["items"]) for s in doc["sections"])
    print("=" * 68)
    print("学术研究页生成器（build_academic.py）")
    print("=" * 68)
    print(f"文献条目：{n} 条（中文 {sum(len(s['items']) for s in doc['sections'] if s['style']=='paper')} / 国际 {sum(len(s['items']) for s in doc['sections'] if s['style']=='list')}）")
    if args.check:
        print("需更新" if changed else "已是最新 ✅")
        if changed:
            sys.exit(1)
        return
    if changed:
        OUT.write_text(new, encoding="utf-8")
        print(f"[OK] 已生成 {OUT.relative_to(ROOT)}")
    else:
        print("无变化，跳过写入")


if __name__ == "__main__":
    main()
