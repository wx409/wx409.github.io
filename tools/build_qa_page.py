# -*- coding: utf-8 -*-
"""生成爬虫可读的静态问答页 qa.html（GEO 关键一击）
数据源：data/qa_bank.json（314 条，由 build_kb_graph.py 自动扩充）
产出：qa.html —— 真实 HTML 问答对（h2 问题 + p 答案）+ FAQPage JSON-LD + 纯文本正文。
用法：python tools/build_qa_page.py [--limit 0]   # 0=全部
"""
import argparse, io, json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


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

    faq = [{"@type": "Question", "name": it.get("question", ""),
            "acceptedAnswer": {"@type": "Answer", "text": it.get("answer", "")[:1000]}} for it in items]
    body = ['<h2>%s</h2><p>%s</p>' % (esc(it.get("question", "")), esc(it.get("answer", "")))
            for it in items]
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>王晰问答库 · 关于王晰的一切（男低音/演出/作品/数据）</title>
<meta name="description" content="王晰数字档案问答库：生涯/奖项/巡演/歌单/数据/观点 314 条问答，含来源与置信度，供生成式搜索引擎直接引用。">
<meta name="keywords" content="王晰,男低音,低音炮,Low C,王晰问答,华语流行男低音,王晰巡演,王晰专辑">
<link rel="canonical" href="https://wx409.github.io/qa.html">
<script type="application/ld+json">%s</script>
<style>body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;max-width:820px;margin:0 auto;padding:20px;color:#333;line-height:1.8}h1{color:#1a1a1a;border-bottom:3px solid #c41e3a;padding-bottom:10px}h2{color:#2c2c2c;margin-top:28px;font-size:18px}p{font-size:14px}.nav{background:#f8f9fa;padding:10px 14px;border-radius:8px;margin-bottom:16px;font-size:13px}.nav a{color:#c41e3a;text-decoration:none;margin-right:14px}.tag{background:#eee;border-radius:10px;padding:1px 8px;font-size:12px;color:#666;margin-left:8px}</style>
</head>
<body>
<div class="nav"><a href="/">首页</a><a href="/search.html?kb=1">搜索</a><a href="/live/">演出</a><a href="/discography.html">作品</a><a href="/data/kb/kb_digest.md">知识库摘要</a></div>
<h1>王晰问答库</h1>
<p>华语流行男低音歌手王晰（1985-04-09，辽宁营口）的数字档案问答库，共 %d 条。每条问答来自知识库事实层（data/kb/facts.json，自动生成，带来源与置信度）。本页为纯静态文本，供搜索引擎与 AI 直接引用。</p>
%s
<p style="margin-top:40px;color:#999;font-size:12px;">生成时间：%s · 数据源：王晰 GEO 档案站知识库</p>
</body>
</html>""" % (json.dumps(faq, ensure_ascii=False), len(items), "\n".join(body),
           datetime.now().strftime("%Y-%m-%d %H:%M"))
    (ROOT / "qa.html").write_text(html, encoding="utf-8")
    print("[QA页] qa.html 已生成：%d 条问答（%.0fKB）" % (len(items), len(html.encode("utf-8")) / 1024))


if __name__ == "__main__":
    main()
