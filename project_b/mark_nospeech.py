"""把「无有效语音」的条目在根表里标为「无对白（跳过）」"""
import json
import os

BASE = r"E:\wx\私有\王晰全文库\采访目录"
IDX = os.path.join(BASE, "转写索引.json")
ROOT = os.path.join(BASE, "采访杂志根表.json")

idx = json.load(open(IDX, encoding="utf-8"))
table = json.load(open(ROOT, encoding="utf-8"))

def key_of(s):
    s = (s or "").split("?")[0]
    return s.rsplit("/", 1)[-1] if s else ""

nospeech = [it for it in idx["items"] if it.get("no_speech")]
print("无语音记录", len(nospeech))

changed = 0
for ns in nospeech:
    mid = key_of(ns.get("src", ""))
    title = (ns.get("title") or "")[:20]
    for e in table["items"]:
        hit_mid = mid and mid in (e.get("链接") or "")
        hit_title = title and (e.get("名称") or "")[:20] == title
        if hit_mid or hit_title:
            if not (e.get("状态") or "").startswith("无对白"):
                e["状态"] = "无对白（跳过）"
                note = e.get("备注") or ""
                if "纯音乐/无对白" not in note:
                    e["备注"] = (note + "｜纯音乐/无对白，已跳过").strip("｜")
                changed += 1
            break

table["count"] = len(table["items"])
json.dump(table, open(ROOT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("标记", changed, "条")

import subprocess
import sys
subprocess.call([sys.executable, "-X", "utf8",
                 os.path.join(os.path.dirname(os.path.abspath(__file__)), "slim_root_table.py")])
