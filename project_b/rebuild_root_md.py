"""根表对账 + 重生成 md
1) 清单里已删掉、且没有全文的「人工核对」条目 → 从根表移除
2) 任何情况下 md 都由 json 重新生成（避免 md 过期）
"""
import json, os, re
from datetime import date

BASE = r"E:\wx\私有\王晰全文库\采访目录"
JS = os.path.join(BASE, "采访杂志根表.json")
MD = os.path.join(BASE, "采访杂志根表.md")
TODO = os.path.join(BASE, "待人工清单.md")

table = json.load(open(JS, encoding="utf-8"))
md_text = open(TODO, encoding="utf-8").read() if os.path.exists(TODO) else ""
live_links = set(re.findall(r"https?://[^\s)）]+", md_text))
live_norm = {u.rstrip("/") for u in live_links}

before = len(table["items"])
removed = []
keep = []
for it in table["items"]:
    link = (it.get("链接", "") or "").rstrip("/")
    is_manual = "人工核对" in (it.get("渠道", "") or "") or "待人工" in (it.get("渠道", "") or "")
    has_full = bool(it.get("全文路径"))
    if is_manual and not has_full and link and link not in live_norm:
        removed.append(it["名称"][:40])
        continue
    keep.append(it)

table["items"] = keep
table["count"] = len(keep)
table["updated"] = date.today().isoformat()
json.dump(table, open(JS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 重新生成 md
md = ["# 王晰 采访/杂志 根表", "",
      "更新：%s ｜ 共 %d 条（已存全文 %d 条）" % (
          table["updated"], table["count"],
          sum(1 for i in keep if i.get("全文路径"))), "",
      "| 时间 | 名称 | 类型 | 渠道 | 状态 | 全文 | 链接 |",
      "|---|---|---|---|---|---|---|"]
for it in keep:
    md.append("| %s | %s | %s | %s | %s | %s | %s |" % (
        it.get("时间") or "—", (it.get("名称") or "")[:34], it.get("类型", ""),
        (it.get("渠道") or "")[:16], it.get("状态", ""),
        (it.get("全文路径") or "—")[:26], (it.get("链接") or "")[:58]))
open(MD, "w", encoding="utf-8").write("\n".join(md) + "\n")

print("根表 %d → %d（移除 %d 条已删清单项）" % (before, len(keep), len(removed)))
for r in removed[:10]:
    print("  移除：", r)
