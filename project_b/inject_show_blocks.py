# -*- coding: utf-8 -*-
"""把「双人场次块级」数据注入 data/archive_stage_tour.json（幂等）。

为什么用注入而不是直接写进生成器：`archive_stage_tour.json` 由
`音域分析/轨迹/生成巡演现场报告.py` 全量重写（按 tag 正则只认「六巡广州20260823…」这类命名），
本场素材是「块级、无曲名」，不适配该正则。因此改为：
  data/show_blocks/*.json（人工可维护的单一事实源）
    → 本脚本合并为 archive_stage_tour.json 的顶层键 `show_blocks` + `show_blocks_meta`
**注意**：任何一次重跑 生成巡演现场报告.py 之后，需再跑一次本脚本（已登记进 docs 方法论备忘）。

用法：python -X utf8 project_b\\inject_show_blocks.py
"""
from __future__ import annotations

import io
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = Path(r"D:\wx409.github.io")
TARGET = ROOT / "data" / "archive_stage_tour.json"
SRC_DIR = ROOT / "data" / "show_blocks"


def main() -> int:
    items = []
    for p in sorted(SRC_DIR.glob("*.json")):
        try:
            items.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"!! 跳过 {p.name}: {e}")
    if not items:
        print("!! data/show_blocks/ 下没有可用数据")
        return 1
    t = json.loads(TARGET.read_text(encoding="utf-8"))
    t["show_blocks"] = items
    t["show_blocks_meta"] = {
        "count": len(items),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "caliber": "场次音频切分与歌手归属",
        "note": "双人场次块级数据；**不含极值音/音域主张**。"
                "重跑 生成巡演现场报告.py 后需重跑本项目 注入脚本。",
        "source": "data/show_blocks/*.json",
    }
    TARGET.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] 注入 {len(items)} 场 → {TARGET.relative_to(ROOT)}（顶层键 show_blocks）")
    for it in items:
        print(f"   {it['show']['name']} {it['show']['date']}｜块 {len(it['blocks'])}"
              f"（进统计 {sum(1 for b in it['blocks'] if b['in_stats'])}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
