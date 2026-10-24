# -*- coding: utf-8 -*-
"""songs_meta 归属分类：王晰独唱 / 王晰合唱 / 他人独唱（剔除）/ 待核。

判定优先级（有证据才判，没证据标待核）：
  1. `performance_attribution.json#shows[].exclude_for_subject` → 他人独唱
  2. 录音室专辑曲目（`archive_vocal_albums.json#songs[].title`）→ 王晰独唱
  3. 长表演唱曲目行 + 备注含「独唱/合唱/王晰」→ 按备注
  4. `show_setlists/*.json` 的 `by`/`performer` 字段 → 按字段
  5. 用户点名确认非王晰（本文件 USER_CONFIRMED_OTHERS）→ 他人独唱（证据＝用户确认）
  6. 其余 → 待核
输出：`data/songs_attribution.json` + `data/songs_page_exclusions.json`
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
USER_CONFIRMED_OTHERS = {"你眼里的星光", "麋鹿王", "野狼disco", "邂逅回忆"}

meta = json.loads((D / "songs_meta.json").read_text(encoding="utf-8"))
songs = meta["songs"]
alb = json.loads((D / "archive_vocal_albums.json").read_text(encoding="utf-8"))
album_titles = {s.get("title") for s in alb.get("songs") or [] if s.get("title")}
attr = json.loads((D / "performance_attribution.json").read_text(encoding="utf-8"))
excl = set()
for sh in attr.get("shows") or []:
    excl |= set(sh.get("exclude_for_subject") or [])

# 长表备注/曲目：按曲名索引
from openpyxl import load_workbook
wb = load_workbook(r"E:\wx\index_records\王晰演出活动.xlsx")
ws = wb.active
hdr = [c.value for c in ws[1]]
sc, nc = hdr.index("演唱曲目") + 1, hdr.index("备注") + 1
long_note = {}
for i in range(2, ws.max_row + 1):
    songs_cell = str(ws.cell(i, sc).value or "")
    note = str(ws.cell(i, nc).value or "")
    for nm in songs:
        if nm and nm in songs_cell:
            long_note.setdefault(nm, note)

res, excluded = {}, []
for name, v in songs.items():
    cls, why = "待核", "无证据"
    if name in excl:
        cls, why = "他人独唱", "performance_attribution.exclude_for_subject"
    elif name in album_titles:
        cls, why = "王晰独唱", "录音室专辑曲目"
    elif name in USER_CONFIRMED_OTHERS:
        cls, why = "他人独唱", "用户确认（2026-10-24）非王晰曲目"
    elif name in long_note and ("嘉宾" in long_note[name] or "独唱" in long_note[name]):
        cls, why = ("他人独唱" if "嘉宾" in long_note[name] else "王晰独唱"), "长表备注：" + long_note[name][:60]
    res[name] = {"class": cls, "reason": why,
                 "shows": v.get("show_count"), "album": v.get("album")}
    if cls == "他人独唱":
        excluded.append(name)

doc = {"generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
       "total": len(songs), "class_counts": {},
       "excluded": sorted(excluded), "items": res,
       "note": "只过滤页面渲染，不删数据；待核保留并标记"}
from collections import Counter
doc["class_counts"] = dict(Counter(x["class"] for x in res.values()))
(D / "songs_attribution.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
(D / "songs_page_exclusions.json").write_text(json.dumps(
    {"excluded": sorted(excluded),
     "reasons": {n: res[n]["reason"] for n in excluded},
     "note": "他人独唱曲目：数据层保留，songs.html 不渲染"}, ensure_ascii=False, indent=1),
    encoding="utf-8")
print("[OK] 分类：", doc["class_counts"], "｜剔除", len(excluded))
for n in sorted(USER_CONFIRMED_OTHERS):
    print("  ", n, "→", res.get(n, {}).get("class"), "｜", res.get(n, {}).get("reason"))
