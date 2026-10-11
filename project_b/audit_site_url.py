# -*- coding: utf-8 -*-
"""换域回归守卫（**边界**：只扫生成器源码 project_b/*.py 与 tools/*.py ——
生成页天然含 canonical/og:url 域名，那是产物不是硬编码，**禁止改成全站扫描**）。

判定：**fail = 生成器源码里出现 SITE_ALIASES 登记的本站历史域名**（即"还有人写死旧域名"）。
SITE_URL 自身的同值字面量**不算硬编码**（换域时由 apply_site_url.py 统一收口）。
用法：python -X utf8 project_b\\audit_site_url.py   （退出码 1 = 命中历史域名）
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "project_b"))
from site_url import SITE_URL, SITE_ALIASES  # noqa

TARGET = SITE_URL.split("//", 1)[1].strip("/")
ALIASES = {a.split("//", 1)[-1].strip("/") for a in SITE_ALIASES if a}
HOST = re.compile(r"https?://([A-Za-z0-9.\-]+\.[A-Za-z]{2,})")
EXEMPT = {"site_url.py", "audit_site_url.py"}
SCAN_GLOBS = ("project_b/*.py", "tools/*.py")


def main() -> int:
    hits = []
    for g in SCAN_GLOBS:
        for p in sorted(ROOT.glob(g)):
            if not p.is_file() or p.name in EXEMPT:
                continue
            txt = p.read_text(encoding="utf-8", errors="ignore")
            found = {h for h in {m.group(1) for m in HOST.finditer(txt)} if h in ALIASES}
            if found:
                hits.append((p.relative_to(ROOT).as_posix(), sorted(found)))
    print("=" * 60)
    print(f"换域回归守卫：生成器源码中是否写死历史域名（别名表 {sorted(ALIASES) or '空'}）")
    print("=" * 60)
    if not hits:
        print(f"  ✅ 0 命中（同值字面量 {TARGET} 不计为硬编码）")
        return 0
    print(f"  命中 {len(hits)} 个文件：")
    for f, ds in hits[:40]:
        print(f"    {f} × {ds}")
    print("\n结论：生成器写死了历史域名 → fail")
    return 1


if __name__ == "__main__":
    sys.exit(main())
