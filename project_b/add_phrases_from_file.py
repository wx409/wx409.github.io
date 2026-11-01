"""从「文本/切分结果」入池：一句话一行或 `## [时间码]` 段落都能处理

用法：
  python -X utf8 project_b/add_phrases_from_file.py --file "…_王晰.md" --source "东方艺享家 2026-06-17" --type interview
  python -X utf8 project_b/add_phrases_from_file.py --file notes.txt --source "手摘金句" --type interview --quality high --rights free

说明：
  · 自动切句（。！？；），只收 12–60 字、含第一人称或观点词的句子
  · 去重（与库内已有句子比对）
  · 默认 quality=mid（待校对），明确可信时用 --quality high
"""
import argparse
import json
import re
from collections import Counter

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
DICE = r"D:\wx409.github.io\data\dice_sets.json"

KEEP = re.compile(r"[我咱]|其实|觉得|因为|所以|但是|希望|认为|坚持|理解|明白|选择|相信")
TRUNC = set("在的了我你他们和跟就都也还但而如果因所以为与以及")


def extract(text):
    out = []
    for sec in re.split(r"^##\s*", text, flags=re.M):
        body = "\n".join(l for l in sec.splitlines() if not l.startswith("#")).strip()
        if not body:
            continue
        for s in re.split(r"[。！？；\n]", body):
            s = re.sub(r"\s+", "", s).strip("，、 ")
            if not (12 <= len(s) <= 60):
                continue
            if s[-1] in TRUNC:
                continue
            if not KEEP.search(s):
                continue
            out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--type", default="interview", choices=["interview", "talk", "lyrics", "mystic", "song"])
    ap.add_argument("--quality", default="mid", choices=["high", "mid", "low"])
    ap.add_argument("--rights", default="free")
    ap.add_argument("--mood", default="")
    a = ap.parse_args()

    text = open(a.file, encoding="utf-8", errors="ignore").read()
    cands = extract(text)

    bank = json.load(open(BANK, encoding="utf-8"))
    exist = {re.sub(r"\s", "", i["text"]) for i in bank["items"]}
    added = 0
    for s in cands:
        if s in exist:
            continue
        exist.add(s)
        bank["items"].append({
            "text": s, "type": a.type, "source": a.source,
            "curated": a.quality == "high", "rights": a.rights,
            "mood": a.mood or a.type, "verified": a.quality == "high",
            "quality": a.quality,
        })
        added += 1

    bank["count"] = len(bank["items"])
    bank["by_type"] = dict(Counter(i["type"] for i in bank["items"]))
    bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
    json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("候选 %d｜入池 %d（%s / quality=%s）｜现共 %d"
          % (len(cands), added, a.type, a.quality, bank["count"]))
    print("下一步：python -X utf8 project_b/rebuild_dice_sets.py 或 build_phrases_page.py")


if __name__ == "__main__":
    main()
