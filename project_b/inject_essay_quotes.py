# -*- coding: utf-8 -*-
"""把歌迷赏析精彩句注入两处（标记块，幂等）：
  ① 首页 index.html「金句墙 · 听众说」——标注「歌迷赏析摘录」，不冒充观众repo；
  ② 巡演页 live/*.html——该页歌单含某曲目时，在「数据效应」前插入该曲赏析摘录。

数据源：data/essay_quotes.json（人工精选，作者授权引用；全文仅本地留存）
用法：python -X utf8 project_b/inject_essay_quotes.py [--check]
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data" / "essay_quotes.json"
INDEX = ROOT / "index.html"
LIVE = ROOT / "live"

IDX_START = "<!-- ESSAY-QUOTES-INDEX:START（由 project_b/inject_essay_quotes.py 生成，勿手改）-->"
IDX_END = "<!-- ESSAY-QUOTES-INDEX:END -->"
LIVE_START = "<!-- ESSAY-QUOTES-LIVE:START（同上，勿手改）-->"
LIVE_END = "<!-- ESSAY-QUOTES-LIVE:END -->"


def esc(t: str) -> str:
    return html.escape(str(t or ""), quote=True)


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def block_index(items: list[dict]) -> str:
    rows = [IDX_START]
    for it in items:
        pub = f' · {esc(it["published"])}' if it.get("published") else ""
        rows.append(
            '<article class="quote-item" data-source-level="oral">'
            f'<blockquote><p>"{esc(it["punch"])}"</p>'
            f'<small>— 歌迷赏析《{esc(it["source_title"])}》，{esc(it["author"])}，2024.07</small></blockquote>'
            f'<span class="source-verification">来源：《{esc(it["song"])}》曲目赏析（曲目级文本分析{pub}）'
            f' · 作者授权引用，全文仅本地留存 <span class="src-badge oral">歌迷赏析</span></span>'
            '</article>')
    rows.append(IDX_END)
    return "\n".join(rows)


def block_live(page_html: str, items: list[dict]) -> str | None:
    hits = [it for it in items if f'《{it["song"]}》' in page_html or it["song"] in page_html]
    if not hits:
        return None
    rows = [LIVE_START, '<h2>📖 曲目赏析摘录（歌迷评论）</h2>',
            '<p style="font-size:13px;color:#777;">本场歌单中曲目的歌迷赏析摘录（作者授权引用，全文仅本地留存、本站不转载）。'
            '与本站声学实测互证见 <a href="../voice.html">音域实测页</a>。</p>', '<ul>']
    for it in hits:
        pub = f' · {esc(it["published"])}' if it.get("published") else ""
        rows.append(f'<li>《{esc(it["song"])}》—— «{esc(it["quote"])}»'
                    f'<br><span style="color:#888;font-size:12px">摘自《{esc(it["source_title"])}》，'
                    f'{esc(it["author"])}{pub}</span></li>')
    rows.append('</ul>')
    rows.append(LIVE_END)
    return "\n".join(rows)


def inject_index(doc: dict, check: bool) -> str:
    src = INDEX.read_text(encoding="utf-8")
    items = [it for it in doc["items"] if it.get("on_index")]
    block = block_index(items)
    if IDX_START in src and IDX_END in src:
        new = re.sub(re.escape(IDX_START) + r".*?" + re.escape(IDX_END), block, src, flags=re.S)
    else:
        anchor = "<h3>听众说</h3>"
        i = src.find(anchor)
        if i < 0:
            raise SystemExit("index.html 未找到「听众说」锚点")
        j = src.find("</section>", i)
        if j < 0:
            j = src.find("<h2", i)
        if j < 0:
            raise SystemExit("index.html 未找到「听众说」段落边界")
        new = src[:j] + block + "\n" + src[j:]
    if new != src and not check:
        INDEX.write_text(new, encoding="utf-8", newline="")
    return f"index.html：{'更新' if new != src else '无变化'}（{len(items)} 条）"


def inject_live(doc: dict, check: bool) -> list[str]:
    out = []
    for p in sorted(LIVE.glob("*.html")):
        src = p.read_text(encoding="utf-8")
        block = block_live(src, doc["items"])
        if block is None:
            if LIVE_START in src:
                new = re.sub(re.escape(LIVE_START) + r".*?" + re.escape(LIVE_END), "", src, flags=re.S)
                if new != src and not check:
                    p.write_text(new, encoding="utf-8", newline="")
                out.append(f"{p.name}：移除（歌单无匹配曲目）")
            continue
        if LIVE_START in src and LIVE_END in src:
            new = re.sub(re.escape(LIVE_START) + r".*?" + re.escape(LIVE_END), block, src, flags=re.S)
        else:
            m = re.search(r"<h2>📊 数据效应", src)
            if not m:
                m = re.search(r"<h2>[^<]*歌单", src)
            if not m:
                out.append(f"{p.name}：跳过（未找到插入锚点）")
                continue
            new = src[:m.start()] + block + "\n" + src[m.start():]
        if new != src and not check:
            p.write_text(new, encoding="utf-8", newline="")
        out.append(f"{p.name}：{'更新' if new != src else '无变化'}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    doc = load()
    print("[歌迷赏析摘录注入]", "（check 模式，不写盘）" if a.check else "")
    print(" ", inject_index(doc, a.check))
    for line in inject_live(doc, a.check):
        print(" ", line)
    print(f"  数据源 data/essay_quotes.json：{len(doc['items'])} 条（首页精选 {sum(1 for i in doc['items'] if i.get('on_index'))} 条）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
