#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""导航与内链审计：找出「孤儿页」（全站无任何入口）与「导航不一致」（某些页缺公共入口）。

第一性原理：站点是给人看 + 给 AI 抓的；一个页面若没有任何内链入口，
等于不存在（对搜索引擎和读者都是）。导航一致性是 GEO 的最低要求。
页面清单与导航内容均取自 project_b/build_nav.py（单一事实源），本脚本只做体检。

用法：
  python project_b/audit_nav.py
退出码：0=无问题；1=存在孤儿页或导航漂移。
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project_b"))

from build_nav import NAV_ITEMS, target_pages  # noqa: E402

# 应用页/工作文件：自带布局或无完整 HTML 骨架，不参与导航一致性检查
NAV_CHECK_SKIP_DIRS = {"project_b", "temp", "dashboard", "map"}


def nav_hrefs(html: str) -> list[str]:
    """取页面里 NAV_START 标记或 .nav 区块中的链接"""
    m = re.search(r"<!-- NAV_START -->(.*?)<!-- NAV_END -->", html, re.S)
    if not m:
        m = re.search(r'<div class="nav">(.*?)</div>', html, re.S)
    if not m:
        return []
    return re.findall(r'href="([^"]+)"', m.group(1))


def main() -> None:
    pages = target_pages()
    page_rels = {p.relative_to(ROOT).as_posix() for p in pages}

    hrefs: dict[str, set[str]] = {}
    all_targets: set[str] = set()
    for p in pages:
        html = p.read_text(encoding="utf-8", errors="ignore")
        rel = p.relative_to(ROOT).as_posix()
        hrefs[rel] = set(nav_hrefs(html))
        for h in re.findall(r'href="([^"#?]+)', html):
            all_targets.add(h.strip())

    sitemap = ""
    if (ROOT / "sitemap.xml").exists():
        sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8", errors="ignore")

    print("=" * 68)
    print("导航与内链审计")
    print("=" * 68)

    # 1) 孤儿页
    orphans = []
    for rel in sorted(page_rels):
        if rel.endswith("index.html") and "/" not in rel:
            continue
        cands = {rel, "/" + rel, rel.replace("index.html", ""), "/" + rel.replace("index.html", "")}
        referenced = any(c in all_targets for c in cands)
        in_sitemap = rel in sitemap or ("/" + rel) in sitemap
        if not referenced and not in_sitemap:
            orphans.append(rel)
    print("\n【孤儿页】无任何内链入口且不在 sitemap：")
    print("  无 ✅" if not orphans else "\n".join("  " + o for o in orphans))

    # 2) 导航一致性
    canon = [h for h, _, _ in NAV_ITEMS]
    print("\n【导航不一致】缺少公共入口的页面：")
    problems = 0
    for rel, links in sorted(hrefs.items()):
        if any(rel.startswith(d + "/") for d in NAV_CHECK_SKIP_DIRS):
            continue
        if not links:
            print(f"  {rel}: 无导航区块")
            problems += 1
            continue
        norm = {l.lstrip("./") for l in links}
        # 宽松匹配：允许相对路径（index.html）与绝对路径（/index.html）等价
        missing = [c for c in canon if c not in norm and c.lstrip("/") not in norm]
        if missing:
            print(f"  {rel}: 缺 {', '.join(missing)}")
            problems += 1
    if problems == 0:
        print("  全部一致 ✅")

    print("\n" + "=" * 68)
    print(f"页面数 {len(pages)}｜孤儿页 {len(orphans)}｜导航不一致 {problems}")
    if orphans or problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
