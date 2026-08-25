# -*- coding: utf-8 -*-
"""渲染「广州站整理摘录」区块到 live-reviews.html（重庆摘录下，防重建丢失）

数据源：temp/_gz_quotes.json（人工维护的广州站整场观感/主题精选）
原则（与 render_xhs_songs.py 一致）：
- 只收录整场观感与跨曲主题评论，与「按歌曲归类」区互斥、不重复
- 昵称匿名化为「观众X」（与按歌曲归类区同一编号）；来源（平台/日期/单源）披露
- blockquote + quote-meta 语义结构；幂等（先删旧区块再写）
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audience_anon

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\wx409.github.io")
HTML = ROOT / "live-reviews.html"
QUOTES = ROOT / "temp" / "_gz_quotes.json"
SHOW_DATE = "2026-08-23"


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def main():
    if not QUOTES.exists():
        print("无 _gz_quotes.json，跳过（整理摘录未配置）"); return
    quotes = json.loads(QUOTES.read_text(encoding="utf-8"))
    rows = quotes.get("quotes", [])
    if not rows:
        print("无整理摘录内容"); return

    aud_map = audience_anon.build_audience_map()

    lis = []
    for q in rows:
        val = q.get("text", "")
        author = q.get("author", "")
        anon = audience_anon.anonymize(author, aud_map)  # '小红书 @昵称' -> '小红书观众 X'
        code = anon.replace("小红书观众 ", "") if anon != "小红书观众" else ""
        lis.append(
            f'        <li class="audience-quote" data-audience="{esc(code)}">'
            f'<blockquote>{esc(val)}</blockquote>'
            f'<p class="quote-meta"><span class="tag">小红书</span> {esc(anon)} · {SHOW_DATE} · '
            f'<span class="src-badge single">单源</span></p></li>'
        )

    section = (
        '\n\n    <h2 id="guangzhou-20260823">六巡 · 回（2026）· 广州站整理摘录</h2>\n'
        '    <div class="history-item" style="border-left:4px solid #0a7a5a;padding-left:12px;">\n'
        '        <strong>2026.08.23</strong> · 广州 · 广东艺术剧院 · 六巡「回」\n'
        '        <p class="src-note">'
        '整场观感与主题精选，与上方「按歌曲归类」区互补、不重复收录；'
        '为保护隐私，昵称以「观众X」匿名呈现（同一编号即同一观众）。</p>\n'
        '        <ul class="quote-list">\n' + "\n".join(lis) + '\n        </ul>\n'
        '    </div>\n'
    )

    html = HTML.read_text(encoding="utf-8")
    # 删旧区块：从广州 h2 到「如何贡献」h2（无缩进的 <h2>如何贡献）之前，或页脚前
    pat = re.compile(
        r'\n    <h2 id="guangzhou-20260823">.*?(?=\n<h2>如何贡献|\n    <p style="margin-top: 40px)',
        re.S)
    html, n_del = pat.subn("", html)
    # 插入到重庆摘录 div 后、如何贡献 前
    i = html.find('id="chongqing-20260613"')
    j = html.find("</div>", i)
    k = html.find("<h2>如何贡献", j)
    if i < 0 or j < 0 or k < 0:
        print("!! 定位失败"); return
    html = html[:k] + section + html[k:]
    HTML.write_text(html, encoding="utf-8")
    print(f"已写入广州整理摘录区（删旧 {n_del} 个，匿名编号 {len(aud_map)} 位观众）")


if __name__ == "__main__":
    main()
