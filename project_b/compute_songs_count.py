# -*- coding: utf-8 -*-
"""实算两晚「节目编号 / 歌曲总数（展开口径）」并写入 show_setlists（**先算准再写**）。

算式（用户给的口径）：歌曲总数 = 编号数 − 串烧槽位数 + 串烧成员曲数 −（重复列的曲目去重）
  10-09：23 − 2 + 6 = 27，再按实际去重（No.14《我会找到你》与点歌 No.21 同一首）→ 以去重后为准
  10-10：23 − 2 + 6 = 27，另「加唱《生日歌》」单列 → 含加唱 / 不含加唱两个数
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

D = Path(r"D:\wx409.github.io\data")
SL9 = D / "show_setlists" / "2026-10-09_北京.json"
SL10 = D / "show_setlists" / "2026-10-10_北京.json"


def calc(doc: dict) -> dict:
    segs = doc["segment_list"]
    medley_slots = [s for s in segs if len(s.get("songs") or []) > 1]
    members = sum(len(s.get("songs") or []) for s in medley_slots)
    numbered = len(segs)
    linear = numbered - len(medley_slots) + members          # 用户给的算式
    flat = [x for s in segs for x in (s.get("songs") or [])]
    dup = [k for k, v in Counter(flat).items() if v > 1]
    unique = len(set(flat))
    encore = (doc.get("point_song_segment") or {}).get("encore_extra") or []
    enc_names = [e.get("song") for e in encore if e.get("song")]
    return {"numbered": numbered, "medley_slots": len(medley_slots), "medley_members": members,
            "linear": linear, "flat": len(flat), "unique": unique, "dup": dup,
            "encore": enc_names, "with_encore": unique + len([x for x in enc_names if x not in flat])}


def main() -> int:
    d9 = json.loads(SL9.read_text(encoding="utf-8"))
    d10 = json.loads(SL10.read_text(encoding="utf-8"))
    c9, c10 = calc(d9), calc(d10)
    print("10-09:", json.dumps(c9, ensure_ascii=False))
    print("10-10:", json.dumps(c10, ensure_ascii=False))

    conv9 = (f"节目编号 {c9['numbered']}（两段串烧各算 1 条、点歌 4 首各占 1 号）｜实际歌曲 "
             f"{c9['unique']} 首（含 2 段串烧共 {c9['medley_members']} 首；"
             f"算式 {c9['numbered']} − {c9['medley_slots']} + {c9['medley_members']} = {c9['linear']}，"
             f"再按去重：{('、'.join(c9['dup']) or '无')} 重复列 → **{c9['unique']} 首**）")
    conv10 = (f"节目编号 {c10['numbered']}｜实际歌曲 {c10['unique']} 首"
              f"（含 2 段串烧共 {c10['medley_members']} 首；算式 {c10['numbered']} − {c10['medley_slots']} "
              f"+ {c10['medley_members']} = {c10['linear']}，去重后 {c10['unique']}）"
              f"，另**加唱《{'、'.join(c10['encore'])}》** → 含加唱 {c10['with_encore']} 首")

    for d, c, conv in ((d9, c9, conv9), (d10, c10, conv10)):
        d["segments_no"] = c["numbered"]
        d["songs_count"] = c["numbered"]                       # 用户要的「歌曲总数」但明确按 23 登记 → 另立字段
        d["songs_count_primary"] = c["numbered"]               # 主口径（节目编号）
        d["songs_count_total"] = c["unique"]                   # 展开口径（去重后）
        d["songs_count_total_linear"] = c["linear"]            # 用户算式结果（未去重）
        d["songs_count_dup"] = c["dup"]
        if c["encore"]:
            d["songs_count_total_with_encore"] = c["with_encore"]
            d["songs_count_total_without_encore"] = c["unique"]
            d["songs_count_recommended_display"] = c["with_encore"]
        else:
            d["songs_count_recommended_display"] = c["unique"]
        d["songs_count_conversion"] = conv
        d["songs_count_note"] = ("**两栏并列展示**：`节目编号 23`｜`实际歌曲 N（含 2 段串烧共 6 首"
                                 + ("，另加唱《生日歌》" if c["encore"] else "") + "）`；换算式同列，"
                                 "避免读者把「编号数」误读成「只唱了 23 首」。")
        d["segments"] = c["numbered"]
        d["songs_n"] = c["unique"]
    d10.pop("songs_count_pending", None)
    d10["pending_caliber"] = {"issue": "10-10 是否也按 23 登记", "status": "**已确认（用户 2026-10-14：也按 23）**",
                              "resolved": True}
    for d in (d9, d10):
        d["notes"] = [x for x in (d.get("notes") or []) if "歌曲数口径" not in x]
        d["notes"].append("★ 歌曲数口径（2026-10-14 用户定案）：" + d["songs_count_conversion"]
                          + "。旧文「19 段 / 26 曲」已作废（旧结构见 `legacy_segment_list`）。")
    SL9.write_text(json.dumps(d9, ensure_ascii=False, indent=1), encoding="utf-8")
    SL10.write_text(json.dumps(d10, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[OK] 两晚已写入 songs_count_primary=23 / songs_count_total（去重后）与换算式")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
