"""字幕 OCR 清洗 + 与 ASR 对齐（v2：强过滤拉丁乱码/水印）

用法：python -X utf8 project_b/merge_subtitle_asr.py <字幕json> <ASR转写txt> <输出前缀>
"""
import json
import os
import re
import sys

sub_json, asr_txt, prefix = sys.argv[1], sys.argv[2], sys.argv[3]
subs = json.load(open(sub_json, encoding="utf-8"))

CJK = re.compile(r"[\u4e00-\u9fff]")
WATER = ["音乐流水纪", "音乐流纪", "流水纪", "音乐财经", "音乐编程", "音乐制造", "音乐创世纪",
         "点赞", "分享", "赞赏", "关注", "订阅", "NAKED", "GOLD", "LUMIX", "DRAFT", "Preliminary"]
FIX = [("太家好", "大家好"), ("不筑", "不说"), ("王娇", "王晰"), ("王听", "王晰"),
       ("听晓", "王晰"), ("雷美天", "雷美替胺"), ("藏枪", "藏腔")]


def usable(t):
    if len(t) < 5:
        return False
    cjk = len(CJK.findall(t))
    if cjk < 4:
        return False
    # 拉丁/数字/符号占比过高 → 丢
    if cjk / max(len(t), 1) < 0.55:
        return False
    if re.search(r"[_=<>\\/]{2,}|LH\d|F\(\d", t):
        return False
    return True


clean = []
for r in subs:
    t = r["text"]
    for a, b in FIX:
        t = t.replace(a, b)
    for w in WATER:
        t = t.replace(w, "")
    t = re.sub(r"\s{2,}", " ", t).strip(" 丨|·-—、,，")
    if not usable(t):
        continue
    clean.append({"t": r["t"], "text": t})

merged = []
for c in clean:
    if merged:
        last = merged[-1]
        if c["text"] == last["text"] or c["text"] in last["text"]:
            continue
        if c["t"] - last["t"] <= 1 and last["text"] in c["text"]:
            merged[-1] = c
            continue
    merged.append(c)

asr = []
for line in open(asr_txt, encoding="utf-8", errors="ignore"):
    m = re.match(r"^\[(\d{2}):(\d{2})\]\s*(.+)$", line.strip())
    if m:
        asr.append({"t": int(m.group(1)) * 60 + int(m.group(2)), "text": m.group(3)})

base = os.path.splitext(asr_txt)[0]
out_canon = base + "_字幕校正版.txt"
out_diff = base + "_字幕vs转写_差异.md"

with open(out_canon, "w", encoding="utf-8") as f:
    f.write("来源：B站 BV1GJFYeuEpb 硬字幕 OCR｜原始 %d 条 → 清洗后 %d 条\n\n" % (len(subs), len(merged)))
    for c in merged:
        mm, ss = int(c["t"]) // 60, int(c["t"]) % 60
        f.write("[%02d:%02d] %s\n" % (mm, ss, c["text"]))

diff = []
for c in merged:
    if not asr:
        break
    a = min(asr, key=lambda x: abs(x["t"] - c["t"]))
    if abs(a["t"] - c["t"]) <= 3 and a["text"].strip() != c["text"].strip():
        diff.append((c["t"], c["text"], a["text"]))

with open(out_diff, "w", encoding="utf-8") as f:
    f.write("# 字幕 vs 转写（差异 %d 处，按时间）\n\n" % len(diff))
    f.write("| 时间 | 字幕(OCR) | 转写(ASR) |\n|---|---|---|\n")
    for t, s, a in diff[:300]:
        f.write("| %02d:%02d | %s | %s |\n" % (t // 60, t % 60, s.replace("|", "／"), a.replace("|", "／")))

print("清洗后 %d 条｜差异 %d 处" % (len(merged), len(diff)))
print(out_canon)
print(out_diff)
