"""采访骰重挑：剔除“标题《…》/主题为/被称为/由…举办”这类台账式描述，只留可引用的内容句。"""
import json, os

ROOT = r"D:\wx409.github.io"
BANK = os.path.join(ROOT, "data", "phrase_bank.json")
DICE = os.path.join(ROOT, "data", "dice_sets.json")

META_START = ("标题《", "主题为", "被称为", "由中国", "在演唱", "分享歌曲", "具体采访内容")
faces_text = [
    "称低音是“天赐的礼物”，形容低音像“大海，表面平静，内里却汹涌澎湃”。",
    "谈到坚持的意义：“在这个路上，有的人上车，有的人下车……能够坚持下来的都是很了不起的。”",
    "坦言对《歌手》舞台留有遗憾，提到“家庭”和“作品”是最坚实的安全区。",
    "将巡回音乐会《吾》的新年第一站定在长沙，称其为“梦想开始的地方”。",
    "透露当年的温馨目标：“当爸爸”。",
    "以《歌手4》踢馆新人身份，详细讲述曾做代驾司机的辛酸过往。",
]

bank = json.load(open(BANK, encoding="utf-8"))
meta = 0
for it in bank["items"]:
    if it["type"] != "interview" or it.get("mood") == "title":
        continue
    if it["text"].startswith(META_START):
        it["mood"] = "meta"
        meta += 1
    else:
        it["mood"] = "quote"
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("台账式描述改为 mood=meta:", meta)

bymap = {it["text"]: it for it in bank["items"] if it["type"] == "interview"}
faces, missing = [], []
for t in faces_text:
    if t in bymap:
        faces.append({"text": t, "source": bymap[t]["source"]})
    else:
        missing.append(t)
print("缺失", missing)

dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["interview"]["faces"] = faces
dice["sets"]["interview"]["face_count"] = len(faces)
dice["sets"]["interview"]["disclaimer"] = "出自采访记录汇编（备注行）；为转述句，引用时标“据采访记录”"
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for f in faces:
    print("  ", f["text"][:50], "|", f["source"])
