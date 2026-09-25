# -*- coding: utf-8 -*-
"""曲名清洁度核查：全数据源扫描「canon() 会改写」的名字，量化是否已统一。

判定：对每个数据文件里的**曲名字段/键**取原值 x，若 canon(x) != x → 记为"未净化"。
输出：按文件 × 变体统计 + 合计覆盖率。
退出码：0 = 清洁度 ≥ 99%；1 = 仍有明显未净化项
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from song_names import canon  # noqa: E402

NAME_KEYS = {"song", "title", "name", "song_title", "songtitle", "songname", "曲名", "track"}
LIST_KEYS = {"songs", "song_titles", "titles", "tracks", "songlist", "song_list"}
SKIP = {"song_aliases.json", "song_names.py"}


def walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if isinstance(v, str) and kl in NAME_KEYS:
                yield k, v, f"{path}.{k}"
            elif isinstance(v, list) and kl in LIST_KEYS:
                for i, x in enumerate(v):
                    if isinstance(x, str):
                        yield i, x, f"{path}.{k}[{i}]"
                    else:
                        yield from walk(x, f"{path}.{k}[{i}]")
            else:
                yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            if isinstance(x, dict):
                yield from walk(x, f"{path}[{i}]")


def main() -> int:
    files = [p for p in list(SITE.glob("data/**/*.json")) + list(SITE.glob("*.json"))
             + list(SITE.glob("dashboard/*.json"))
             if ".bak" not in p.name and p.name not in SKIP]
    total = bad = 0
    per_file = defaultdict(Counter)
    for p in files:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for _, val, _ in walk(data):
            total += 1
            c = canon(val)
            if c != val:
                bad += 1
                per_file[str(p.relative_to(SITE))][f"{val} → {c}"] += 1
    rate = 100 * (total - bad) / total if total else 100.0
    print(f"曲名字段总数 {total}｜未净化 {bad}｜**清洁度 {rate:.2f}%**")
    for f, c in sorted(per_file.items(), key=lambda kv: -sum(kv[1].values()))[:12]:
        print(f"  {f}")
        for k, v in c.most_common(4):
            print(f"      {k} × {v}")
    return 0 if rate >= 99.0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
