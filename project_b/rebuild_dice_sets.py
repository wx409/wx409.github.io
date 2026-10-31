"""重建骰子套：面= {text, source}；去掉歌名骰；每面标注出处"""
import json, os, random

ROOT = r"D:\wx409.github.io"
BANK = os.path.join(ROOT, "data", "phrase_bank.json")
DICE = os.path.join(ROOT, "data", "dice_sets.json")

bank = json.load(open(BANK, encoding="utf-8"))
items = bank["items"]

BAD = ("未详细记录", "未记录", "暂无", "无内容", "待补", "不详")
BAD_END = set("的但在我你他就也还 把被让给对和跟从到一是在那这说有着了过非常特别真会要想能做有年对好")
EMO = ["谢谢", "感谢", "开心", "希望", "温暖", "幸福", "喜欢", "珍惜", "记得", "陪伴", "勇敢", "相信", "感动", "努力"]

ok = [it for it in items if not any(b in it["text"] for b in BAD)]

random.seed(20261031)

def pick(typ, n=6, maxlen=48, mood=None):
    pool = [it for it in ok if it["type"] == typ and 10 <= len(it["text"]) <= maxlen
            and (mood is None or it.get("mood") == mood)]
    random.shuffle(pool)
    return [{"text": it["text"], "source": it["source"]} for it in pool[:n]]

def talk_faces():
    curated = [it for it in ok if it["type"] == "talk" and it.get("curated")]
    if len(curated) >= 6:
        return [{"text": it["text"], "source": it["source"]} for it in curated[:6]]
    pool = sorted([it for it in ok if it["type"] == "talk"],
                  key=lambda it: sum(2 for k in EMO if k in it["text"]), reverse=True)
    return [{"text": it["text"], "source": it["source"]} for it in pool[:6]]

sets = {
    "emotion": {"name": "情绪骰", "disclaimer": "现场说话原句（语音转写未校对，人工挑选）", "faces": talk_faces()},
    "mystic": {"name": "玄学骰", "disclaimer": "娱乐向，非占卜；引语出自站内整理的卦象解析表", "faces": pick("mystic", maxlen=80)},
    "lyrics": {"name": "歌词骰", "disclaimer": "短句引用，版权归原作者；不整首、不成集", "faces": pick("lyrics", maxlen=40)},
    "interview": {"name": "采访骰", "disclaimer": "出自采访记录汇编；部分为标题或备注，非逐字引语",
                  "faces": pick("interview", maxlen=60, mood="note")},
}
for v in sets.values():
    v["face_count"] = len(v["faces"])

json.dump({"generated": "2026-10-31", "sets": sets, "pending": [],
           "note": "面为 {text, source}；歌名类不进骰子"},
          open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k, v in sets.items():
    print("==", v["name"], v["face_count"])
    for f in v["faces"]:
        print("   ", f["text"][:40], "|", f["source"][:28])
