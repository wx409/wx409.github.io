"""从词句库 mystic（64 卦释义）生成 data/hexagrams.json

结构：{"乾": {"乾": {"name":..., "virtue":..., "text":...}}, ...}  以 [上卦][下卦] 索引
卦名规则：`水雷屯（初生）` → 上=水(坎) 下=雷(震)；`乾为天` → 上=乾 下=乾
"""
import json
import re

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
OUT = r"D:\wx409.github.io\data\hexagrams.json"

TRIG = {"天": "乾", "地": "坤", "雷": "震", "风": "巽", "水": "坎", "火": "离", "山": "艮", "泽": "兑",
        "乾": "乾", "坤": "坤", "震": "震", "巽": "巽", "坎": "坎", "离": "离", "艮": "艮", "兑": "兑"}

bank = json.load(open(BANK, encoding="utf-8"))
mystic = [i for i in bank["items"] if i["type"] == "mystic"]

table, made = {}, 0
for it in mystic:
    src = it.get("source") or ""
    raw = src.split("｜")[-1].strip()
    m = re.match(r"^(.{1,2}?)(为.+)（(.+)）$", raw) or re.match(r"^(.{1}?)(.{1}?)(.+)（(.+)）$", raw)
    name, virtue, up, low = "", "", None, None

    mm = re.match(r"^(.+)（(.+)）$", raw)
    body = mm.group(1) if mm else raw
    virtue = mm.group(2) if mm else ""
    if "为" in body and len(body) <= 4:          # 乾为天 / 坤为地
        up = low = TRIG.get(body[0])
        name = body
    else:                                          # 水雷屯
        up = TRIG.get(body[0]); low = TRIG.get(body[1]); name = body
    if not up or not low:
        print("跳过解析失败:", raw)
        continue
    table.setdefault(up, {})[low] = {"name": name, "virtue": virtue,
                                     "text": it["text"], "source": src}
    made += 1

json.dump(table, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("生成 %d 卦 → %s" % (made, OUT))
missing = []
for u in TRIG.values():
    for l in TRIG.values():
        if u not in table or l not in table[u]:
            missing.append(u + l)
print("缺失组合:", len(set(missing)), sorted(set(missing))[:8])
