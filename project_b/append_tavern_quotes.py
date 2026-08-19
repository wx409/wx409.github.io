# -*- coding: utf-8 -*-
"""把小酒馆摘要中的金句并入 index.html 金句墙
从 tavern_summaries.json 提取 quotes，追加到 index.html 的「金句墙」板块。
用法：python project_b/append_tavern_quotes.py
"""
import json, re, html
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
SUMMARIES = ROOT / "tavern" / "tavern_summaries.json"
INDEX = ROOT / "index.html"
# 标记：已插入过则跳过（幂等）
MARKER = '<!-- tavern-quotes-inserted -->'

def build_quotes():
    d = json.loads(SUMMARIES.read_text(encoding='utf-8'))
    eps = d.get('episodes', {})
    all_q = []
    for key, v in eps.items():
        qs = v.get('quotes', [])
        theme = v.get('theme', '')
        ep = v.get('episode', key)
        for q in qs:
            q = q.strip().strip('"').strip()
            if q and len(q) >= 6:
                all_q.append((q, theme, ep))
    return all_q if all_q else None

def main():
    if MARKER in INDEX.read_text(encoding='utf-8'):
        print("已在 index.html 插入过小酒馆金句，跳过")
        return
    quotes = build_quotes()
    if not quotes:
        print("无金句可插入")
        return
    items = []
    for q, theme, ep in quotes:
        items.append(
            '    <article class="quote-item" data-source-level="oral">\n'
            '    <blockquote>\n'
            f'      <p>"{html.escape(q)}"</p>\n'
            f'      <small>— 王晰，深夜小酒馆「{html.escape(theme or ep)}」</small>\n'
            '    </blockquote>\n'
            '    <span class="source-verification">来源：深夜小酒馆逐字稿提炼，' +
            html.escape(ep) + ' <span class="src-badge oral">小酒馆</span> <em style="color:#b8860b;">（小酒馆逐字稿，已提练，原节目音频版权归原作者）</em></span>\n'
            '    </article>\n'
        )
    insert_block = (
        '\n    <h3>王晰 · 深夜小酒馆金句</h3>\n'
        + '\n'.join(items)
        + '\n' + MARKER + '\n'
    )
    idx = INDEX.read_text(encoding='utf-8')
    # 插入到「历史巡演回顾」之前（金句墙末尾）
    anchor = '<h2>历史巡演回顾'
    pos = idx.find(anchor)
    if pos < 0:
        print("[!] 未找到插入锚点")
        return
    new_html = idx[:pos] + insert_block + idx[pos:]
    INDEX.write_text(new_html, encoding='utf-8')
    print(f"[完成] 已插入 {len(quotes)} 条小酒馆金句到 index.html 金句墙")

if __name__ == '__main__':
    main()
