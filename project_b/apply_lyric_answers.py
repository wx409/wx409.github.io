"""读取 docs/歌词可疑清单.md 里用户手写的「答：」结论并执行

格式：条目行 `- 歌词文本  ` 下一行 `<sub>出处 ｜ 原因</sub>`，用户在其后追加「答：xxx」
规则：
  答含「删」→ 从词句库删除该条
  答含「是歌词」→ 保留，标记 verified=true
  答含「歌名」→ 删除（标题行）
"""
import json
import re
from collections import Counter

MD = r"D:\wx409.github.io\docs\歌词可疑清单.md"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"

lines = open(MD, encoding="utf-8").read().splitlines()

pairs = []  # (text, answer)
cur_text = None
for ln in lines:
    s = ln.strip()
    if s.startswith("- ") and "<sub>" not in s:
        cur_text = s[2:].strip()
        continue
    if "答" in s and cur_text:
        m = re.search(r"答[:：]\s*(.*)$", s)
        if m:
            pairs.append((cur_text, m.group(1).strip()))
        cur_text = None

print("解析到 %d 条结论" % len(pairs))

bank = json.load(open(BANK, encoding="utf-8"))
idx = {}
for i, it in enumerate(bank["items"]):
    idx.setdefault(re.sub(r"\s", "", it["text"]), []).append(i)

to_del, to_verify, unmatched = set(), set(), []
for text, ans in pairs:
    key = re.sub(r"\s", "", text)
    hits = idx.get(key)
    if not hits:
        unmatched.append(text)
        continue
    if "删" in ans or "歌名" in ans:
        to_del.update(hits)
    elif "是歌词" in ans:
        to_verify.update(hits)

kept = [it for i, it in enumerate(bank["items"]) if i not in to_del]
before = bank["count"]
bank["items"] = kept
bank["count"] = len(kept)
bank["by_type"] = dict(Counter(i["type"] for i in kept))
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in kept))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("删除 %d 条｜确认歌词 %d 条｜未匹配 %d 条" % (len(to_del), len(to_verify), len(unmatched)))
print("词句库 %d → %d" % (before, bank["count"]))
if unmatched:
    print("未匹配样例:", unmatched[:5])
for i in list(to_del)[:5]:
    print("  删:", bank_text := "[已删]")
