# -*- coding: utf-8 -*-
"""校验并修正：单晚口径 subject_songs 必须来自**段表的实际曲目**（含双人曲），并核对合并值。"""
import json
from pathlib import Path

D = Path(r"D:\wx409.github.io\data")
d9 = json.loads((D / "show_setlists" / "2026-10-09_北京.json").read_text(encoding="utf-8"))
d10 = json.loads((D / "show_setlists" / "2026-10-10_北京.json").read_text(encoding="utf-8"))
am = json.loads((D / "activity_master.json").read_text(encoding="utf-8"))
row = [r for r in am["rows"] if "沉响" in r["title"]][0]
excl = set(json.loads((D / "performance_attribution.json").read_text(encoding="utf-8"))
           ["shows"][0]["exclude_for_subject"])

for tag, d in (("2026-10-09", d9), ("2026-10-10", d10)):
    segs = d["segment_list"]
    sung = next((s for s in segs if (s.get("song") or "").startswith("点歌")), None)
    point_songs = set(sung.get("songs") or []) if sung else set()
    duet = sorted({x for s in segs if s.get("by") == "双人" for x in (s.get("songs") or [])})
    wangxi = sorted({x for s in segs for x in (s.get("songs") or []) if x not in point_songs or x in duet}
                    - excl)
    print(f"== {tag}: 段表曲目 {len({x for s in segs for x in (s.get('songs') or [])})}｜"
          f"双人 {len(duet)}｜点歌段 {sorted(point_songs)}｜王晰口径 {len(wangxi)}")
    print("   ", wangxi)
    b = row["songs_subject_by_night"][tag]
    b["songs"] = wangxi
    b["n"] = len(wangxi)
    b["n_duet"] = len(duet)
    b["n_solo_only"] = len([x for x in wangxi if x not in duet])
    b["source"] = "由该晚 `segment_list` 去傲日独唱（exclude_for_subject）得到；**点歌段中的王晰独唱已并入**"

# 合并值 = 两晚并集
u = sorted(set(row["songs_subject_by_night"]["2026-10-09"]["songs"]) |
           set(row["songs_subject_by_night"]["2026-10-10"]["songs"]))
row["songs_subject_merged_check"] = {"union_of_nights": len(u), "songs": u,
                                     "matches_longtable_songs_subject": (u == sorted(row["songs_subject"]))}
(D / "activity_master.json").write_text(json.dumps(am, ensure_ascii=False, indent=1), encoding="utf-8")
print("合并校验：两晚并集", len(u), "｜长表 songs_subject", len(row["songs_subject"]),
      "｜一致:", u == sorted(row["songs_subject"]))
print("差集（并集 − 长表）:", sorted(set(u) - set(row["songs_subject"])))
print("差集（长表 − 并集）:", sorted(set(row["songs_subject"]) - set(u)))
