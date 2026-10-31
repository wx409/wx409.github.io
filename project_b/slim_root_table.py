"""根表瘦身：只保留「已核对/已处理」；自动微博候选另存，不进根表
口径：
  - 保留：有全文路径的、渠道含「人工核对」或「本地另存」、已转写/已OCR
  - 移出：渠道为「微博搜索：xxx」且无全文的（自动候选）→ 写入 自动候选.md（根表不再展示）
  - 同名只留一条
"""
import json, os, re
from datetime import date

BASE = r"E:\wx\私有\王晰全文库\采访目录"
JS = os.path.join(BASE, "采访杂志根表.json")
CANDS = os.path.join(BASE, "自动候选.json")

table = json.load(open(JS, encoding="utf-8"))
old = table["items"]
cands = json.load(open(CANDS, encoding="utf-8"))["items"] if os.path.exists(CANDS) else []

keep, moved, seen = [], [], set()
for it in old:
    key = re.sub(r"\s+", "", (it.get("名称") or ""))[:30]
    ch = it.get("渠道") or ""
    has_full = bool(it.get("全文路径"))
    curated = ("人工核对" in ch) or ("本地另存" in ch) or ("豆瓣" in ch) or has_full
    if not curated:
        moved.append(it)
        continue
    if key in seen:
        continue
    seen.add(key)
    keep.append(it)

# 合并旧候选
merged = {c.get("链接") or c.get("名称"): c for c in cands}
for m in moved:
    merged.setdefault(m.get("链接") or m.get("名称"), m)

json.dump({"updated": date.today().isoformat(), "count": len(merged),
           "note": "自动采集的微博候选（未核对，不进根表）", "items": list(merged.values())},
          open(CANDS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

table["items"] = keep
table["count"] = len(keep)
table["updated"] = date.today().isoformat()
table["note"] = "只收已核对/已处理条目；自动采集候选见 自动候选.json"
json.dump(table, open(JS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

md = ["# 王晰 采访/杂志 根表", "",
      "更新：%s ｜ 共 %d 条（已存全文 %d 条）" % (table["updated"], len(keep),
                                              sum(1 for i in keep if i.get("全文路径"))),
      "", "> 只列已核对/已处理条目；自动采集的微博候选不进本表（见 `自动候选.md`）。", "",
      "| 时间 | 名称 | 类型 | 渠道 | 状态 | 全文 | 链接 |", "|---|---|---|---|---|---|---|"]
for it in keep:
    md.append("| %s | %s | %s | %s | %s | %s | %s |" % (
        it.get("时间") or "—", (it.get("名称") or "")[:34], it.get("类型", ""),
        (it.get("渠道") or "")[:16], it.get("状态", ""),
        (it.get("全文路径") or "—")[:26], (it.get("链接") or "")[:58]))
open(os.path.join(BASE, "采访杂志根表.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

cm = ["# 自动采集候选（%d 条，未核对）" % len(merged), "",
      "这些是每日微博搜索自动抓到的，还没人工确认，**不进根表**。", "",
      "| 渠道 | 名称 | 链接 |", "|---|---|---|"]
for c in list(merged.values())[:300]:
    cm.append("| %s | %s | %s |" % ((c.get("渠道") or "")[:14], (c.get("名称") or "")[:40],
                                    (c.get("链接") or "")[:56]))
open(os.path.join(BASE, "自动候选.md"), "w", encoding="utf-8").write("\n".join(cm) + "\n")

print("根表 %d → %d 条｜候选 %d 条" % (len(old), len(keep), len(merged)))
