"""把本轮补上 mid 的歌曲追加进「收听人数（2026.7.24）.xlsx」

做法：
  1) 与上一个提交对比 songs_compact.json，找出 uid 由 N:/空 → L:mid 的条目
  2) 追加到 Sheet1，列格式与现有行一致（链接列两列相同）
  3) 先备份原文件
"""
import json
import re
import shutil
import subprocess
import time

import openpyxl

XLSX = r"E:\wx\收听人数（2026.7.24）.xlsx"
COMPACT = r"D:\wx409.github.io\tavern\songs_compact.json"
REPO = r"D:\wx409.github.io"

# 1) 取上一个版本的 compact
old_json = subprocess.run(
    ["git", "-C", REPO, "show", "17bf127b:tavern/songs_compact.json"],
    capture_output=True, text=True, encoding="utf-8", errors="ignore").stdout
old = json.loads(old_json)
old_items = old["songs"] if isinstance(old, dict) and "songs" in old else old
old_map = {str(x.get("name")): str(x.get("uid") or "") for x in old_items}

new = json.load(open(COMPACT, encoding="utf-8"))
new_items = new["songs"] if isinstance(new, dict) and "songs" in new else new

filled = []
for x in new_items:
    name, uid = str(x.get("name") or ""), str(x.get("uid") or "")
    if uid.startswith("L:") and not old_map.get(name, "").startswith("L:"):
        filled.append({"name": name, "mid": uid[2:]})
print("本轮新增 mid", len(filled))

# 2) 备份
bak = XLSX.replace(".xlsx", "_备份_%s.xlsx" % time.strftime("%Y%m%d%H%M"))
shutil.copy2(XLSX, bak)
print("备份 →", bak)

# 3) 打开并追加
wb = openpyxl.load_workbook(XLSX)
ws = wb.active
last_row = ws.max_row
last_seq = ws.cell(last_row, 1).value or 0
try:
    seq = int(last_seq)
except Exception:
    seq = last_row - 1

TPL = ("https://y.qq.com/m/client/music_index/index.html?ADTAG=cbshare"
       "&channelId=10036163&mid=%s&openinqqmusic=1&type=%s")

added = 0
for f in sorted(filled, key=lambda x: x["name"]):
    seq += 1
    row = last_row + 1 + added
    full = f["name"].split("\n")[0].strip()
    clean = re.sub(r"[（(].*?[)）]", "", full).strip()
    link = TPL % (f["mid"], f["mid"])
    ws.cell(row, 1, seq)
    ws.cell(row, 2, full)
    ws.cell(row, 3, "王晰")
    ws.cell(row, 4, link)
    ws.cell(row, 5, link)
    ws.cell(row, 6, None)
    ws.cell(row, 7, clean)
    ws.cell(row, 8, "live" if "(Live)" in full else None)
    added += 1

wb.save(XLSX)
print("已追加 %d 行，当前总行数 %d" % (added, ws.max_row))
