"""重挑采访骰面：排除口水/致谢句，优先有观点的句子；并修「流水机→流水纪」"""
import json
import re
from collections import Counter

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

BAD = re.compile(r"流水机|流水记|非常感谢这个|谢谢大家|感谢这个|不好意思|那个那个|嗯|啊，|呢$|吧$|好吧")
GOOD = ["其实", "我觉得", "因为", "所以", "但是", "希望", "认为", "坚持", "理解", "明白",
        "选择", "相信", "低音", "专辑", "音乐", "作品", "舞台", "声音", "创作", "人生"]

bank = json.load(open(BANK, encoding="utf-8"))
for it in bank["items"]:
    it["text"] = it["text"].replace("流水机", "流水纪").replace("流水记", "流水纪")

cands = []
for it in bank["items"]:
    if it["type"] != "interview":
        continue
    t = it["text"]
    if not (16 <= len(t) <= 52):
        continue
    if BAD.search(t):
        continue
    score = sum(2 for k in GOOD if k in t)
    if score < 4:
        continue
    cands.append((score, len(t), it))

cands.sort(key=lambda x: (-x[0], -x[1]))
faces, seen = [], set()
for s, ln, it in cands:
    if it["text"] in seen:
        continue
    seen.add(it["text"])
    faces.append({"text": it["text"], "source": it["source"]})
    if len(faces) >= 12:
        break

json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["interview"]["faces"] = faces[:8]
dice["sets"]["interview"]["face_count"] = len(faces[:8])
dice["sets"]["interview"]["disclaimer"] = "他本人的原话（采访/播客/转写）；出处见来源"
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("采访骰候选 %d｜取 %d 面" % (len(cands), len(faces[:8])))
for f in faces[:8]:
    print("  ", f["text"][:52], "|", f["source"][:26])
