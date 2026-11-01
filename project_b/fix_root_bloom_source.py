"""更正「向下扎根，向上开花」的出处

原记录：来自《音乐流水纪》专访回顾（转引）
真实出处：《天赐的声音》第一季 第 2 期（2020-02，与张韶涵合唱《黎明前的黑暗》后，
        回应丁太升「向上突破而不是向下兼容」的点评）
"""
import json

BANK = r"D:\wx409.github.io\data\phrase_bank.json"

NEW_SOURCE = ("《天赐的声音》S1 第2期（2020-02，与张韶涵合唱《黎明前的黑暗》后回应点评）"
              "｜转引自《音乐流水纪》专访回顾 2026-01")
NOTE = "转引已核：多方报道一致（网易/中国青年网 2020-02 报道）；原话为现场回应，非专访正文"

bank = json.load(open(BANK, encoding="utf-8"))
hit = 0
for it in bank["items"]:
    if "向下扎根" in it.get("text", ""):
        old = it.get("source", "")
        it["source"] = NEW_SOURCE
        it["note"] = NOTE
        it["type"] = "talk"
        it["mood"] = "talk"
        it["quality"] = "high"
        it["curated"] = True
        it["verified"] = False
        hit += 1
        print("更正：", it["text"])
        print("  旧出处:", old[:60])
        print("  新出处:", NEW_SOURCE[:60])

json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n共更正", hit, "条")
