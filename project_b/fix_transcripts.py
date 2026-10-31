"""转写后处理：繁→简 + 固定错名纠正，输出 _转写_修正.txt"""
import glob, os, re

import opencc

BASE = r"E:\wx\私有\王晰全文库\采访目录\全文"
cc = opencc.OpenCC("t2s")

FIX = [
    (r"王熙|王晰晰|王西", "王晰"),
    (r"希哥|晰哥儿", "晰哥"),
    (r"東方影響家|东方影响家|东方向往家", "东方艺享家"),
    (r"沈想与长歌|沉想与长歌|陈响与长歌", "沉响与长歌"),
    (r"聲入人心|声入人新", "声入人心"),
    (r"嘠达梅林|嘎达梅林", "嘎达梅林"),
    (r"乌苏里船歌|烏蘇里船歌", "乌苏里船歌"),
    (r"花儿为什么这样红|花儿为什么这样红", "花儿为什么这样红"),
]

n = 0
for f in sorted(glob.glob(os.path.join(BASE, "*_转写.txt"))):
    raw = open(f, encoding="utf-8", errors="ignore").read()
    head, _, body = raw.partition("\n\n")
    body = cc.convert(body)
    for pat, rep in FIX:
        body = re.sub(pat, rep, body)
    out = f.replace("_转写.txt", "_转写_修正.txt")
    open(out, "w", encoding="utf-8").write(head.replace("转写：faster-whisper small",
                                                        "转写：faster-whisper small；已繁转简+错名纠正") +
                                          "\n\n" + body)
    n += 1
    print("%-44s %6d → %6d 字" % (os.path.basename(out)[:44], len(raw), len(body)))
print("处理", n, "个转写")
