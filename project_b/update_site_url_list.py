# -*- coding: utf-8 -*-
"""update_site_url_list.py —— 把 sitemap 全量页面写入网页列表 Excel（新增/取消标注）"""
import re
import shutil
from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.styles import Font

ROOT = Path(r"D:\wx409.github.io")
XL = Path(r"E:\wx\index_records\wx.github.io网页列表.xlsx")
SITE = "https://wx409.github.io/"

sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
current = re.findall(r"<loc>(.*?)</loc>", sitemap)
current = [u.replace("&amp;", "&") for u in current]

wb = openpyxl.load_workbook(XL)
old = set()
for ws in wb.worksheets:
    for row in ws.iter_rows(values_only=True):
        for v in row:
            if isinstance(v, str) and v.startswith("http"):
                old.add(v.strip())

def title_of(url):
    rel = url[len(SITE):] if url.startswith(SITE) else ""
    if not rel or rel.endswith("/"):
        rel = (rel + "index.html").lstrip("/")
    p = ROOT / rel.split("?")[0]
    if p.exists() and p.suffix == ".html":
        m = re.search(r"<title>(.*?)</title>", p.read_text(encoding="utf-8", errors="ignore"), re.S)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()[:80]
    return ""

name = "全站清单_20261122"
if name in wb.sheetnames:
    del wb[name]
ws = wb.create_sheet(name, 0)
ws.append(["URL", "标题", "状态", "备注", "更新时间"])
ws["A1"].font = ws["B1"].font = ws["C1"].font = ws["D1"].font = ws["E1"].font = Font(bold=True)
today = date.today().isoformat()
seen = set()
for u in current:
    if u in seen:
        continue
    seen.add(u)
    ws.append([u, title_of(u), "启用" if u in old else "新增", "", today])
def exists(u):
    rel = u[len(SITE):] if u.startswith(SITE) else ""
    if not rel:
        return (ROOT / "index.html").exists()
    if rel.endswith("/"):
        rel = rel + "index.html"
    p = ROOT / rel.split("?")[0]
    return p.exists()

for u in sorted(old - set(current)):
    if exists(u):
        ws.append([u, title_of(u), "启用（未入 sitemap）", "页面存在，但未列入 sitemap", today])
    else:
        ws.append([u, "", "取消", "旧清单有、页面已不存在", today])
ws.freeze_panes = "A2"
for col, w in zip("ABCDE", [62, 44, 10, 28, 12]):
    ws.column_dimensions[col].width = w
backup = XL.with_name(XL.stem + "_bak.xlsx")
shutil.copy2(XL, backup)
wb.save(XL)
print("current", len(seen), "old", len(old), "cancelled", len(old - set(current)), "→", name)
