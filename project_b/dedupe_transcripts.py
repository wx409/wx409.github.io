"""转写文件去重与规范化

规则：
  - 按 mid（或标题前 30 字）分组
  - 每组保留「turbo > small」、同模型取最新，其余移到 全文_重复归档\
  - 保留文件统一改名 <mid|slug>_转写_<model>.txt
"""
import glob
import json
import os
import re
import shutil

T = r"E:\wx\私有\王晰全文库\采访目录\全文"
ARCH = r"E:\wx\私有\王晰全文库\采访目录\全文_重复归档"
os.makedirs(ARCH, exist_ok=True)


def key_of(name):
    m = re.match(r"(\d{15,20})_", name)
    if m:
        return m.group(1)
    return re.sub(r"_转写.*", "", name)[:30]


def model_of(path):
    head = open(path, encoding="utf-8", errors="ignore").read(300)
    m = re.search(r"模型：faster-whisper (\w[\w\-]*)", head)
    return m.group(1) if m else "small"


groups = {}
for f in glob.glob(os.path.join(T, "*转写*.txt")):
    groups.setdefault(key_of(os.path.basename(f)), []).append(f)

kept = moved = renamed = 0
for k, files in groups.items():
    # 排序：turbo 优先，其次文件较新
    files.sort(key=lambda p: (0 if model_of(p) == "turbo" else 1, -os.path.getmtime(p)))
    best = files[0]
    for other in files[1:]:
        shutil.move(other, os.path.join(ARCH, os.path.basename(other)))
        moved += 1
    model = model_of(best)
    base = os.path.basename(best)
    canon = "%s_转写_%s.txt" % (k, model)
    if base != canon:
        target = os.path.join(T, canon)
        if os.path.exists(target):
            shutil.move(best, os.path.join(ARCH, base))
            moved += 1
            continue
        os.replace(best, target)
        renamed += 1
    kept += 1

print("保留 %d 组｜归档重复 %d 个｜规范化改名 %d 个" % (kept, moved, renamed))
# 索引同步：把指向已归档文件的条目清掉
IDX = r"E:\wx\私有\王晰全文库\采访目录\转写索引.json"
if os.path.exists(IDX):
    idx = json.load(open(IDX, encoding="utf-8"))
    live = {os.path.basename(p) for p in glob.glob(os.path.join(T, "*转写*.txt"))}
    for it in idx["items"]:
        it["exists"] = it.get("out") in live
    json.dump(idx, open(IDX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("索引条目 %d（存在 %d）" % (len(idx["items"]), sum(1 for i in idx["items"] if i.get("exists"))))
