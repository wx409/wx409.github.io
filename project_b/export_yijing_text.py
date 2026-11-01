"""导出「周易原文」到 data/hexagrams_full.json（修正：键是整数；卦名需繁简转换）"""
import json
import os
import pickle

import ichingshifa
import opencc

PKG = os.path.dirname(ichingshifa.__file__)
DETAIL = pickle.load(open(os.path.join(PKG, "data.pkl"), "rb"))["易經卦爻詳解"]
S2T = opencc.OpenCC("s2t")

OURS = r"D:\wx409.github.io\data\hexagrams.json"
OUT = r"D:\wx409.github.io\data\hexagrams_full.json"

TRIGS = ["乾", "兑", "离", "震", "巽", "坎", "艮", "坤"]
MATRIX = {
    "乾": ["乾", "履", "同人", "无妄", "姤", "讼", "遁", "否"],
    "兑": ["夬", "兑", "革", "随", "大过", "困", "咸", "萃"],
    "离": ["大有", "睽", "离", "噬嗑", "鼎", "未济", "旅", "晋"],
    "震": ["大壮", "归妹", "丰", "震", "恒", "解", "小过", "豫"],
    "巽": ["小畜", "中孚", "家人", "益", "巽", "涣", "渐", "观"],
    "坎": ["需", "节", "既济", "屯", "井", "坎", "蹇", "比"],
    "艮": ["大畜", "损", "贲", "颐", "蛊", "蒙", "艮", "剥"],
    "坤": ["泰", "临", "明夷", "复", "升", "师", "谦", "坤"],
}

ours = json.load(open(OURS, encoding="utf-8"))
merged, missing = {}, []

for up in TRIGS:
    for i, low in enumerate(TRIGS):
        short = MATRIX[up][i]
        rec = (ours.get(up) or {}).get(low) or {}
        d = DETAIL.get(S2T.convert(short)) or DETAIL.get(short)
        if not d:
            missing.append(short)
            continue
        merged.setdefault(up, {})[low] = {
            "full": rec.get("name", short),
            "short": short,
            "virtue": rec.get("virtue", ""),
            "guaci": d.get(0, ""),
            "yaoci": [d.get(n, "") for n in range(1, 7)],
            "tuan": d.get(7, ""),
            "our_text": rec.get("text", ""),
        }

json.dump(merged, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("导出 %d 卦｜缺失 %d %s" % (sum(len(v) for v in merged.values()), len(missing), missing))

for up, low, label in (("坎", "震", "水雷屯"), ("乾", "乾", "乾为天"), ("坤", "乾", "地天泰")):
    k = merged[up][low]
    print("\n%s（%s）：" % (label, k["full"]))
    print("  卦辞:", k["guaci"][:56])
    print("  初爻:", k["yaoci"][0][:48])
