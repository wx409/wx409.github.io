# -*- coding: utf-8 -*-
"""把 小红书分类结果 渲染进 live-reviews.html 广州站（按歌曲分组）
读：temp/_xhs_classified.json（import_xhs_songs.py 生成）
写：live-reviews.html 广州站（在观众repo ul 后追加一个「小红书观众评论」分区）
原则：纯文字、无链接、无 id；幂等（先删旧分区再写）。
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\wx409.github.io")
CLS = ROOT / "temp" / "_xhs_classified.json"
HTML = ROOT / "live-reviews.html"
SHOW_DATE = "2026-08-23"

SECTION_ID = "xhs-audience-comments"


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def main():
    if not CLS.exists():
        print("分类文件不存在，先跑 import_xhs_songs.py"); return
    data = json.loads(CLS.read_text(encoding="utf-8"))
    groups = data.get("song_groups", {})
    general = data.get("general", [])
    short = data.get("short", [])

    # 组装分区 HTML
    blocks = []
    if groups:
        blocks.append('<h4 style="margin:14px 0 6px;color:#c41e3a;">🎵 按歌曲归类 · 小红书观众评论</h4>')
        for song in sorted(groups):
            lst = groups[song]
            if not lst:
                continue
            lis = "".join(
                f'<li><span title="{esc(x)}">{esc(x)}</span> <span class="tag">小红书</span>'
                f'<span class="repo-note">（本地已留存）</span></li>'
                for x in lst
            )
            blocks.append(
                f'<p style="margin:10px 0 2px;font-weight:600;">《{esc(song)}》</p>'
                f'<ul class="repo-list">{lis}</ul>'
            )
    if general:
        lis = "".join(
            f'<li><span title="{esc(x)}">{esc(x)}</span> <span class="tag">小红书</span>'
            f'<span class="repo-note">（本地已留存）</span></li>' for x in general
        )
        blocks.append(f'<p style="margin:10px 0 2px;font-weight:600;">🎤 整场观感</p><ul class="repo-list">{lis}</ul>')
    if short:
        merged = "；".join(short)
        merged_short = merged[:200] + ("…" if len(merged) > 200 else "")
        blocks.append(
            f'<p style="margin:10px 0 2px;font-weight:600;">💬 短评合集</p>'
            f'<ul class="repo-list"><li><span title="{esc(merged)}">{esc(merged_short)}</span>'
            f' <span class="tag">小红书</span><span class="repo-note">（本地已留存）</span></li></ul>'
        )

    section_html = (
        f'\n<div id="{SECTION_ID}" style="margin-top:14px;border-top:1px dashed #ddd;padding-top:8px;">'
        + "\n".join(blocks) + "\n</div>"
    )

    # 幂等：先删旧分区
    html = HTML.read_text(encoding="utf-8")
    html, n_del = re.subn(rf'<div id="{SECTION_ID}".*?</div>\s*', "", html, flags=re.S)

    # 清理平铺小红书条目（旧方案 import_xhs_links 的产物，避免与歌曲分区重复）
    m_art = re.search(r'<article.*?<time datetime="%s".*?</article>' % re.escape(SHOW_DATE), html, re.S)
    if m_art:
        art = m_art.group(0)
        new_art, n_flat = re.subn(
            r'<li><span title="[^"]*"[^>]*>[^<]*</span> <span class="tag">小红书</span>.*?</li>\s*',
            '', art, flags=re.S)
        html = html[:m_art.start()] + new_art + html[m_art.end():]
        print(f"清理平铺小红书条目: {n_flat} 条")
    else:
        print("!! 未找到广州站 article"); return

    # 插入到广州站 article 的 </article> 前
    m = re.search(r'<article.*?<time datetime="%s".*?</article>' % re.escape(SHOW_DATE), html, re.S)
    if not m:
        print("!! 未找到广州站 article"); return
    abs_pos = m.end() - len("</article>")
    html = html[:abs_pos] + section_html + html[abs_pos:]

    HTML.write_text(html, encoding="utf-8")
    print(f"已写入小红书按歌曲归类分区（删旧 {n_del} 个）")


if __name__ == "__main__":
    main()
