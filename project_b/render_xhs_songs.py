# -*- coding: utf-8 -*-
"""把小红书分类结果渲染进 live-reviews.html 广州站（按歌曲分组）

读：temp/_xhs_classified.json（import_xhs_songs.py 生成，保留原始昵称）
写：live-reviews.html 广州站 article 内「小红书观众评论 · 按歌曲归类」分区

原则（GEO + 隐私）：
- 来源（平台/日期/单源）披露；账号昵称匿名化为「观众A/B/C」（同一编号=同一观众，跨区一致）
- 去重：同一条正文在 ≥2 个歌目重复 → 视为整场观感，不在此区重复渲染（由整理摘录区策展）
- 全文可见（不再塞进 title 属性）；blockquote + quote-meta 语义结构
- 纯文字、无链接；幂等（先删旧分区再写）
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audience_anon

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\wx409.github.io")
CLS = ROOT / "temp" / "_xhs_classified.json"
HTML = ROOT / "live-reviews.html"
SHOW_DATE = "2026-08-23"

SECTION_ID = "xhs-audience-comments"


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def dedup_to_general(groups):
    """同正文在 ≥2 个歌目出现 → 归入整场观感（不在此区渲染）；仅 1 次 → 留在原歌目。"""
    counter = Counter()
    for lst in groups.values():
        for x in lst:
            counter[audience_anon.strip_nick(x)] += 1
    new_groups, general = {}, []
    for song, lst in groups.items():
        kept = [x for x in lst if counter[audience_anon.strip_nick(x)] == 1]
        general += [x for x in lst if counter[audience_anon.strip_nick(x)] >= 2]
        if kept:
            new_groups[song] = kept
    return new_groups, general


def render_quote(x, aud_map):
    code = aud_map.get(audience_anon.nick_of(x), "")
    body = esc(audience_anon.strip_nick(x))
    return (
        f'<li class="audience-quote" data-audience="{esc(code)}">'
        f'<blockquote>{body}</blockquote>'
        f'<p class="quote-meta"><span class="tag">小红书</span> 观众 {esc(code)} · 2026-08-23 · '
        f'<span class="src-badge single">单源</span></p></li>'
    )


def main():
    if not CLS.exists():
        print("分类文件不存在，先跑 import_xhs_songs.py"); return
    data = json.loads(CLS.read_text(encoding="utf-8"))
    groups = data.get("song_groups", {})
    general = list(data.get("general", []))
    short = data.get("short", [])

    groups, deduped_general = dedup_to_general(groups)
    general += deduped_general  # 跨歌文本并入整场观感（供摘录区策展，本区不渲染）
    print(f"去重：跨歌文本 {len(deduped_general)} 条移入整场观感（本区不重复渲染）")

    aud_map = audience_anon.build_audience_map()

    blocks = []
    if groups:
        blocks.append('<h4 style="margin:14px 0 6px;color:#c41e3a;">🎵 按歌曲归类 · 小红书观众评论</h4>')
        blocks.append(
            '<p class="src-note">观众真实反馈摘录，纯文字呈现、无链接；'
            '为保护隐私，昵称以「观众X」匿名呈现（同一编号即同一观众）。</p>'
        )
        for song in sorted(groups):
            lst = groups[song]
            if not lst:
                continue
            lis = "".join(render_quote(x, aud_map) for x in lst)
            blocks.append(f'<p class="song-head">《{esc(song)}》</p><ul class="quote-list">{lis}</ul>')

    section_html = (
        f'\n<div id="{SECTION_ID}" class="audience-section" style="margin-top:14px;border-top:1px dashed #ddd;padding-top:8px;">'
        + "\n".join(blocks) + "\n</div>"
    )

    # 幂等：先删旧分区
    html = HTML.read_text(encoding="utf-8")
    html, n_del = re.subn(rf'<div id="{SECTION_ID}".*?</div>\s*', "", html, flags=re.S)

    # 清理旧平铺小红书条目（旧方案 import_xhs_links 的产物，避免与歌曲分区重复）
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
