# -*- coding: utf-8 -*-
"""timeline.json 补两条：沉响 10-09 / 10-10 各一条（按日期唯一条目，不按 title 去重）。

原因：原有条目是 2026-09-10 的「官宣/开票」，把两场写在同一条标题里；
页面按条目日期渲染，读者只看到「10-09、10-10」这一行，没有两场各自的演出条目。
"""
import json
from pathlib import Path

P = Path(r"D:\wx409.github.io\data\timeline.json")
d = json.loads(P.read_text(encoding="utf-8"))
NEW = [
    {"date": "2026-10-09", "type": "career",
     "title": "《沉响与长歌》北京首场（王晰 × 傲日其愣）· 北京天桥艺术中心·大剧场",
     "source": "用户确认场次 + 工作室微博（2026-10-12 点歌帖）+ 现场歌单",
     "stage": "东演"},
    {"date": "2026-10-10", "type": "career",
     "title": "《沉响与长歌》北京第二场（王晰 × 傲日其愣）· 北京天桥艺术中心·大剧场",
     "source": "用户确认场次 + 工作室微博（2026-10-14 点歌帖）+ 现场歌单",
     "stage": "东演"},
]
have = {(x.get("date"), x.get("title")) for x in d}
n = 0
for e in NEW:
    if (e["date"], e["title"]) in have:
        continue
    # 同日期同演出若已存在（按日期+关键词），不重复加
    if any(x.get("date") == e["date"] and "沉响" in str(x.get("title")) for x in d):
        continue
    d.append(e)
    n += 1

# 按日期排序（字符串日期可直接排）
d.sort(key=lambda x: str(x.get("date") or ""))
P.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"[OK] 新增 {n} 条，合计 {len(d)} 条")
for x in d:
    if str(x.get("date", "")).startswith("2026-10") or "沉响" in str(x.get("title")):
        print("  ", x["date"], "|", str(x["title"])[:70])
