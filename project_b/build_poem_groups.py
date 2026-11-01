"""把「六爻诗卦」重组为可分爻位取词的结构（9 组 × 6 词）

写入 dice_sets.json 的 poem 套：groups=[{name, words:[{text,source}]}]
"""
import json

import pandas as pd

CSV = r"E:\wx\骰子周边20260608\GEO\GEO\王晰六爻诗卦\wangxi_dice_54_words.csv"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

ORDER = ["初爻·潜", "二爻·见", "三爻·惕", "四爻·跃", "五爻·飞", "上爻·亢",
         "天骰·天时", "地骰·地利", "人骰·人和"]

df = pd.read_csv(CSV)
groups = []
for name in ORDER:
    rows = df[df["爻位/象位"] == name]
    if rows.empty:
        # 兼容命名差异
        rows = df[df["爻位/象位"].str.startswith(name.split("·")[0])]
    words = [{"text": str(r["词"]).strip(),
              "source": "六爻诗卦·%s（第%d骰 面%d）" % (name, int(r["骰子编号"]),
                                                int(str(r["所属面"]).replace("面", "")))}
             for _, r in rows.iterrows() if str(r["词"]).strip()]
    groups.append({"name": name, "words": words})

dice = json.load(open(DICE, encoding="utf-8"))
poem = dice["sets"]["poem"]
poem["groups"] = groups
poem["face_count"] = sum(len(g["words"]) for g in groups)
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("诗卦分组：")
for g in groups:
    print("  %-8s %d 词：%s" % (g["name"], len(g["words"]), "、".join(w["text"] for w in g["words"])))
