# -*- coding: utf-8 -*-
"""给 data/song_aliases.json 加《岩缝中开出的花》别名（岩峰中开出的花 = 旧写法）。

依据：B站全程 BV1Mypv6zECb p28 标题作「岩缝中开出的花」；既往站内/素材多处作
「岩峰中开出的花」→ 统一到 BV/图源写法，防统计拆成两首。幂等。
用法：python -X utf8 project_b/patch_alias_yanfeng.py [--apply]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

P = Path(r"D:\wx409.github.io\data\song_aliases.json")
CANON = "岩缝中开出的花"
OLD = "岩峰中开出的花"


def main() -> int:
    apply = "--apply" in sys.argv
    d = json.loads(P.read_text(encoding="utf-8"))
    al = d.setdefault("aliases", {})
    cur = al.get(CANON, [])
    if OLD in cur:
        print("[=] 别名已存在：%s → %s" % (OLD, CANON))
    else:
        al[CANON] = sorted(set(cur + [OLD]))
        print("[别名] %s → %s（+%s）" % (OLD, CANON, OLD))
    d["generated_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    if apply:
        P.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[写入]", P)
    else:
        print("（试算，未写盘；加 --apply 落地）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
