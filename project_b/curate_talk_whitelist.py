"""情绪骰人工白名单：只有读得通的句子进骰面，其余 talk 标 low（不进骰）

背景：现场 talk 是 ASR 输出，句读与用词错误多，规则清不掉。
     所以改为「人工白名单 + 其余降级」，宁可少，不可烂。
"""
import json
from collections import Counter

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

CURATED = [
    "你们知不知道在珠峰大北有个邮局",
    "我特别想在邮局里写一下想对你们说的话",
    "我是一个非常含蓄腼腆的人",
    "我一想到你们在的话我会非常非常的温暖",
    "你们也受到了我对你们的改变",
    "看到你们开心，我也真的很开心",
    "我相信我未来会更好的，继续加油",
    "其实我对新的一面还是特别的期待",
]
FACES = [
    "你们知不知道在珠峰大北有个邮局",
    "我特别想在邮局里写一下想对你们说的话",
    "我是一个非常含蓄腼腆的人",
    "我一想到你们在的话我会非常非常的温暖",
    "你们也受到了我对你们的改变",
    "看到你们开心，我也真的很开心",
]

bank = json.load(open(BANK, encoding="utf-8"))
curated_set = set(CURATED)
hit = 0
faces = []
for it in bank["items"]:
    if it["type"] != "talk":
        continue
    if it["text"] in curated_set:
        it["quality"] = "high"
        it["curated"] = True
        hit += 1
        if it["text"] in FACES and len(faces) < 6:
            faces.append({"text": it["text"], "source": it["source"]})
    else:
        it["quality"] = "low"
        it["curated"] = False

# 若白名单命中不足 6 面，按 FACES 顺序从库里补
if len(faces) < 6:
    idx = {i["text"]: i for i in bank["items"] if i["type"] == "talk"}
    faces = [{"text": t, "source": idx[t]["source"]} for t in FACES if t in idx][:6]

bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["emotion"]["faces"] = faces
dice["sets"]["emotion"]["face_count"] = len(faces)
dice["sets"]["emotion"]["disclaimer"] = "现场说话原句（人工白名单：只收读得通的句子）"
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("白名单命中 %d｜情绪骰 %d 面｜high 总数 %d" % (hit, len(faces), bank["quality_stats"].get("high", 0)))
for f in faces:
    print("  ", f["text"][:34], "|", f["source"])
