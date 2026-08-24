# -*- coding: utf-8 -*-
"""小红书按链接抓取结果入库：_by_links_summary.json → live_repos.json → live-reviews.html
原则（铁律）：
  - 站内只放「短句+外链可复核」，不存图/视频上站（本地已留存 xhs_archive\按链接\）
  - 用 HTML 级插入，绝不跑 build_live_reviews.py（会冲掉微博条目）
  - 自动跳过：无标题且无 desc 的条目、非巡演相关的
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\wx409.github.io")
SUMMARY = Path(r"E:\wx\私有工具\xhs_archive\_by_links_summary.json")
REPOS_JSON = ROOT / "data" / "live_repos.json"
HTML = ROOT / "live-reviews.html"
SHOW_DATE = "2026-08-23"

# 可入库关键词（内容里含这些才算巡演现场信息）
RELEVANT = ["王晰", "巡演", "广州", "演唱会", "现场", "橄榄树", "Your Man", "情网", "夜色",
            "月半弯", "Yesterday", "像雾像雨", "低音", "合唱", "个巡", "回"]


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def make_title(it):
    """生成入库标题：@作者：内容要点（短句）"""
    title = (it.get("title") or "").strip()
    desc = re.sub(r"\s+", " ", (it.get("desc") or "")).strip()
    text = (title + "。" + desc) if title and desc else (title or desc)
    # 去掉话题标签
    text = re.sub(r"#\S+#", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    author = it.get("author", "")
    short = text[:45] + ("…" if len(text) > 45 else "")
    return f"@{author}：{short}" if author else short


def main():
    if not SUMMARY.exists():
        print("汇总文件不存在"); return
    data = json.loads(SUMMARY.read_text(encoding="utf-8"))
    items = [it for it in data.get("items", []) if it.get("ok")]
    print(f"抓取成功 {len(items)} 条")

    # 筛选相关
    picked = []
    for it in items:
        blob = f"{it.get('title','')} {it.get('desc','')}"
        if any(k in blob for k in RELEVANT):
            picked.append(it)
    print(f"相关内容 {len(picked)} 条")

    # 生成入库条目
    new_items = []
    for it in picked:
        title = make_title(it)
        if not title:
            continue
        link = (it.get("link") or "").split("?")[0]
        new_items.append({
            "title": title,
            "platform": "小红书",
            "url": link,
            "level": "single",
        })

    if not new_items:
        print("无可入库条目"); return

    # 追加 live_repos.json（去重）
    repos = json.loads(REPOS_JSON.read_text(encoding="utf-8"))
    existing = repos["repos"].get(SHOW_DATE, [])
    exist_urls = {r.get("url") for r in existing}
    added = [it for it in new_items if it["url"] not in exist_urls]
    if not added:
        print("全部已存在"); return
    repos["repos"][SHOW_DATE] = existing + added
    REPOS_JSON.write_text(json.dumps(repos, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"live_repos.json 追加 {len(added)} 条小红书")

    # HTML 级插入（绝不重建）
    html = HTML.read_text(encoding="utf-8")
    if "王晰微博" not in html:
        print("!! 页面无微博条目，中止（防止误伤）"); return
    m = re.search(r'(<time datetime="%s"[^>]*>.*?</ul>)' % re.escape(SHOW_DATE), html, re.S)
    if not m:
        print(f"!! 未找到 {SHOW_DATE} 的 </ul>"); return
    segment = m.group(1)
    ul_pos = segment.rfind("</ul>")
    abs_pos = m.start() + ul_pos
    lis = []
    for r in added:
        lis.append(
            f'<li><a href="{esc(r["url"])}" target="_blank" rel="noopener nofollow">{esc(r["title"])}</a> '
            f'<span class="tag">小红书</span> <span class="src-badge single">单源</span></li>'
        )
    block = "\n" + "\n".join(lis) + "\n"
    HTML.write_text(html[:abs_pos] + block + html[abs_pos:], encoding="utf-8")
    print(f"live-reviews.html 已插入 {len(added)} 条小红书（HTML级，未重建）")


if __name__ == "__main__":
    main()
