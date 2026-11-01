"""修正状态判定：不在曲库里的 mid，先查 QQ 详情——

  属于播客（专辑含 小酒馆/城市漫行 或名含「(节目)」）→ 标「播客（在架）」
  查不到 → 「已下架（平台无此曲）」
"""
import json
import re
import time
import urllib.request

import openpyxl

XLSX = r"E:\wx\收听人数（2026.7.24）.xlsx"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
CK = open(r"E:\wx\index_records\qqmusic.txt", encoding="utf-8", errors="ignore").read().strip()
H = {"User-Agent": UA, "Referer": "https://y.qq.com/", "Cookie": CK,
     "Content-Type": "application/json"}

POD_ALBUM = ("小酒馆", "城市漫行", "哄你入睡")


def detail(mid):
    payload = {"comm": {"ct": 24, "cv": 0},
               "req": {"module": "music.pf_song_detail_svr", "method": "get_song_detail",
                       "param": {"song_mid": mid}}}
    req = urllib.request.Request("https://u.y.qq.com/cgi-bin/musicu.fcg",
                                 data=json.dumps(payload).encode(), headers=H)
    r = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore"))
    tr = ((r.get("req") or {}).get("data") or {}).get("track_info") or {}
    return {"name": tr.get("name") or "", "album": (tr.get("album") or {}).get("name") or ""}


wb = openpyxl.load_workbook(XLSX)
ws = wb.active
STATUS_COL = 9

changed = {"podcast": 0, "gone": 0}
pods = []
for r in range(2, ws.max_row + 1):
    st = str(ws.cell(r, STATUS_COL).value or "")
    if not st.startswith("已下架"):
        continue
    link = str(ws.cell(r, 4).value or "")
    m = re.search(r"mid=([0-9A-Za-z]+)", link)
    if not m:
        continue
    mid = m.group(1)
    try:
        d = detail(mid)
    except Exception:
        continue
    if d["album"] and any(k in d["album"] for k in POD_ALBUM):
        ws.cell(r, STATUS_COL, "播客（在架）")
        changed["podcast"] += 1
        pods.append({"name": d["name"], "album": d["album"], "mid": mid})
    elif not d["name"]:
        ws.cell(r, STATUS_COL, "已下架（平台无此曲）")
        changed["gone"] += 1
    else:
        ws.cell(r, STATUS_COL, "在架（非曲库）")
    time.sleep(0.25)

wb.save(XLSX)
print("播客 %d ｜ 平台无此曲 %d" % (changed["podcast"], changed["gone"]))
json.dump(pods, open(r"D:\wx409.github.io\data\podcast_mids.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("播客 mid 已存 data/podcast_mids.json（%d 条）" % len(pods))
for p in pods[:5]:
    print("  ", p["album"][:18], "|", p["name"][:34], p["mid"])
