"""启发式说话人切分（无 diarization）：把他/主持人/未定分开

用法：python -X utf8 project_b/split_speakers.py "<转写文件>"
输出：同目录 <name>_王晰.md / <name>_主持人.md / <name>_未定.md

判定依据（可解释，非黑箱）：
  主持人：出现「您 / 请问 / 能不能 / 是不是 / 对吧 / 呢？/ 想问 / 我们想听 / 介绍一下」
          或整段以问号结尾
  王晰  ：第一人称「我/我的/我当时/我觉得」≥2 次，且无主持人线索
  其他  ：两者都不满足 → 未定（不猜）
"""
import os
import re
import sys

path = sys.argv[1]
lines = [l for l in open(path, encoding="utf-8", errors="ignore").read().splitlines() if l.startswith("[")]

# 合并成段（间隔 >2.5s 或 >150 字）
paras = []
cur, cur_t, prev_t = [], None, None
for l in lines:
    m = re.match(r"^\[(\d{2}):(\d{2})\]\s*(.*)$", l)
    if not m:
        continue
    t = int(m.group(1)) * 60 + int(m.group(2))
    txt = m.group(3).strip()
    if cur and (t - (prev_t or t) > 3 or sum(len(x) for x in cur) > 150):
        paras.append((cur_t, "".join(cur)))
        cur, cur_t = [], None
    if not cur:
        cur_t = "%02d:%02d" % (t // 60, t % 60)
    cur.append(txt)
    prev_t = t
if cur:
    paras.append((cur_t, "".join(cur)))

HOST = ["您", "请问", "能不能", "是不是", "对吧", "想问", "我们想听", "介绍一下",
        "好不好", "可以吗", "跟大家", "观众", "听众", "网友", "请问一下"]
GUEST = ["我的", "我当时", "我觉得", "其实我", "然后我", "因为我", "我就", "我们当时"]

host, guest, unknown, mixed = [], [], [], []
for t, body in paras:
    h = sum(body.count(k) for k in HOST)
    g = body.count("我") + sum(body.count(k) for k in GUEST)
    if body.rstrip().endswith(("？", "?")):
        host.append((t, body))
        continue
    # 「你」密集且出现提问套路 → 主持人（他自述时几乎不用「你」）
    if body.count("你") >= 2 or re.search(r"那在|是不是|你觉得|你当时|你是|你跟|你的这张", body):
        h += 2
    if h >= 1 and g >= 3:
        mixed.append((t, body))      # 同段既有提问又有自述：不硬分
    elif h >= 1:
        host.append((t, body))
    elif g >= 2:
        guest.append((t, body))
    else:
        unknown.append((t, body))

base = os.path.splitext(path)[0]


def dump(suffix, title, rows):
    out = base + "_%s.md" % suffix
    with open(out, "w", encoding="utf-8") as f:
        f.write("# %s（%d 段）\n\n" % (title, len(rows)))
        for t, body in rows:
            f.write("## [%s]\n\n%s\n\n" % (t, body))
    return out

a = dump("王晰", "判定为王晰（第一人称自述）", guest)
b = dump("主持人", "判定为主持人（提问/介绍）", host)
c = dump("未定", "未定（两类线索都不足，未猜）", unknown)
_m = dump("混合", "混合（同段既有提问又有自述，不硬分）", mixed)
print("段落 %d｜王晰 %d｜主持人 %d｜混合 %d｜未定 %d" % (len(paras), len(guest), len(host), len(mixed), len(unknown)))
print("输出：\n  %s\n  %s\n  %s" % (a, b, c))
for t, body in guest[:2]:
    print("\n[王晰][%s] %s" % (t, body[:110]))
for t, body in host[:1]:
    print("[主持人][%s] %s" % (t, body[:110]))
