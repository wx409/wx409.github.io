"""把处理队列结果并回采访杂志根表 + 生成处理结果说明"""
import json, os
from datetime import date

BASE = r"E:\wx\私有\王晰全文库\采访目录"
Q = os.path.join(BASE, "处理队列.json")
ROOT = os.path.join(BASE, "采访杂志根表.json")

q = json.load(open(Q, encoding="utf-8"))["items"]
table = json.load(open(ROOT, encoding="utf-8"))
idx = {(it.get("链接", "") or "").split("?")[0]: it for it in table["items"]}

added = 0
for r in q:
    key = (r["link"] or "").split("?")[0]
    art = r.get("transcript") or r.get("ocr") or r.get("text_path") or ""
    words = 0
    if art:
        p = os.path.join(BASE, "全文", art)
        if os.path.exists(p):
            words = len(open(p, encoding="utf-8", errors="ignore").read())
    it = idx.get(key)
    if it is None:
        it = {"名称": r["title"][:80], "类型": "采访", "时间": r["date"], "链接": r["link"],
              "全文路径": "", "字数": 0, "渠道": "人工核对清单", "状态": "待抓", "备注": ""}
        table["items"].append(it); idx[key] = it; added += 1
    it["全文路径"] = art
    it["字数"] = words
    it["状态"] = {"已转写": "已存（本地转写）", "已OCR": "已存（本地OCR）"}.get(r["status"], "已存")
    extra = []
    if r.get("video_path"):
        extra.append("视频已下")
    if r.get("image_dir"):
        extra.append("图片已下")
    it["备注"] = ("｜".join(extra) + "｜来源：待人工清单核对") if extra else "来源：待人工清单核对"

table["items"].sort(key=lambda x: (x.get("时间") or "0000"), reverse=True)
table["count"] = len(table["items"])
table["updated"] = date.today().isoformat()
json.dump(table, open(ROOT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

md = ["# 本轮处理结果（%s）" % date.today().isoformat(), "",
      "| 时间 | 名称 | 处理 | 字数 | 产出文件 |", "|---|---|---|---|---|"]
for r in q:
    out = r.get("transcript") or r.get("ocr") or r.get("text_path") or ""
    kind = {"已转写": "本地转写", "已OCR": "本地OCR"}.get(r["status"], "原文")
    w = 0
    p = os.path.join(BASE, "全文", out)
    if out and os.path.exists(p):
        w = len(open(p, encoding="utf-8", errors="ignore").read())
    md.append("| %s | %s | %s | %d | %s |" % (r["date"], r["title"][:34], kind, w, out[:40]))
open(os.path.join(BASE, "处理结果.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
print("根表 %d 条（新增 %d）｜本次处理 %d 条" % (table["count"], added, len(q)))
