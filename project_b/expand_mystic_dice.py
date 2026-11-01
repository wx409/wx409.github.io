"""玄学骰扩到 64 卦（易经六十四卦全量，取自词句库 mystic）"""
import json

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

bank = json.load(open(BANK, encoding="utf-8"))
mystic = [i for i in bank["items"] if i["type"] == "mystic"]
print("卦象池", len(mystic))

faces = [{"text": m["text"], "source": m["source"]} for m in mystic]
dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["mystic"]["faces"] = faces
dice["sets"]["mystic"]["face_count"] = len(faces)
dice["sets"]["mystic"]["disclaimer"] = "易经六十四卦（每卦一句释义，娱乐向）"
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("玄学骰 %d 面" % len(faces))
for f in faces[:4]:
    print("  ", f["text"][:44])
