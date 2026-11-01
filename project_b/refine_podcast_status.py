"""按专辑细分状态 + 把「城市漫行」25 期并入小酒馆音频池"""
import json
import re

import openpyxl

XLSX = r"E:\wx\收听人数（2026.7.24）.xlsx"
POD = json.load(open(r"D:\wx409.github.io\data\podcast_mids.json", encoding="utf-8"))
AUDIO = r"D:\wx409.github.io\data\tavern_audio.json"

pod_map = {p["mid"]: p for p in POD}

wb = openpyxl.load_workbook(XLSX)
ws = wb.active
STATUS = 9
cnt = {"小酒馆": 0, "城市漫行": 0, "其他": 0}
for r in range(2, ws.max_row + 1):
    link = str(ws.cell(r, 4).value or "")
    m = re.search(r"mid=([0-9A-Za-z]+)", link)
    if not m:
        continue
    p = pod_map.get(m.group(1))
    if not p:
        continue
    if "小酒馆" in p["album"]:
        ws.cell(r, STATUS, "播客（小酒馆·在架）")
        cnt["小酒馆"] += 1
    elif "城市漫行" in p["album"]:
        ws.cell(r, STATUS, "播客（城市漫行·在架）")
        cnt["城市漫行"] += 1
    else:
        ws.cell(r, STATUS, "播客（在架）")
        cnt["其他"] += 1
wb.save(XLSX)
print("状态细分：", cnt)

# 并入城市漫行
d = json.load(open(AUDIO, encoding="utf-8"))
items = d["items"]
have = {str(x.get("mid")) for x in items}
added = 0
for p in POD:
    if "城市漫行" not in p["album"] or p["mid"] in have:
        continue
    items.append({"name": p["name"], "mid": p["mid"], "album": p["album"],
                  "duration_sec": None, "episode": (p["name"] or "")[:10],
                  "category": "城市漫行", "theme": ""})
    added += 1
d["count"] = len(items)
json.dump(d, open(AUDIO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("小酒馆音频池 %d 条（新增城市漫行 %d 条）" % (len(items), added))
