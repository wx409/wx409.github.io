"""给词句打质量分层：high / mid / low（骰子只抽 high）

打分维度（可解释）：
  +2 长度 18–45 字（太短没信息，太长抽出来读不完）
  +2 含观点/态度词（我觉得/其实/因为/希望/认为/发现/坚持/理解/明白/选择）
  +2 含具体名词（专辑/歌/舞台/录音/音乐/低音/作品/时间/演唱会/巡演/北京…）
  -2 以语气词开头或结尾（对/嗯/啊/然后/就这样）
  -2 纯重复（同一词出现 3 次以上）
  -3 长度 <14 字

>=5 → high｜2–4 → mid｜<2 → low
非 interview 类（歌词/卦象/歌名）默认 high（本身经过筛选）
"""
import json
import re
from collections import Counter

BANK = r"D:\wx409.github.io\data\phrase_bank.json"

OPINION = ["我觉得", "其实", "因为", "希望", "认为", "发现", "坚持", "理解", "明白",
           "选择", "相信", "不想", "愿意", "感谢", "遗憾", "重要", "意思", "感觉"]
NOUN = ["专辑", "歌", "舞台", "录音", "音乐", "低音", "作品", "时间", "演唱会", "巡演",
        "北京", "长沙", "城市", "观众", "老师", "团队", "声音", "创作", "编曲", "情绪",
        "人生", "生活", "自己", "大家", "孩子", "家人"]
FILLER = re.compile(r"^(对|嗯|啊|哦|然后|就是|那个|这个|好吧|是的|对对)")


def score(it):
    if it["type"] not in ("interview", "talk"):
        return "high"
    t = it["text"]
    s = 0
    if 18 <= len(t) <= 45:
        s += 2
    elif len(t) < 14:
        s -= 3
    if any(w in t for w in OPINION):
        s += 2
    if any(w in t for w in NOUN):
        s += 2
    if FILLER.match(t) or t.endswith(("对", "嗯", "啊", "然后")):
        s -= 2
    if re.search(r"(.{2,3})\1{2,}", t):
        s -= 2
    if s >= 5:
        return "high"
    if s >= 2:
        return "mid"
    return "low"


bank = json.load(open(BANK, encoding="utf-8"))
c = Counter()
for it in bank["items"]:
    q = score(it)
    it["quality"] = q
    c[q] += 1

bank["quality_stats"] = dict(c)
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("质量分层:", dict(c), "| 总", bank["count"])
by = Counter((it["type"], it.get("quality")) for it in bank["items"])
for k in sorted(by):
    print("  %-10s %-5s %d" % (k[0], k[1], by[k]))
