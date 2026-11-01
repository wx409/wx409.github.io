"""说话人切分 v2：用「轮次交替 + 上下文」修正未定段

改进点：
  1. 短附和（<12 字且只含对/嗯/是/好）→ 归给上一位说话者
  2. 未定段若前后都是同一人 → 判给该人
  3. 未定段若含「你/您」→ 主持人；含「我」≥1 且无「你」→ 王晰
"""
import os
import re
import sys

path = sys.argv[1]
lines = [l for l in open(path, encoding="utf-8", errors="ignore").read().splitlines() if l.startswith("[")]

paras, cur, cur_t, prev_t = [], [], None, None
for l in lines:
    m = re.match(r"^\[(\d{2}):(\d{2})\]\s*(.*)$", l)
    if not m:
        continue
    t = int(m.group(1)) * 60 + int(m.group(2))
    txt = m.group(3).strip()
    if cur and (t - (prev_t or t) > 3 or sum(len(x) for x in cur) > 150):
        paras.append([cur_t, "".join(cur), None])
        cur, cur_t = [], None
    if not cur:
        cur_t = "%02d:%02d" % (t // 60, t % 60)
    cur.append(txt)
    prev_t = t
if cur:
    paras.append([cur_t, "".join(cur), None])

HOST_W = ["您", "请问", "能不能", "是不是", "对吧", "想问", "介绍一下", "好不好", "可以吗"]
GUEST_W = ["我的", "我当时", "我觉得", "其实我", "然后我", "因为我", "我就", "我们"]

for p in paras:
    body = p[1]
    h = sum(body.count(k) for k in HOST_W)
    if body.count("你") >= 2 or re.search(r"那在|是不是|你觉得|你当时|你是", body):
        h += 2
    g = body.count("我")
    if body.rstrip().endswith(("？", "?")):
        p[2] = "主持"
    elif h >= 1 and g >= 3:
        p[2] = "混合"
    elif h >= 1:
        p[2] = "主持"
    elif g >= 2:
        p[2] = "王晰"
    else:
        p[2] = None

# 短附和归上一说话者
for i, p in enumerate(paras):
    if p[2] is None and len(p[1]) < 14 and re.fullmatch(r"[对嗯啊是好谢哈，。！~\s]+", p[1]):
        for j in range(i - 1, -1, -1):
            if paras[j][2] in ("王晰", "主持"):
                p[2] = paras[j][2]
                break

# 前后同人 → 判给该人
for i, p in enumerate(paras):
    if p[2] is not None:
        continue
    prev_c = next((paras[j][2] for j in range(i - 1, -1, -1) if paras[j][2] in ("王晰", "主持")), None)
    next_c = next((paras[j][2] for j in range(i + 1, len(paras)) if paras[j][2] in ("王晰", "主持")), None)
    if prev_c and prev_c == next_c:
        p[2] = prev_c
    elif prev_c or next_c:
        body = p[1]
        if "你" in body or "您" in body:
            p[2] = "主持"
        elif "我" in body:
            p[2] = "王晰"

buckets = {"王晰": [], "主持": [], "混合": [], None: []}
for p in paras:
    buckets[p[2]].append((p[0], p[1]))

base = os.path.splitext(path)[0]


def dump(suffix, title, rows):
    out = base + "_%s.md" % suffix
    with open(out, "w", encoding="utf-8") as f:
        f.write("# %s（%d 段）\n\n" % (title, len(rows)))
        for t, body in rows:
            f.write("## [%s]\n\n%s\n\n" % (t, body))
    return out

dump("王晰", "判定为王晰", buckets["王晰"])
dump("主持人", "判定为主持人", buckets["主持"])
dump("混合", "混合", buckets["混合"])
dump("未定", "仍未定", buckets[None])
print("段落 %d｜王晰 %d｜主持 %d｜混合 %d｜未定 %d"
      % (len(paras), len(buckets["王晰"]), len(buckets["主持"]), len(buckets["混合"]), len(buckets[None])))
