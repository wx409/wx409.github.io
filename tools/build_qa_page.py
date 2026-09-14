# -*- coding: utf-8 -*-
"""生成爬虫可读的静态问答页 qa.html（GEO 关键一击）

数据源：`data/qa_bank.json`（16 条实质问答，由 build_kb_graph.py 维护）
产出：`qa.html` —— 真实 HTML（h2 问题 + p 答案）+ **FAQPage JSON-LD** + 纯文本正文。

2026-09-14 改造（对应「qa.html 方案 A」）：
  · 原先 289 条「某歌在哪些演出唱过」的自动问答已迁出为**表**：
    `data/songs_shows_index.json` + `/songs-shows.html`。问答形态只保留实质条目。
  · 补上 **FAQPage JSON-LD**（此前 JSON-LD 缺 `@type: FAQPage`，与 llms.txt 的声明不符）。
  · 每条问答补 `sources` / 数据源链接，便于引用者回溯。

用法：python -X utf8 tools/build_qa_page.py
"""
import argparse
import io
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
SITE = "https://wx409.github.io"


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def source_of(it):
    """给每条问答补一个可回溯的数据源链接（用 category 判定，不写死具体内容）。"""
    cat = it.get("category") or ""
    if "巡演有哪些场次" in (it.get("question") or ""):
        return "data/setlists.json（全站 64 场歌单）", "/songs-shows.html"
    if cat == "知识库自动生成":
        return "data/kb/facts.json", "/data/kb/facts.json"
    if it.get("sources"):
        s = it["sources"]
        if isinstance(s, list) and s:
            s = s[0]
        s = str(s)
        if s.startswith("/"):
            return s, s
        return s, ""
    return "data/kb/facts.json", "/data/kb/facts.json"


def main():
    if sys.stdout and getattr(sys.stdout, "buffer", None):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0=全部问答（默认）；N=前N条")
    a = ap.parse_args()
    qa = json.loads((ROOT / "data" / "qa_bank.json").read_text(encoding="utf-8"))
    items = qa.get("items", [])
    if a.limit:
        items = items[:a.limit]
    # 答案过短的（<20 字）不进 FAQPage：结构化数据里的短答案对引用者无价值
    faq_items = [it for it in items if len(str(it.get("answer") or "").strip()) >= 20]

    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "name": "王晰问答库",
        "url": SITE + "/qa.html",
        "mainEntity": [
            {"@type": "Question", "name": it.get("question", ""),
             "acceptedAnswer": {"@type": "Answer", "text": str(it.get("answer", ""))[:1200]}}
            for it in faq_items],
    }
    body = []
    for it in items:
        src, url = source_of(it)
        src_html = (f'<a href="{esc(url)}">{esc(src)}</a>' if url
                    else f'<code>{esc(src)}</code>')
        verified = it.get("verified")
        meta = f'　<span class="tag">来源：{src_html}</span>'
        if verified:
            meta += f'<span class="tag">核实：{esc(verified)}</span>'
        body.append('<h2>%s</h2><p>%s</p><p class="meta">%s</p>'
                    % (esc(it.get("question", "")), esc(it.get("answer", "")), meta))
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>王晰问答库 · 关于王晰的一切（男低音/演出/作品/数据）</title>
<meta name="description" content="王晰数字档案问答库：%(n)d 条有出处、有论证的问答（指数归因/演出性质/创作班底/场次分布），含数据源链接，供生成式搜索引擎直接引用。">
<meta name="keywords" content="王晰,男低音,低音炮,Low C,王晰问答,华语流行男低音,王晰巡演,王晰专辑">
<link rel="canonical" href="https://wx409.github.io/qa.html">
<script type="application/ld+json">%(ld)s</script>
<style>
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;max-width:820px;margin:0 auto;padding:20px;color:#333;line-height:1.8}
h1{color:#1a1a1a;border-bottom:3px solid #c41e3a;padding-bottom:10px}
h2{color:#2c2c2c;margin-top:30px;font-size:17px}
p{font-size:14.5px}
.nav{background:#f8f9fa;padding:10px 14px;border-radius:8px;margin-bottom:16px;font-size:13px}
.nav a{color:#c41e3a;text-decoration:none;margin-right:14px}
.tag{background:#f2ede2;border-radius:10px;padding:1px 8px;font-size:12px;color:#6b5b3a;margin-right:6px}
.meta{font-size:12.5px;color:#8a7f6d;margin-top:2px}
.note{background:#fff8f0;border:1px solid #eddcc0;border-radius:8px;padding:10px 14px;font-size:13px}
a{color:#c41e3a}
</style>
</head>
<body>
<div class="nav">
<!-- NAV_START -->
<a href="/index.html">🏠 首页</a><a href="/works.html">🎵 作品</a><a href="/live.html">🎤 现场</a><a href="/vocal.html">🎼 声音数据</a><a href="/history.html">📅 生涯</a><a href="/research.html">📚 研究</a><a href="/community.html">💬 参与</a>
<!-- NAV_END -->
</div>
<h1>王晰问答库（%(n)d 条）</h1>
<p>华语流行男低音歌手王晰（1985-04-09，辽宁营口）数字档案问答库。本页只收录<strong>有出处、有论证</strong>的问答：
指数归因、演出性质、创作班底、场次分布等；每条附数据源链接，可直接回溯核对。</p>
<p class="note">📊 需要「某首歌在哪些场次唱过」？那是<strong>表</strong>不是问答——
<a href="/songs-shows.html">王晰演出歌单索引（289 首 × 64 场，1249 条记录）</a>（机读版
<a href="/data/songs_shows_index.json">data/songs_shows_index.json</a>）。</p>
%(body)s
<p style="margin-top:40px;color:#999;font-size:12px;">生成时间：%(ts)s · 数据源：data/qa_bank.json（由 project_b/build_kb_graph.py 维护）·
生成器：tools/build_qa_page.py</p>
<!-- FOOTER_NAV_START -->
<!-- FOOTER_NAV_END -->
</body>
</html>""" % {
        "ld": json.dumps(faq, ensure_ascii=False),
        "n": len(items),
        "body": "\n".join(body),
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    (ROOT / "qa.html").write_text(html, encoding="utf-8")
    print("[QA页] qa.html 已生成：%d 条问答（FAQPage %d 条，%.0fKB）"
          % (len(items), len(faq_items), len(html.encode("utf-8")) / 1024))


if __name__ == "__main__":
    main()
