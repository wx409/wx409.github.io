"""把现场 talk 与歌词片段切句，并入 data/phrase_bank.json；重建骰子套。"""
import glob, json, os, re
from collections import Counter

ROOT = r"D:\wx409.github.io"
TALK_DIR = r"E:\wx\论文素材_王晰作传\现场talk"
BANK = os.path.join(ROOT, "data", "phrase_bank.json")
LYR = os.path.join(ROOT, "tavern", "lyrics_fragments.json")
DICE = os.path.join(ROOT, "data", "dice_sets.json")

bank = json.load(open(BANK, encoding="utf-8"))
items = [it for it in bank["items"] if it.get("type") != "lyrics"]      # 旧的“歌名+说明”改判 song
for it in bank["items"]:
    if it.get("type") == "lyrics":
        it2 = dict(it); it2["type"] = "song"; items.append(it2)

MARK = re.compile(r"(?:^|[，。！？、；：]|嗯+|然后|所以|但是|因为|其实|我觉得|就是说|你知道吗|对吧|是吧|真的)")

def split_talk(text):
    parts = [p.strip() for p in MARK.split(text) if p and p.strip()]
    out = []
    for p in parts:
        p = re.sub(r"[\s]+", "", p)
        if 10 <= len(p) <= 46 and re.search(r"[我你咱]", p) and "王晰" not in p:
            out.append(p)
    return out

talk_items, seen = [], set()
for f in sorted(glob.glob(os.path.join(TALK_DIR, "**", "*.txt"), recursive=True)):
    rel = os.path.relpath(f, TALK_DIR)
    city = rel.split(os.sep)[0] if os.sep in rel else ""
    text = open(f, encoding="utf-8", errors="ignore").read()
    for s in split_talk(text):
        if s in seen:
            continue
        seen.add(s)
        talk_items.append({"text": s, "type": "talk",
                           "source": "%s｜%s" % (city, os.path.basename(f)[:40]),
                           "curated": False, "rights": "free", "mood": "talk",
                           "verified": False})

# 歌词片段
lyr_items = []
ly = json.load(open(LYR, encoding="utf-8"))
for song, v in ly.items():
    if song == "_meta" or not isinstance(v, dict):
        continue
    for fr in v.get("fragments") or []:
        t = (fr.get("text") or "").strip()
        if not t:
            continue
        lyr_items.append({"text": t, "type": "lyrics",
                          "source": "歌词《%s》" % song,
                          "curated": False, "rights": "仅内部",
                          "mood": "/".join(fr.get("moods") or []), "verified": True})

items.extend(talk_items)
items.extend(lyr_items)

# 去重
seen, uniq = set(), []
for it in items:
    if it["text"] in seen:
        continue
    seen.add(it["text"]); uniq.append(it)

stat = Counter(it["type"] for it in uniq)
bank = {"generated": "2026-10-31", "count": len(uniq), "by_type": dict(stat),
        "note": "talk=现场转写切句（未校对，verified=false）；lyrics=歌词片段（仅内部，短句引用）；song=歌名+官方说明；mystic=卦象；interview=采访。",
        "items": uniq}
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("phrase_bank:", len(uniq), dict(stat))

# 骰子套重建
import random
random.seed(20261031)

def pick(t, n=6):
    pool = [x["text"] for x in uniq if x["type"] == t and 8 <= len(x["text"]) <= 48]
    random.shuffle(pool)
    return pool[:n]

sets = {
    "emotion": {"name": "情绪骰", "disclaimer": "现场说话原句（转写未校对）；出处见来源字段",
                "faces": pick("talk")},
    "mystic": {"name": "玄学骰", "disclaimer": "娱乐向，非占卜；引语出自站内整理的卦象解析表",
               "faces": pick("mystic")},
    "lyrics": {"name": "歌词骰", "disclaimer": "短句引用，版权归原作者；不整首、不成集",
               "faces": pick("lyrics")},
    "song": {"name": "歌名骰", "disclaimer": "歌名＋官方一句说明", "faces": pick("song")},
    "interview": {"name": "采访骰", "disclaimer": "出自采访记录汇编；部分为标题/备注，非逐字引语",
                  "faces": pick("interview")},
}
for v in sets.values():
    v["face_count"] = len(v["faces"])
json.dump({"generated": "2026-10-31", "sets": sets, "pending": []},
          open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("骰套:", {k: (v["name"], v["face_count"]) for k, v in sets.items()})
