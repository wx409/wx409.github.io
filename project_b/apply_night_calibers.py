# -*- coding: utf-8 -*-
"""按用户裁决落库：单晚王晰口径 + 双人曲计数规则 + 曲名归一刷新清单。

裁决（2026-10-14 用户）：
  1 《我会找到你》维持傲日其愣 → 保留在 exclude_for_subject
  2 **另立单晚口径** `songs_subject_by_night`（10-09 / 10-10 各一值），与两晚合并行口径并列
  3 **双人曲与加唱《生日歌》"算两个人的"** → 双人曲同时计入王晰与傲日各自口径
  4 10-09 No.6/No.7 维持「双人」→ 不改
  5 《唱起草原的歌》曲名归一 → 刷新站内产物（只改曲名/键/ID）

产出：`data/performance_attribution.json` 增 `night_calibers`；`data/activity_master.json`
增 `songs_subject_by_night`（单晚）与 `songs_subject`（合并，保留）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

D = Path(r"D:\wx409.github.io\data")
SL9 = D / "show_setlists" / "2026-10-09_北京.json"
SL10 = D / "show_setlists" / "2026-10-10_北京.json"
ATTR = D / "performance_attribution.json"
AM = D / "activity_master.json"

RULE = ("**双人曲与加唱『算两个人的』**（2026-10-14 用户裁决）：双人合唱曲（含加唱《生日歌》）"
        "**同时计入王晰口径与傲日口径**——即 `songs_subject` 保留双人曲；仅「同台嘉宾独唱」"
        "（`exclude_for_subject`）才从王晰口径剔除。")


def night_subject(doc: dict, excl: set) -> dict:
    segs = doc["segment_list"]
    flat = sorted({x for s in segs for x in (s.get("songs") or [])})
    duets = sorted({x for s in segs if s.get("by") == "双人" for x in (s.get("songs") or [])})
    cleared = sorted([x for x in flat if x not in excl])
    return {"n_numbered": doc.get("songs_count_primary") or doc.get("segments_no"),
            "n_expanded": len(flat), "n_duet_songs": len(duets), "n_solo_only_wangxi": len(cleared) - len(duets),
            "subject_n": len(cleared), "subject_songs": cleared, "duet_songs": duets}


def main() -> int:
    a = json.loads(ATTR.read_text(encoding="utf-8"))
    sh = a["shows"][0]
    excl = set(sh["exclude_for_subject"])
    d9 = json.loads(SL9.read_text(encoding="utf-8"))
    d10 = json.loads(SL10.read_text(encoding="utf-8"))
    n9, n10 = night_subject(d9, excl), night_subject(d10, excl)

    sh["night_calibers"] = {
        "what": "**单晚口径**（用户裁决 2026-10-14：另立），与「两晚合并行」口径**并列保留**",
        "counting_rule": RULE,
        "why_need_both": "长表一行＝两晚合并登记；此前只有合并值（勿把合并值当单场）。"
                         "单晚口径用于回答「某一晚王晰唱了哪些/多少」；合并口径用于「这轮演出共覆盖多少」。",
        "by_night": {
            "2026-10-09": n9,
            "2026-10-10": n10,
        },
        "merged_note": "合并值 = 两晚并集去重（见 `activity_master.json` 该行 `songs_subject`）",
    }
    ATTR.write_text(json.dumps(a, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[OK] performance_attribution.night_calibers：10-09 %d 首｜10-10 %d 首（含双人）"
          % (n9["subject_n"], n10["subject_n"]))

    am = json.loads(AM.read_text(encoding="utf-8"))
    for r in am["rows"]:
        if "沉响" not in r.get("title", ""):
            continue
        r["songs_subject_by_night"] = {
            "2026-10-09": {"n": n9["subject_n"], "songs": n9["subject_songs"],
                           "n_duet": n9["n_duet_songs"], "n_solo_only": n9["n_solo_only_wangxi"]},
            "2026-10-10": {"n": n10["subject_n"], "songs": n10["subject_songs"],
                           "n_duet": n10["n_duet_songs"], "n_solo_only": n10["n_solo_only_wangxi"]},
        }
        r["songs_subject_note"] = ("`songs_subject`（%d 首）＝**两晚合并去重**口径；"
                                   "`songs_subject_by_night` ＝**单晚**口径（10-09 %d / 10-10 %d，含双人曲）。"
                                   % (len(r.get("songs_subject") or []), n9["subject_n"], n10["subject_n"])
                                   + RULE)
    AM.write_text(json.dumps(am, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[OK] activity_master.songs_subject_by_night 已写入；合并值 %d"
          % len([r for r in am["rows"] if "沉响" in r.get("title", "")][0].get("songs_subject") or []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
