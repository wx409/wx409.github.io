"""导入六爻库整本歌词（55 首）→ 切成短句入词句库（仅内部、短句引用）

规则：
  - 按【歌名】分段
  - 一行一句；跳过语气行、重复行、过短（<8）过长（>34）
  - 去重（全库范围内）
  - rights=仅内部，quality=high，type=lyrics
"""
import json
import os
import re
from collections import Counter

SRC = r"E:\wx\骰子周边20260608\王晰声卦_六爻v4.3\data\lyrics.txt"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

txt = open(SRC, encoding="utf-8", errors="ignore").read()
bank = json.load(open(BANK, encoding="utf-8"))
exist = {re.sub(r"\s", "", i["text"]) for i in bank["items"]}

cur_song, added, songs = "", [], set()
for line in txt.splitlines():
    s = line.strip()
    if not s:
        continue
    m = re.match(r"^【([^】]+)】", s)
    if m:
        cur_song = m.group(1).strip()
        songs.add(cur_song)
        continue
    s = re.sub(r"\s+", "", s)
    s = s.strip("，、。！？；：\"“”")
    if not (8 <= len(s) <= 34):
        continue
    if re.fullmatch(r"[啊哦嗯吧呢啦呀]+", s):
        continue
    if s in exist:
        continue
    if not re.search(r"[\u4e00-\u9fff]", s):
        continue
    exist.add(s)
    added.append({"text": s, "type": "lyrics", "source": "歌词《%s》" % (cur_song or "未知"),
                  "curated": False, "rights": "仅内部", "mood": "lyric",
                  "verified": True, "quality": "high"})

bank["items"].extend(added)
bank["count"] = len(bank["items"])
bank["by_type"] = dict(Counter(i["type"] for i in bank["items"]))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 歌词骰：从全池随机挑 12 句
import random
random.seed(20261101)
pool = [i for i in bank["items"] if i["type"] == "lyrics" and 10 <= len(i["text"]) <= 26]
picked = random.sample(pool, min(12, len(pool)))
dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["lyrics"]["faces"] = [{"text": p["text"], "source": p["source"]} for p in picked]
dice["sets"]["lyrics"]["face_count"] = len(picked)
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("歌词导入 %d 句｜覆盖 %d 首｜歌词池现 %d 条"
      % (len(added), len(songs), len(pool)))
for p in picked[:6]:
    print("  ", p["text"], "|", p["source"])
