# -*- coding: utf-8 -*-
"""一次性清理公开文件里已有的本机绝对路径（幂等）。

纪律：公开 JSON 不得含本地绝对路径。写入侧的净化在 notify.py（治本）；
本脚本处理存量，并对 calibers/essay_quotes 的 source 字段做同样的净化。

实现要点：**先遍历结构、对字符串值净化，再 json.dumps**——
若先 dumps 再正则，会把转义用的反斜杠一起吃掉，产出非法 JSON（已踩过）。

用法：python -X utf8 project_b/redact_local_paths.py [--check]
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "project_b"))
from notify import redact  # noqa: E402  同一套规则（单一事实源）

TARGETS = ["data/notifications.json", "data/calibers.json", "data/essay_quotes.json"]


def walk(obj):
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, list):
        return [walk(x) for x in obj]
    if isinstance(obj, dict):
        return {k: walk(v) for k, v in obj.items()}
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    dirty = 0
    for rel in TARGETS:
        p = os.path.join(ROOT, rel.replace("/", os.sep))
        if not os.path.exists(p):
            continue
        doc = json.loads(io.open(p, encoding="utf-8").read())
        cur = json.dumps(doc, ensure_ascii=False, indent=1)
        new = json.dumps(walk(doc), ensure_ascii=False, indent=1)
        changed = cur != new
        print("%-30s %s" % (rel, "含本机路径 → 需净化" if changed else "已干净 ✅"))
        if changed:
            dirty += 1
            if not args.check:
                io.open(p, "w", encoding="utf-8").write(new)
    if args.check and dirty:
        print("\n[FAIL] %d 个文件含本机路径" % dirty)
        return 1
    print("\n[OK] 完成（变更 %d 个文件）" % dirty)
    return 0


if __name__ == "__main__":
    sys.exit(main())
