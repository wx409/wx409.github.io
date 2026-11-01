"""采访骰面 v3：优先「带句末标点」的成句，不足时再补转写句；去重按前 24 字"""
import json
import re

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

BAD = re.compile(r"流水机|流水记|非常感谢这个|谢谢大家|感谢这个|不好意思|那个那个")
GOOD = ["其实", "我觉得", "因为", "所以", "但是", "希望", "认为", "坚持", "理解", "明白",
        "选择", "相信", "低音", "专辑", "音乐", "作品", "舞台", "声音", "创作", "人生", "标签"]
TRUNC = set("在的了我你他们和跟就都也还但而如果因所以为与以及")


def norm(t):
    return re.sub(r"[。，、！？；：\s]", "", t)[:16]


bank = json.load(open(BANK, encoding="utf-8"))
solid, loose = [], []
for it in bank["items"]:
    if it["type"] != "interview":
        continue
    t = it["text"].strip()
    if not (20 <= len(t) <= 60) or BAD.search(t):
        continue
    score = sum(2 for k in GOOD if k in t)
    if score < 4:
        continue
    if t[-1] in TRUNC:
        continue
    # 人工整理稿（curated）视为成句，即使保存时去掉了句号
    if t[-1] in "。！？" or it.get("curated") or it.get("mood") in ("quote", "quote_mag"):
        solid.append((score, len(t), it))
    else:
        loose.append((score, len(t), it))

solid.sort(key=lambda x: (-x[0], -x[1]))
loose.sort(key=lambda x: (-x[0], -x[1]))

faces, seen = [], set()
for group in (solid, loose):
    for s, ln, it in group:
        k = norm(it["text"])
        if k in seen:
            continue
        seen.add(k)
        faces.append({"text": it["text"], "source": it["source"]})
        if len(faces) >= 10:
            break
    if len(faces) >= 10:
        break

dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["interview"]["faces"] = faces
dice["sets"]["interview"]["face_count"] = len(faces)
dice["sets"]["interview"]["disclaimer"] = "他本人的原话（采访/播客/转写）；出处见来源"
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("成句池 %d｜转写池 %d｜取 %d 面" % (len(solid), len(loose), len(faces)))
for f in faces:
    print("  ", f["text"][:56], "|", f["source"][:22])
