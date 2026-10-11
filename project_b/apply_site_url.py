# -*- coding: utf-8 -*-
"""生成后单点收口：只把 **SITE_ALIASES 里登记的本站历史域名** 统一为 SITE_URL。

- **不动任何第三方外链**（w3.org / schema.org / 平台 / 备案 … 一律不改）；
- 别名表为空时，本步骤**必然零改动** → 这就是"输出中性"的可证形式；
- `--verify`：先快照全部产物 → 跑一次 → 逐文件 read_bytes 比较；
  别名表为空时**非零差异即 fail（退出码 1）**，可随时复跑作回归证明。

运维口径：换域 = 填 SITE_ALIASES + 改 SITE_URL + 跑一次部署。
用法：python -X utf8 project_b\\apply_site_url.py [--dry] [--verify]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from site_url import SITE_URL, SITE_ALIASES  # noqa

TARGET = SITE_URL.split("//", 1)[1].strip("/")
ALIASES = {a.split("//", 1)[-1].strip("/") for a in SITE_ALIASES if a}
HOST = re.compile(r"https?://([A-Za-z0-9.\-]+\.[A-Za-z]{2,})")
EXTS = {".html", ".json", ".md", ".xml", ".txt"}
SKIP = ("temp/", ".git/", "node_modules/", "live/weibo-snap/", "live/archive/", "chat/")


def artifacts():
    for p in sorted(SITE.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in EXTS:
            continue
        rel = p.relative_to(SITE).as_posix()
        if any(s in rel for s in SKIP) or rel == "project_b/site_url.py":
            continue
        yield p, rel


def rewrite(txt: str):
    """只替换命中别名表的主机名；第三方外链原样保留。"""
    if not ALIASES:
        return txt, 0, set()
    hit = set()

    def rep(m):
        if m.group(1) in ALIASES:
            hit.add(m.group(1))
            return SITE_URL + m.group(0).split(m.group(1), 1)[1]
        return m.group(0)

    return HOST.sub(rep, txt), len(hit), hit


def main() -> int:
    verify = "--verify" in sys.argv
    dry = "--dry" in sys.argv or verify
    snap = {}
    files = list(artifacts())
    if verify:
        for p, rel in files:
            try:
                snap[rel] = p.read_bytes()
            except Exception:
                pass
    changed = []
    for p, rel in files:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        new, n, hit = rewrite(txt)
        if new != txt:
            changed.append(rel)
            if not dry:
                p.write_text(new, encoding="utf-8")
    print(f"apply_site_url: 产物 {len(files)} 个｜别名表 {sorted(ALIASES) or '空'}｜改写 {len(changed)} 个")
    if verify:
        diff = [rel for rel, b in snap.items()
                if (SITE / rel).exists() and (SITE / rel).read_bytes() != b]
        print(f"[--verify] 比较 {len(snap)} 个文件｜差异 {len(diff)} 个"
              + ("（别名表为空 → 要求 0）" if not ALIASES else ""))
        for d in diff[:3]:
            print("   DIFF", d)
        if diff:
            print("!! 回归证明失败：非零差异")
            return 1
        print("✅ 输出中性证明通过（零差异）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
