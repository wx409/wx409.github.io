# -*- coding: utf-8 -*-
"""10-09 歌曲数按图编号定为 **23**（主口径），展开曲数作为二级口径；10-10 加 pending_caliber 标记。

换算：**23 个编号**（含 2 段串烧）＝ **21 个常规编号 + 2 段串烧**；**按曲展开 = 21 + 6 = 27**
（与 `songs_n`＝28 差 1，原因已查明：10-09 图 No.14《我会找到你》与点歌段 No.21 重复列同一首，
故「编号 23」对应的**唯一曲目**为 27 首）。10-10 无此重复（两处为不同曲目），展开即 28。
用法：python -X utf8 project_b/set_songs_count_23.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
SL9 = D / "show_setlists" / "2026-10-09_北京.json"
SL10 = D / "show_setlists" / "2026-10-10_北京.json"

CONV = ("**换算关系（两套口径）**：主口径 `songs_count` = **23**（图编号：两段串烧各算 1 段、点歌 4 首各占 1 编号）"
        "＝ 21 个常规编号 + 2 段串烧；二级口径 `songs_n`（按曲展开）= 27（10-09，含两段串烧共 6 首；"
        "另 No.14 与点歌 No.21 为同一首《我会找到你》重复列，故唯一曲目 27）／28（10-10，无重复）。")


def main() -> int:
    d9 = json.loads(SL9.read_text(encoding="utf-8"))
    d10 = json.loads(SL10.read_text(encoding="utf-8"))

    # ① 10-09：主口径 23
    d9["songs_count"] = 23
    d9["songs_count_caliber"] = "图编号（串烧各算 1 段）——**用户明确 2026-10-14：10-09 按 23 登记**"
    d9["songs_count_expanded"] = 27
    d9["songs_count_conversion"] = CONV
    d9["songs_count_calc"] = {
        "numbered": 23, "medley_blocks": 2, "regular_numbers": 21,
        "expanded_tracks": 27,
        "why_not_28": "图 No.21（点歌《我会找到你》）与 No.14 为同一首，编号合计 23 但唯一曲目 27",
    }
    n = [x for x in (d9.get("notes") or []) if "歌曲数口径" not in x]
    n.append("★ 歌曲数口径（2026-10-14 用户定案）：**本场 = 23**（图编号；串烧各算 1 段）。"
             + CONV + " 旧文所写「19 段 / 26 曲」系早期 19 段歌单口径，**已作废**（旧结构见 `legacy_segment_list`）。")
    d9["notes"] = n

    # ② 10-10：**暂不动**，只加 pending_caliber
    d10["songs_count"] = 23
    d10["songs_count_pending"] = True
    d10["pending_caliber"] = {
        "issue": "10-10 图上同为 23 个编号（串烧各算 1 段），但用户本轮**只明确 10-09**",
        "current": "已按图登记 `segments_no` = 23、`songs_n` = 28，`songs_count` 暂同 23",
        "ask": "**10-10 是否也按 23 作主口径登记？**（确认后去掉本标记）",
        "does_not_affect": "不涉归属，不影响 songs_subject",
    }
    d10["songs_count_conversion"] = CONV
    d10["songs_count_expanded"] = 28
    SL9.write_text(json.dumps(d9, ensure_ascii=False, indent=1), encoding="utf-8")
    SL10.write_text(json.dumps(d10, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[OK] 10-09 songs_count=23（展开 27）；10-10 songs_count=23 + pending_caliber 标记")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
