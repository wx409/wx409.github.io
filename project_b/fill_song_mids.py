"""用「收听人数（2026.7.24）.xlsx」里的 mid，补齐曲库缺失的歌曲 ID

来源列：ngrid_链接 中的 `mid=XXXXXXXX`
目标：
  1) data/songs_meta.json 的 mid 字段（No mid / N: 前缀 → 真 mid）
  2) dashboard/dashboard_data.json 的 song_index[].uid（N: → 真 mid）
  3) tavern/songs_compact.json 的 uid
输出：报告被补全多少、仍缺多少
"""
import json
import re
from collections import Counter

import pandas as pd

XLSX = r"E:\wx\收听人数（2026.7.24）.xlsx"
META = r"D:\wx409.github.io\data\songs_meta.json"
DASH = r"D:\wx409.github.io\dashboard\dashboard_data.json"
COMPACT = r"D:\wx409.github.io\tavern\songs_compact.json"


def norm(s):
    s = str(s or "")
    s = re.sub(r"[（(].*?[)）]", "", s)              # 去括号（Live）等
    s = s.replace("王晰", "").replace("/", "").replace("、", "")
    return re.sub(r"[\s《》「」·・,，.。'\"-]", "", s).lower()


# 1) 读表建映射
df = pd.read_excel(XLSX, sheet_name=0)
mp = {}
for _, r in df.iterrows():
    name = r.get("歌曲名称")
    link = str(r.get("ngrid_链接") or "")
    m = re.search(r"[?&]mid=([0-9A-Za-z]+)", link)
    if not m:
        continue
    mid = m.group(1)
    if name and mid:
        mp.setdefault(norm(name), mid)

print("表内可解析 mid", len(mp))

# 2) 补 songs_meta
meta = json.load(open(META, encoding="utf-8"))
songs = meta["songs"]
songs = songs if isinstance(songs, list) else list(songs.values())
filled_meta = 0
for s in songs:
    mid = str(s.get("mid") or "")
    if mid.startswith("L:") or (mid and not mid.startswith(("No", "N:"))):
        continue
    hit = mp.get(norm(s.get("name")))
    if hit:
        s["mid"] = "L:" + hit
        filled_meta += 1
json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("songs_meta 补全", filled_meta)

# 3) 补 dashboard song_index
dash = json.load(open(DASH, encoding="utf-8"))
filled_dash = 0
for it in dash.get("song_index") or []:
    uid = str(it.get("uid") or "")
    if uid.startswith("L:"):
        continue
    hit = mp.get(norm(it.get("name")))
    if hit:
        it["uid"] = "L:" + hit
        filled_dash += 1
json.dump(dash, open(DASH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("dashboard 补全", filled_dash)

# 4) 补 songs_compact
comp = json.load(open(COMPACT, encoding="utf-8"))
items = comp["songs"] if isinstance(comp, dict) and "songs" in comp else comp
filled_comp = 0
for it in items:
    uid = str(it.get("uid") or "")
    if uid.startswith("L:"):
        continue
    hit = mp.get(norm(it.get("name")))
    if hit:
        it["uid"] = "L:" + hit
        filled_comp += 1
json.dump(comp, open(COMPACT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("songs_compact 补全", filled_comp)

# 5) 复查
comp2 = json.load(open(COMPACT, encoding="utf-8"))
items2 = comp2["songs"] if isinstance(comp2, dict) and "songs" in comp2 else comp2
print("剩余不可播:", sum(1 for x in items2 if not str(x.get("uid", "")).startswith("L:")))
