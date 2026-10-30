"""语料去重：按正文哈希分组，把重复文件移入 _dupes/（不删除），并记录映射。
用法：python -X utf8 project_b/dedupe_weibo_corpus.py [--dry]
"""
import hashlib, json, os, re, shutil, sys

CORPUS = r"E:\wx\wx_textmine_corpus"
DIRS = ["本人微博", "工作室微博", "少城时代"]
MAP = os.path.join(CORPUS, "_dupes_map.json")

def norm(path):
    t = open(path, encoding="utf-8", errors="ignore").read()
    t = re.sub(r"\s+", "", t)
    return t

def main(dry):
    mapping, kept, moved = {}, 0, 0
    for d in DIRS:
        base = os.path.join(CORPUS, d)
        if not os.path.isdir(base):
            continue
        seen = {}
        dupe_dir = os.path.join(r"E:\wx\wx_textmine_dupes", d)
        os.makedirs(dupe_dir, exist_ok=True)
        for f in sorted(os.listdir(base)):
            if not f.endswith(".txt"):
                continue
            p = os.path.join(base, f)
            h = hashlib.sha1(norm(p).encode("utf-8")).hexdigest()
            if h in seen:
                mapping[os.path.join(d, f)] = os.path.join(d, seen[h])
                moved += 1
                if not dry:
                    shutil.move(p, os.path.join(dupe_dir, f))
            else:
                seen[h] = f
                kept += 1
        print("%s: 保留 %d｜重复 %d" % (d, len(seen), moved))
    if not dry:
        json.dump(mapping, open(MAP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("合计|唯一 %d｜重复 %d｜映射 %s" % (kept, moved, MAP if not dry else "(dry)"))

if __name__ == "__main__":
    main("--dry" in sys.argv)
