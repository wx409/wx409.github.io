"""清理曲库里的 N: 占位条目：同名已有 L: 真 mid 的，删掉占位

（N:xxx 是历史遗留的「只有歌名」条目，会造成曲库虚高、可播率虚低）
"""
import json
import re

P = r"D:\wx409.github.io\tavern\songs_compact.json"
d = json.load(open(P, encoding="utf-8"))
items = d["songs"] if isinstance(d, dict) and "songs" in d else d
print("清理前", len(items))


def norm(s):
    t = str(s or "").split("\n")[0]
    t = re.sub(r"(王晰|Elvis\s*Wang|张韶涵|刘也|郑云龙|阿云嘎)", "", t, flags=re.I)
    return re.sub(r"[\s《》()（）\-—·/]", "", t).lower()


real = {norm(x.get("name")) for x in items if str(x.get("uid", "")).startswith("L:")}
kept, dropped = [], 0
for x in items:
    uid = str(x.get("uid", ""))
    if uid.startswith("N:") and norm(x.get("name")) in real:
        dropped += 1
        continue
    kept.append(x)

if isinstance(d, dict):
    d["songs"] = kept
    d["count"] = len(kept)
json.dump(d, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("删除同名占位 %d 条 → 现 %d 条" % (dropped, len(kept)))

import collections
c = collections.Counter(str(x.get("uid"))[:2] for x in kept)
print("uid 分布", c.most_common())
