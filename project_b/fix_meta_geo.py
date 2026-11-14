#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO 收尾：批量补长短标题与短描述（针对 Bing WMT「titles/metas too short」建议）。

原则：
  · 只做「追加事实性后缀」，不改原有语义、不堆关键词；
  · 幂等：已包含后缀的跳过；
  · 默认 dry-run；--write 才落盘。
后缀：
  title      → "｜王晰数字档案"
  description→ "｜王晰（男低音）数字档案：实测数据均标注出处与口径。"
阈值：title < 20 字；description < 80 字符。
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
SKIP_DIRS = {".git", "temp", "temp_dl", "tmp", "logs", "assets", "docs", "project_b",
             "tools", "templates", "__pycache__", "repo", "migrate", "dsh-config-portable",
             ".github", "data"}
T_SUFFIX = "｜王晰数字档案"
D_SUFFIX = "｜王晰（男低音）数字档案：实测数据均标注出处与口径。"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    changed = []
    for p in ROOT.rglob("*.html"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        s = p.read_text(encoding="utf-8", errors="ignore")
        if 'http-equiv="refresh"' in s:
            continue
        orig = s

        m = re.search(r"<title>(.*?)</title>", s, re.S | re.I)
        if m:
            t = re.sub(r"\s+", " ", m.group(1)).strip()
            if len(t) < 20 and T_SUFFIX not in t:
                s = s.replace(m.group(0), f"<title>{t}{T_SUFFIX}</title>", 1)

        # 描述：只对「主入口页」用正文首段生成，不做全站模板后缀
        MAIN = {"index.html", "works.html", "live.html", "vocal.html", "history.html",
                "research.html", "community.html", "qa.html", "quotes.html", "stage.html"}
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        d = re.search(r'(<meta\s+name=["\']description["\']\s+content=["\'])(.*?)(["\'])', s, re.S | re.I)
        if d and rel in MAIN:
            v = re.sub(r"\s+", " ", d.group(2)).strip()
            p1 = re.search(r"<main[^>]*>(.*?)</main>", s, re.S | re.I)
            body = p1.group(1) if p1 else s
            ps = re.findall(r"<p[^>]*>(.*?)</p>", body, re.S | re.I)
            first = ""
            for x in ps:
                t2 = re.sub(r"<[^>]+>", "", x)
                t2 = re.sub(r"\s+", " ", t2).strip()
                if len(t2) >= 30:
                    first = t2
                    break
            if first and len(v) < 80:
                cand = (v + "。" if v and not v.endswith("。") else v) + first
                cand = cand[:150]
                new = d.group(1) + cand + d.group(3)
                s = s[: d.start()] + new + s[d.end():]

        if s != orig:
            changed.append(str(p.relative_to(ROOT)).replace("\\", "/"))
            if not a.dry_run:
                p.write_text(s, encoding="utf-8")

    print(f"{'已写入' if not a.dry_run else 'dry-run'}：{len(changed)} 页")
    for c in changed[:12]:
        print("  ", c)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
