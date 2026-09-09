# -*- coding: utf-8 -*-
"""sitemap.xml lastmod 自动回填（部署链自动执行，禁手写日期）

口径（单一事实源 = git）：
  1. 工作区有改动的页面  → lastmod = 今天（本次提交后即为提交日）
  2. 无改动但 git 有记录 → lastmod = 该文件最后一次提交日期（%cs）
  3. 两者都取不到        → 保留原值（只增不减，绝不让 lastmod 倒退）

用法：
  python -X utf8 project_b/update_sitemap_lastmod.py           # 写入
  python -X utf8 project_b/update_sitemap_lastmod.py --dry     # 只打印差异
  python -X utf8 project_b/update_sitemap_lastmod.py --check   # 有落后即 exit 1（审计用）
"""
from __future__ import annotations

import io
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SITEMAP = ROOT / "sitemap.xml"
BASE = "https://wx409.github.io/"
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
TODAY = date.today().isoformat()


def git(args: list[str]) -> str:
    """在仓库根执行 git，失败返回空串（沙箱无 git 时不阻塞部署）。"""
    try:
        r = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True, timeout=60)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def loc_to_path(loc: str) -> Path | None:
    """URL → 仓库内文件路径（站内相对 URL 才映射，外链返回 None）。"""
    if not loc.startswith(BASE):
        return None
    rel = loc[len(BASE):]
    rel = rel.split("#")[0].split("?")[0]
    rel = unquote(rel)          # 中文页面的 URL 是百分号编码，需还原成真实文件名
    if rel == "" or rel.endswith("/"):
        rel += "index.html"
    p = ROOT / rel
    return p


def build_date_map() -> tuple[dict[str, str], set[str]]:
    """返回 (路径→最后提交日, 工作区有改动的路径集合)。"""
    dates: dict[str, str] = {}
    dirty: set[str] = set()

    for line in git(["status", "--porcelain"]).splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:  # 重命名
            path = path.split(" -> ")[-1]
        dirty.add(path.replace("\\", "/"))

    # 一次拿到全部页面的最后提交日：git log --name-only 全历史可能很大，故只取最近 4000 次提交
    cur = ""
    for line in git(["log", "--format=%x01%cs", "--name-only", "-n", "4000"]).splitlines():
        if line.startswith("\x01"):
            cur = line[1:].strip()
        elif line.strip():
            key = line.strip().replace("\\", "/")
            if key not in dates:      # log 由新到旧，首次出现即为最新
                dates[key] = cur
    return dates, dirty


def main() -> int:
    dry = "--dry" in sys.argv
    check = "--check" in sys.argv

    if not SITEMAP.exists():
        print("[sitemap] 缺少 sitemap.xml，跳过")
        return 0

    text = io.open(SITEMAP, encoding="utf-8").read()
    tree = ET.fromstring(text)
    dates, dirty = build_date_map()

    changed: list[tuple[str, str, str]] = []
    missing: list[str] = []
    for url in tree.findall("sm:url", NS):
        loc = (url.findtext("sm:loc", default="", namespaces=NS) or "").strip()
        lm = url.find("sm:lastmod", NS)
        if lm is None or not loc:
            continue
        path = loc_to_path(loc)
        if path is None:
            continue
        rel = str(path.relative_to(ROOT)).replace("\\", "/")
        if not path.exists():
            missing.append(rel)
            continue
        if rel in dirty:
            new = TODAY
        else:
            new = dates.get(rel, "")
        old = (lm.text or "").strip()
        if new and new > old:
            changed.append((loc, old, new))
            if not dry and not check:
                lm.text = new

    # ---- 补全遗漏页：顶层 HTML 若不在 sitemap 中则自动登记（stage.html 曾漏登记）----
    have = {(u.findtext("sm:loc", default="", namespaces=NS) or "").strip()
            for u in tree.findall("sm:url", NS)}
    added: list[str] = []
    for page in sorted(ROOT.glob("*.html")):
        if page.name in ("live_template.html", "404.html", "index.html"):  # 首页的规范 URL 是根路径 /
            continue
        loc = BASE + page.name
        if loc in have:
            continue
        rel = page.name
        lm = TODAY if rel in dirty else dates.get(rel, TODAY)
        entry = (f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lm}</lastmod>\n"
                 f"    <changefreq>weekly</changefreq>\n    <priority>0.6</priority>\n  </url>\n")
        added.append(loc)
        if not dry and not check:
            text = text.replace("</urlset>", entry + "</urlset>")

    if (changed or added) and not dry and not check:
        # 保持原始排版：按行回填（正则容忍 LF/CRLF 混排），最小化 diff
        for loc, old, new in changed:
            text = re.sub(
                r"(<loc>" + re.escape(loc) + r"</loc>\s*<lastmod>)" + re.escape(old) + r"(</lastmod>)",
                lambda m: m.group(1) + new + m.group(2),
                text,
            )
        io.open(SITEMAP, "w", encoding="utf-8", newline="").write(text)

    print(f"[sitemap] 共 {len(tree.findall('sm:url', NS))} 条 URL，本次回填 {len(changed)} 条")
    if added:
        print(f"[sitemap] 补登记遗漏页 {len(added)} 个：")
        for loc in added:
            print(f"  + {loc}")
    for loc, old, new in changed[:20]:
        print(f"  {loc} : {old} -> {new}")
    if len(changed) > 20:
        print(f"  …另有 {len(changed) - 20} 条")
    if missing:
        print(f"  [警告] sitemap 指向但仓库内不存在：{', '.join(missing[:5])}")

    if check and changed:
        print(f"[sitemap] FAIL：{len(changed)} 条 lastmod 落后于 git 记录")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
