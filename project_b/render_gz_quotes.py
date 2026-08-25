# -*- coding: utf-8 -*-
"""渲染「广州站优美评论」区块到 live-reviews.html（重庆摘录下，防重建丢失）
数据源：temp/_gz_quotes.json（人工维护的广州站精选评论）
幂等：先删旧区块再写。build_live_reviews 重建后自动调用。
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\wx409.github.io")
HTML = ROOT / "live-reviews.html"
QUOTES = ROOT / "temp" / "_gz_quotes.json"


def main():
    if not QUOTES.exists():
        print("无 _gz_quotes.json，跳过（优美评论未配置）"); return
    quotes = json.loads(QUOTES.read_text(encoding="utf-8"))
    rows = quotes.get("quotes", [])
    if not rows:
        print("无优美评论内容"); return

    blocks = []
    for q in rows:
        val = q.get("text", "")
        author = q.get("author", "小红书观众")
        blocks.append(
            f'        <p style="font-size:13px;margin:6px 0;color:#444;">'
            f'<span class="tag">小红书</span> "{val}" '
            f'<span style="color:#999;font-size:12px;">—— {author}，2026.08.23 广州</span></p>'
        )

    section = (
        '\n\n    <h2 id="guangzhou-20260823">六巡 · 回（2026）· 广州站整理摘录</h2>\n'
        '    <div class="history-item" style="border-left:4px solid #0a7a5a;padding-left:12px;">\n'
        '        <strong>2026.08.23</strong> · 广州 · 广东艺术剧院 · 六巡「回」\n'
        '        <p style="color:#555;font-size:13px;margin:8px 0;">'
        '精选小红书观众现场评论（纯文字呈现，原文/图/视频本地已留存）。</p>\n'
        + "\n".join(blocks) +
        '\n    </div>\n'
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
    print(f"已写入广州优美评论区（删旧 {n_del} 个）")


if __name__ == "__main__":
    main()
