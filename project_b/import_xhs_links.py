# -*- coding: utf-8 -*-
"""小红书按链接抓取结果入库 · 纯文字版（方案A：不写id、无链接、≥20字）
============================================================
原则（铁律，2026-08-24 定稿）：
  - 站内**只放纯文字**（`@作者：内容要点`），**不写链接**（小红书无token链接会被
    搜索引擎视为假死链：爬虫/未登录访客一律重定向到 404/登录页，伤害站点信任度）
  - **不写 note_id**（隐私：笔记 id 不应公开）
  - 文字内容要点 **少于 20 字不写入**（弱内容不上站，保持档案质量）
  - 图/视频/全文本地留存 E:/wx/私有工具/xhs_archive/按链接/（不进 git）
  - 绝不跑 build_live_reviews.py（会冲掉微博条目）；小红书条目也不进 live_repos.json
    （否则 build 重建会把它渲染成带链接的 repo）

输入：E:/wx/私有工具/xhs_archive/_by_links_summary.json（fetch_xhs_links.py 生成）
用法：python project_b/import_xhs_links.py
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\wx409.github.io")
SUMMARY = Path(r"E:\wx\私有工具\xhs_archive\_by_links_summary.json")
HTML = ROOT / "live-reviews.html"
SHOW_DATE = "2026-08-23"

# 可入库关键词（内容里含这些才算巡演现场信息）
RELEVANT = ["王晰", "巡演", "广州", "演唱会", "现场", "橄榄树", "Your Man", "情网", "夜色",
            "月半弯", "Yesterday", "像雾像雨", "低音", "合唱", "个巡", "回"]

MIN_TEXT = 20  # 内容要点少于 20 字不写入


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def make_content(it):
    """生成入库正文：@作者：内容要点（去话题标签、压缩空白、限长60）"""
    title = (it.get("title") or "").strip()
    desc = re.sub(r"\s+", " ", (it.get("desc") or "")).strip()
    text = (title + "。" + desc) if title and desc else (title or desc)
    text = re.sub(r"#\S+#", "", text)          # 去话题标签
    text = re.sub(r"\s+", " ", text).strip()    # 压缩空白
    text = re.sub(r"[。．]+$", "", text)         # 去尾部句号
    if len(text) < MIN_TEXT:
        return ""
    author = (it.get("author") or "").strip()
    short = text[:60] + ("…" if len(text) > 60 else "")
    return f"@{author}：{short}" if author else short


def main():
    if not SUMMARY.exists():
        print("汇总文件不存在:", SUMMARY); return
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    items = [it for it in data.get("items", []) if it.get("ok")]
    print(f"抓取成功 {len(items)} 条")

    # 1) 筛选相关 + ≥20字
    picked = []
    for it in items:
        blob = f"{it.get('title','')} {it.get('desc','')}"
        if not any(k in blob for k in RELEVANT):
            continue
        content = make_content(it)
        if not content:
            print(f"  [跳过<{MIN_TEXT}字或无内容] {it.get('title','')[:20]}…")
            continue
        picked.append(content)
    print(f"可入库（相关且≥{MIN_TEXT}字）: {len(picked)} 条")

    if not picked:
        print("无可入库内容")
        return

    # 2) 生成纯文字 <li>（无链接、无 id）
    lis = []
    seen = set()
    for content in picked:
        if content in seen:
            continue
        seen.add(content)
        lis.append(
            f'<li><span title="{esc(content)}">{esc(content)}</span> '
            f'<span class="tag">小红书</span> <span class="src-badge single">单源</span></li>'
        )

    # 3) HTML 级插入（绝不重建）；先清掉该场已有的小红书条目（避免重复）
    html = HTML.read_text(encoding="utf-8")
    if "王晰微博" not in html:
        print("!! 页面无微博条目，中止（防止误伤）"); return

    # 清旧：删「带 xiaohongshu 链接」的 li（旧链接式）与「纯文字版」小红书 li（防重复）。
    # 链接式用 <a href="https://www.xiaohongshu 锚定；纯文字式用 <span title=...> 锚定，
    # 两者都限定在本 li 内（内容不含 <），绝不跨条目吞掉微博。
    m_art = re.search(r'<article.*?<time datetime="%s".*?</article>' % re.escape(SHOW_DATE), html, re.S)
    if not m_art:
        print(f"!! 未找到 {SHOW_DATE} 的 article"); return
    art = m_art.group(0)
    pat_li = re.compile(
        r'<li>(?:<a href="https://www\.xiaohongshu\.com[^"]*"[^>]*>.*?</a>|'
        r'<span title="[^"]*"[^>]*>[^<]*</span>) <span class="tag">小红书</span>.*?</li>\s*',
        re.S)
    new_art, n_removed = pat_li.subn('', art)
    print(f"清理旧小红书条目（链接式+纯文字式）: {n_removed} 条")

    # 4) 在清理后的 new_art 内插入纯文字（插到 </ul> 前，无 ul 则建）
    block = "\n" + "\n".join(lis) + "\n"
    ul_m = re.search(r'</ul>', new_art)
    if ul_m:
        new_art = new_art[:ul_m.start()] + block + new_art[ul_m.start():]
    else:
        new_art = new_art.replace('</article>', '<ul class="repo-list">' + block + '</ul>\n</article>', 1)

    # 用 new_art 替换 html 里的旧 article
    html = html[:m_art.start()] + new_art + html[m_art.end():]

    HTML.write_text(html, encoding="utf-8")
    print(f"live-reviews.html 已写入 {len(lis)} 条小红书纯文字（无链接/无id，未重建）")


if __name__ == "__main__":
    main()
