"""采访骰改为「他本人原话」：清理噪声、挑 6 条"""
import json, os, re
from collections import Counter

ROOT = r"D:\wx409.github.io"
BANK = os.path.join(ROOT, "data", "phrase_bank.json")
DICE = os.path.join(ROOT, "data", "dice_sets.json")

NOISE = re.compile(r"第.{1,3}届|大赛|音乐节|金钟奖流行音乐大赛|海上联合")
bank = json.load(open(BANK, encoding="utf-8"))

items, dropped = [], 0
for it in bank["items"]:
    if it["type"] == "interview" and it.get("mood") == "quote":
        t = it["text"]
        if NOISE.search(t) or (len(t) < 12 and not re.search(r"[我你]", t)):
            dropped += 1
            continue
    items.append(it)
bank["items"] = items
bank["count"] = len(items)
bank["by_type"] = dict(Counter(it["type"] for it in items))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("噪声剔除", dropped, "| 现共", bank["count"], bank["by_type"])

PICK = [
    "在这个路上，有的人上车，有的人下车，很多人选择放弃，能够坚持下来的不多，而能坚持下来的都是很了不起的",
    "很多人给我的标签——低音炮、低音王子，其实我不是很喜欢。因为低音和高音只是音域，不是风格",
    "有人问我，为什么不再去酒吧？我说，如果再唱，我一定要站在最牛的舞台上，让人服，而不是为了生存",
    "低音像是大海，表面平静，内里却汹涌澎湃",
    "国内有太多的男低音，可能在做歌做专辑时一些问题还没有遇到，应该如何拿出例子，这是我的使命",
    "我相信我们都不是天才，都在路上",
]
bymap = {it["text"]: it for it in bank["items"] if it["type"] == "interview"}
faces, missing = [], []
for t in PICK:
    if t in bymap:
        faces.append({"text": t, "source": bymap[t]["source"]})
    else:
        missing.append(t)
print("缺失", missing)

dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["interview"]["faces"] = faces
dice["sets"]["interview"]["face_count"] = len(faces)
dice["sets"]["interview"]["disclaimer"] = "他本人的原话（摘自采访正文引号内）；出处为文章标题"
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for f in faces:
    print("  ", f["text"][:44], "|", f["source"][:34])
