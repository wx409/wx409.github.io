# -*- coding: utf-8 -*-
"""换域回归守卫（**边界**：只扫生成器源码 project_b/*.py 与 tools/*.py——生成页天然含 canonical/og:url 域名，那是产物不是硬编码，**禁止改成全站扫描**）：全站生成产物 grep 硬编码域名，命中即 fail（site_url.py 自身除外）。

为什么：换域应「改一处」（project_b/site_url.py）。历史生成器有约 30 处硬编码
`https://wx409.github.io`，新生成器再写死就会让换域重新变成几十处修改。
用法：python -X utf8 project_b\\audit_site_url.py   （退出码 1 = 存在硬编码）
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOMAIN = "wx409.github.io"
EXEMPT = {"site_url.py", "audit_site_url.py"}
# 只扫「生成器源码」：生成页天然含 canonical/og:url 域名（那是产物，不是硬编码）
SCAN_GLOBS = ("project_b/*.py", "tools/*.py")
SKIP_DIRS = {".git", "node_modules", "temp", "docs", ".dsh", "logs", "assets"}
# 第三方/存档类产物（微博快照等）不在「换域改一处」的范围内
SKIP_SUBSTR = ("live/weibo-snap/", "live/archive/", "chat/")


def main() -> int:
    hits = []
    cand = []
    for g in SCAN_GLOBS:
        cand += sorted(ROOT.glob(g))
    for p in cand:
        if not p.is_file():
            continue
        relposix = p.relative_to(ROOT).as_posix()
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if any(s in relposix for s in SKIP_SUBSTR):
            continue
        if p.name in EXEMPT:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if DOMAIN in txt:
            hits.append((p.relative_to(ROOT).as_posix(), txt.count(DOMAIN)))
    print("=" * 60)
    print("换域回归守卫：硬编码域名扫描（豁免 site_url.py）")
    print("=" * 60)
    if not hits:
        print("  ✅ 未发现硬编码域名")
        return 0
    total = sum(n for _, n in hits)
    print(f"  命中 {len(hits)} 个文件 / 共 {total} 处：")
    for f, n in hits[:40]:
        print(f"    {f} × {n}")
    if len(hits) > 40:
        print(f"    …另有 {len(hits) - 40} 个文件")
    print("\n结论：存在硬编码域名 → fail（换域应只改 project_b/site_url.py）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
