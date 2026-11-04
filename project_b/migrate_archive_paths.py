#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把顶层 story-*.html / share*.html 迁进 /stories/ 与 /share/，旧 URL 留跳转页。

原则
  · 文件用 git mv 迁走（保留历史）；
  · 全站引用改写成新路径（绝对 / 、全 URL、裸相对三种形态都处理）；
  · 旧 URL 保留一个 meta-refresh 跳转页 + canonical 指向新地址 + noindex（过渡期），
    因为 GitHub Pages 不能做 301，只能靠跳转页 + canonical 收敛权重；
  · sitemap 里的旧 URL 直接改成新 URL（跳转页不收录）；
  · 幂等：已经迁过的不再重复处理。

用法（工作目录 D:\\wx409.github.io）：
    python -X utf8 project_b\\migrate_archive_paths.py --dry-run
    python -X utf8 project_b\\migrate_archive_paths.py
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://wx409.github.io"
SITE = BASE + "/"

TEXT_EXT = (".html", ".json", ".js", ".txt", ".md", ".py", ".xml")

# 旧名 → 新相对路径
def build_map() -> dict[str, str]:
    m = {}
    for p in sorted(ROOT.glob("story-*.html")):
        m[p.name] = f"stories/{p.name}"
    for p in sorted(ROOT.glob("share-*.html")):
        m[p.name] = f"share/{p.name}"
    if (ROOT / "share.html").exists():
        m["share.html"] = "share/index.html"
    return m


def tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=str(ROOT), capture_output=True)
    return [ROOT / x.decode("utf-8") for x in out.stdout.split(b"\0") if x]


def rewrite_text(text: str, mapping: dict[str, str], is_root_level: bool) -> str:
    for old, new in mapping.items():
        # 1) 全 URL
        text = text.replace(f"{SITE}{old}", f"{SITE}{new}")
        # 2) 绝对路径
        text = text.replace(f'"/{old}"', f'"/{new}"').replace(f"'/{old}'", f"'/{new}'")
        text = re.sub(r"(?<=href=)/" + re.escape(old) + r"\b", "/" + new, text)
        # 3) 裸相对（只在该文件所在层级能正确解析时替换）
        prefix = "" if is_root_level else "../"
        text = text.replace(f'href="{old}"', f'href="{prefix}{new}"')
        text = text.replace(f"'{old}'", f"'{prefix}{new}'")
        text = text.replace(f'`{old}`', f'`{prefix}{new}`')
    return text


def redirect_stub(old: str, new: str) -> str:
    target = "/" + new
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>页面已迁移</title>
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="{SITE}{new}">
<meta http-equiv="refresh" content="0; url={target}">
<style>body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;padding:40px;line-height:1.8;color:#333}}a{{color:#c41e3a}}</style>
</head>
<body>
<p>本页已迁到新地址：<a href="{target}">{target}</a></p>
<p style="color:#888;font-size:13px">旧链接会自动跳转；如未跳转请点上面的链接。</p>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="story/share 页归档迁移")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    mapping = build_map()
    if not mapping:
        print("没有需要迁移的文件（可能已迁完）")
        return 0
    print(f"待迁移 {len(mapping)} 个文件：")
    for old, new in list(mapping.items())[:5]:
        print(f"  {old} -> {new}")
    if len(mapping) > 5:
        print(f"  … 其余 {len(mapping) - 5} 个")

    if args.dry_run:
        print("dry-run，未改动")
        return 0

    # 1) 建目录并 git mv
    (ROOT / "stories").mkdir(exist_ok=True)
    (ROOT / "share").mkdir(exist_ok=True)
    for old, new in mapping.items():
        dst = ROOT / new
        if dst.exists():
            print(f"  跳过（目标已存在）: {new}")
            continue
        subprocess.run(["git", "mv", old, new], cwd=str(ROOT), check=True)
    print(f"已迁移 {len(mapping)} 个文件")

    # 2) 改写全站引用
    changed = 0
    for f in tracked_files():
        if not f.exists() or f.suffix.lower() not in TEXT_EXT:
            continue
        if f.name in mapping:  # 跳转页/新页内容另外处理
            continue
        try:
            t = f.read_text(encoding="utf-8")
        except Exception:
            continue
        root_level = f.parent == ROOT
        t2 = rewrite_text(t, mapping, root_level)
        if t2 != t:
            f.write_text(t2, encoding="utf-8", newline="")
            changed += 1
    print(f"引用已改写：{changed} 个文件")

    # 3) 旧 URL 跳转页
    n_stub = 0
    for old, new in mapping.items():
        p = ROOT / old
        if not p.exists():
            p.write_text(redirect_stub(old, new), encoding="utf-8", newline="")
            n_stub += 1
    print(f"旧 URL 跳转页：{n_stub} 个")

    # 4) sitemap：旧 URL → 新 URL
    sm = ROOT / "sitemap.xml"
    if sm.exists():
        t = sm.read_text(encoding="utf-8")
        t2 = t
        for old, new in mapping.items():
            t2 = t2.replace(f"{SITE}{old}", f"{SITE}{new}")
        if t2 != t:
            sm.write_text(t2, encoding="utf-8", newline="")
            print("sitemap 已更新")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
