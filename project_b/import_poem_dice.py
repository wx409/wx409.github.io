"""两件事：
   1) 把「采访正文｜…」来源的条目确认为 high（它们来自 xlsx 里的原文，非 AI 摘要）
   2) 把「王晰六爻诗卦」的 54 个词导入为新股套「诗卦骰」
"""
import json
from collections import Counter

import pandas as pd

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"
CSV = r"E:\wx\骰子周边20260608\GEO\GEO\王晰六爻诗卦\wangxi_dice_54_words.csv"

# --- 1) 采访正文确认为高可信 ---
bank = json.load(open(BANK, encoding="utf-8"))
n = 0
for it in bank["items"]:
    src = it.get("source") or ""
    if src.startswith("采访正文｜"):
        it["quality"] = "high"
        it["verified"] = True
        it["note"] = "原文出自《王晰采访记录汇编.xlsx》正文列"
        n += 1
bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("采访正文确认为 high：%d 条" % n)

# --- 2) 诗卦骰 ---
df = pd.read_csv(CSV)
faces = []
for _, r in df.iterrows():
    w = str(r["词"]).strip()
    if not w:
        continue
    faces.append({"text": w, "source": "六爻诗卦·%s（第%d骰 面%d）"
                  % (r["爻位/象位"], int(r["骰子编号"]), int(r["所属面"].replace("面", "")))})

dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["poem"] = {
    "name": "诗卦骰",
    "disclaimer": "六爻诗卦 54 词（9 骰 × 6 面：初爻潜/二爻见/三爻惕/四爻跃/五爻飞/上爻亢/天/地/人）",
    "faces": faces,
    "face_count": len(faces),
}
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("诗卦骰 %d 面" % len(faces))
for f in faces[:6]:
    print("  ", f["text"], "|", f["source"])
