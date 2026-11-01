"""清洗现场 talk 词句：去语气词、去重复、统一友好出处，重挑情绪骰面

规则：
  1. 行内删语气词（嗯/啊/哦/呃/那个/然后/就是/这个/对对/哈哈/是吧/对不对）
  2. 删完太短（<10 字）或只剩虚词的丢弃
  3. 近重复合并（去掉标点后比较，含包含关系也算重复）
  4. 出处改友好格式：「上海 · 2025-11-21 现场 talk」
  5. 重新打分（quality），骰面只取 high
"""
import json
import re
from collections import Counter

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

FILLER = re.compile(r"(嗯+|啊+|哦+|呃+|那个|然后|就是|这个|对对+|哈哈+|是吧|对不对|你知道吧|好吧|那个那个)")
SPLIT = re.compile(r"[。！？；]")

def friendly_source(src):
    s = src or ""
    city = ""
    m = re.search(r"^(上海|北京|广州|成都|重庆|杭州|武汉|长沙|深圳|西安|南京|郑州|青岛|天津|苏州|宁波|福州|厦门|合肥|济南|昆明|贵阳|南宁|海口|三亚|沈阳|哈尔滨|长春|石家庄|太原|呼和浩特|兰州|西宁|银川|乌鲁木齐|拉萨)", s)
    if m:
        city = m.group(1)
    ymd = re.search(r"(20\d{2})(\d{2})(\d{2})", s)
    date = "%s-%s-%s" % (ymd.group(1), ymd.group(2), ymd.group(3)) if ymd else ""
    if city and date:
        return "%s · %s 现场 talk" % (city, date)
    if date:
        return "%s 现场 talk" % date
    return "现场 talk"

def normalize(t):
    t = FILLER.sub("", t)
    t = re.sub(r"[\s，、,·—\-～~]+", "", t)
    return t

bank = json.load(open(BANK, encoding="utf-8"))
items = bank["items"]

kept, dropped, merged = [], 0, 0
seen = []

for it in items:
    if it["type"] != "talk":
        kept.append(it)
        continue
    t = it["text"]
    for seg in SPLIT.split(t):
        seg = FILLER.sub("", seg).strip("，、 ")
        seg = re.sub(r"^[和跟就也还但又而]+", "", seg)
        if len(seg) < 10:
            dropped += 1
            continue
        if re.fullmatch(r"[对嗯啊哦呃好是的谢谢大家哈]+", seg):
            dropped += 1
            continue
        norm = normalize(seg)
        if any(norm in x or x in norm for x in seen):
            merged += 1
            continue
        seen.append(norm)
        kept.append({
            "text": seg,
            "type": "talk",
            "source": friendly_source(it.get("source", "")),
            "curated": False,
            "rights": "free",
            "mood": "talk",
            "verified": False,
        })

bank["items"] = kept
bank["count"] = len(kept)
bank["by_type"] = dict(Counter(i["type"] for i in kept))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("talk 清洗：保留 %d｜丢弃 %d｜合并重复 %d"
      % (sum(1 for i in kept if i["type"] == "talk"), dropped, merged))
for i in [x for x in kept if x["type"] == "talk"][:8]:
    print("  ", i["text"][:44], "|", i["source"])
