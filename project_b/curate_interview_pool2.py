"""采访骰面 v2：去重（忽略标点）、排除截断句、偏好完整表达"""
import json
import re

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

BAD = re.compile(r"流水机|流水记|非常感谢这个|谢谢大家|感谢这个|不好意思|那个那个")
GOOD = ["其实", "我觉得", "因为", "所以", "但是", "希望", "认为", "坚持", "理解", "明白",
        "选择", "相信", "低音", "专辑", "音乐", "作品", "舞台", "声音", "创作", "人生", "标签"]
TRUNC = set("在的了我你他们和跟就都也还但而而且如果因")

def norm(t):
    return re.sub(r"[。，、！？；：\s]", "", t)

bank = json.load(open(BANK, encoding="utf-8"))
cands = []
for it in bank["items"]:
    if it["type"] != "interview":
        continue
    t = it["text"].strip()
    if not (18 <= len(t) <= 48):
        continue
    if BAD.search(t):
        continue
    if t[-1] in TRUNC:
        continue
    score = sum(2 for k in GOOD if k in t)
    if score < 4:
        continue
    cands.append((score, len(t), it))

cands.sort(key=lambda x: (-x[0], -x[1]))
faces, seen = [], set()
for s, ln, it in cands:
    k = norm(it["text"])
    if k in seen:
        continue
    seen.add(k)
    faces.append({"text": it["text"], "source": it["source"]})
    if len(faces) >= 10:
        break

dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["interview"]["faces"] = faces
dice["sets"]["interview"]["face_count"] = len(faces)
dice["sets"]["interview"]["disclaimer"] = "他本人的原话（采访/播客/转写）；出处见来源"
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("采访骰 %d 面" % len(faces))
for f in faces:
    print("  ", f["text"][:50], "|", f["source"][:24])
