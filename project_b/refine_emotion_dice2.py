"""情绪骰面终版：ASR 重复字折叠 + 去掉明显截断，挑选 6 面"""
import glob, json, os, re

ROOT = r"D:\wx409.github.io"
TALK_DIR = r"E:\wx\论文素材_王晰作传\现场talk"
BANK = os.path.join(ROOT, "data", "phrase_bank.json")
DICE = os.path.join(ROOT, "data", "dice_sets.json")

def clean(t):
    t = re.sub(r"(.)\1{2,}", r"\1\1", t)          # 三个以上重复 → 两个
    t = re.sub(r"^这个|^那个|^然后|^其实", "", t)
    t = re.sub(r"(非常|特别|真的)$", "", t)
    return t.strip()

MARK = re.compile(r"(?:嗯+|然后|所以|但是|其实|我觉得|就是说|你知道吗|对吧|是吧|真的|谢谢|因为|就是|对啊|你看|我跟你说|那个时候|感谢)")
BAD_END = set("的但在我你他就也还 把被让给对和跟从到一是在那这说有着了过非常特别真")
EMO = ["谢谢", "感谢", "开心", "希望", "温暖", "幸福", "喜欢", "珍惜", "记得", "陪伴", "勇敢", "相信", "感动", "努力", "非常"]

def split(text):
    out = []
    for p in MARK.split(text or ""):
        p = clean(re.sub(r"[\s\dA-Za-z，。！？、；：\"'（）()…—\-]+", "", p or ""))
        if not (12 <= len(p) <= 28) or p[-1] in BAD_END:
            continue
        if not re.search(r"[我你咱]", p):
            continue
        if len(re.findall(r"[\u4e00-\u9fff]", p)) < len(p) * 0.95:
            continue
        out.append(p)
    return out

bank = json.load(open(BANK, encoding="utf-8"))
items = [it for it in bank["items"] if it["type"] != "talk"]
seen = set()
for f in sorted(glob.glob(os.path.join(TALK_DIR, "**", "*.txt"), recursive=True)):
    rel = os.path.relpath(f, TALK_DIR)
    city = rel.split(os.sep)[0] if os.sep in rel else ""
    for s in split(open(f, encoding="utf-8", errors="ignore").read()):
        if s in seen:
            continue
        seen.add(s)
        items.append({"text": s, "type": "talk", "source": "%s｜%s" % (city, os.path.basename(f)[:36]),
                      "curated": False, "rights": "free", "mood": "talk", "verified": False})

from collections import Counter
stat = Counter(it["type"] for it in items)
json.dump({"generated": "2026-10-31", "count": len(items), "by_type": dict(stat), "note": bank.get("note")},
          open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("phrase_bank:", len(items), dict(stat))

talks = [it["text"] for it in items if it["type"] == "talk"]
talks.sort(key=lambda t: (sum(2 for k in EMO if k in t), 1 if 16 <= len(t) <= 26 else 0), reverse=True)
faces = talks[:6]
dice = json.load(open(DICE, encoding="utf-8"))
dice["sets"]["emotion"]["faces"] = faces
dice["sets"]["emotion"]["face_count"] = len(faces)
json.dump(dice, open(DICE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for f in faces:
    print("  ", f)
