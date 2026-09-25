# -*- coding: utf-8 -*-
"""曲名写法审计：检测数据里的重复/近似曲名，防止统计漏算复发。

检查项：
  ① 指数长表：norm() 相同但写法不同的曲名（如 X / X (Live)）
  ② songs_meta：name 归一化后重复的条目
  ③ 未登记在 data/song_aliases.json 的多写法组
退出码：0 = 无问题；1 = 发现未处理的多写法
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from song_names import canon, norm  # noqa: E402

CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")


def main() -> int:
    # ① 指数长表
    idx = defaultdict(set)
    if CSV.exists():
        with CSV.open(encoding="utf-8-sig", errors="ignore") as f:
            f.readline()
            for line in f:
                p = line.rstrip("\n").split(",")
                if len(p) >= 3:
                    idx[norm(p[1])].add(p[1])
    idx_dups = {k: sorted(v) for k, v in idx.items() if len({canon(x) for x in v}) > 1}

    # ② songs_meta
    meta = json.loads((SITE / "data" / "songs_meta.json").read_text(encoding="utf-8"))
    sm = defaultdict(set)
    for k, v in (meta.get("songs") or {}).items():
        sm[norm((v or {}).get("name") or k)].add((v or {}).get("name") or k)
    sm_dups = {k: sorted(v) for k, v in sm.items() if len(v) > 1}

    # ③ 别名表覆盖
    aliases = json.loads((SITE / "data" / "song_aliases.json").read_text(encoding="utf-8")).get("aliases", {})
    covered = set()
    for cn, al in aliases.items():
        for x in [cn] + list(al):
            covered.add(norm(x))

    missing = {k: v for k, v in idx_dups.items() if k not in covered}

    print(f"① 指数长表多写法组：{len(idx_dups)}（已归并，canon 后同曲）")
    for k, v in list(idx_dups.items())[:6]:
        print(f"    {k}: {v}")
    print(f"② songs_meta 名称重复组：{len(sm_dups)}")
    for k, v in list(sm_dups.items())[:6]:
        print(f"    {k}: {v}")
    print(f"③ 未登记进别名表的多写法：{len(missing)}")
    for k, v in list(missing.items())[:8]:
        print(f"    ⚠ {k}: {v}")

    if missing:
        print("\n[FAIL] 存在未登记的多写法 → 请补 data/song_aliases.json（跑 temp/build_aliases 类脚本或手工登记）")
        return 1
    print("\n[OK] 曲名写法无遗漏（多写法均已归并）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
