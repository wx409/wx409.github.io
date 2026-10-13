# -*- coding: utf-8 -*-
"""origin 同步巡检（防"部署只 commit 不 push"造成的静默积压）。

判定：`git status -sb` 出现 `ahead`/`behind` → 自动 `git push origin main` → 复查；
仍不一致 → **红灯 exit 1**（push 失败不得静默）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent


def run(*a):
    return subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8",
                          errors="ignore", cwd=str(SITE))


def sb():
    return run("git", "status", "-sb").stdout.strip()


def main() -> int:
    s = sb()
    first = s.splitlines()[0] if s else ""
    print("  git status -sb:", first)
    if "ahead" not in first and "behind" not in first:
        print("  ✅ 与 origin 同步")
        return 0
    print("  ⚠ 与 origin 不一致 → 自动 push")
    p = run("git", "push", "origin", "main")
    print("  push rc=", p.returncode, ((p.stdout or "") + (p.stderr or "")).strip().splitlines()[-1][:120]
          if ((p.stdout or "") + (p.stderr or "")).strip() else "")
    s2 = sb().splitlines()[0]
    print("  复查:", s2)
    if "ahead" in s2 or "behind" in s2:
        print("  ✗ 仍与 origin 不一致 → 红灯")
        return 1
    print("  ✅ push 后已同步")
    return 0


if __name__ == "__main__":
    sys.exit(main())
