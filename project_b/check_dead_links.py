# -*- coding: utf-8 -*-
"""死链检查：扫描仓库内所有 HTML 的内链（相对路径/站内绝对路径），报告不存在的目标文件"""
import os
import re
from urllib.parse import urlparse, unquote

ROOT = r"D:\wx409.github.io"
SITE = "https://wx409.github.io"

html_files = []
for root, dirs, files in os.walk(ROOT):
    base = os.path.basename(root)
    if base in (".git", "project_b", "temp", "docs", "node_modules", ".vscode"):
        dirs[:] = []  # 不再深入
        continue
    for f in files:
        if f.endswith(".html"):
            html_files.append(os.path.join(root, f))

broken = []
checked = 0
for hp in html_files:
    rel = os.path.relpath(hp, ROOT).replace("\\", "/")
    with open(hp, encoding="utf-8", errors="ignore") as fh:
        content = fh.read()
    # 收集 href/src 链接
    links = re.findall(r'(?:href|src)="([^"#]+?)(?:#[^"]*)?"', content)
    for link in links:
        if not link or link.startswith(("http://", "https://", "mailto:", "tel:", "javascript:", "data:")):
            continue
        if "'" in link or '"' in link or " + " in link:
            continue  # JS 模板拼接，跳过
        link = link.split("?")[0].split("#")[0]  # 去 query/hash
        if not link:
            continue
        if link.startswith(SITE):
            link = link[len(SITE):]
        # 只处理站内相对/根路径
        if link.startswith("/"):
            target = os.path.normpath(os.path.join(ROOT, link.lstrip("/")))
        else:
            target = os.path.normpath(os.path.join(os.path.dirname(hp), unquote(link)))
        if not target.startswith(ROOT):
            continue
        checked += 1
        if not os.path.exists(target):
            broken.append((rel, link))

print("检查文件数: %d, 链接数: %d" % (len(html_files), checked))
if broken:
    print("死链 %d 条:" % len(broken))
    seen = set()
    for page, link in broken:
        key = (page, link)
        if key in seen:
            continue
        seen.add(key)
        print("  %s -> %s" % (page, link))
else:
    print("无死链")
