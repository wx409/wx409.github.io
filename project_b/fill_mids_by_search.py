"""用 QQ 音乐搜索补 mid（v2：修正搜索接口参数 + 清洗带换行/歌手的曲名）"""
import json
import re
import time
import urllib.parse
import urllib.request

COMPACT = r"D:\wx409.github.io\tavern\songs_compact.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
CK = open(r"E:\wx\index_records\qqmusic.txt", encoding="utf-8", errors="ignore").read().strip()
H = {"User-Agent": UA, "Referer": "https://y.qq.com/", "Cookie": CK, "Content-Type": "application/json"}


def search(q):
    payload = {"comm": {"ct": 19, "cv": 1859, "uin": "0"},
               "req": {"module": "music.search.SearchCgiService", "method": "DoSearchForQQMusicDesktop",
                       "param": {"num_per_page": 8, "page_num": 1, "query": q, "search_type": 0}}}
    req = urllib.request.Request("https://u.y.qq.com/cgi-bin/musicu.fcg",
                                 data=json.dumps(payload).encode(), headers=H)
    r = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore"))
    body = (((r.get("req") or {}).get("data") or {}).get("body") or {})
    lst = (body.get("song") or {}).get("list") or []
    return [{"mid": s.get("mid"), "name": s.get("name"),
             "singer": "/".join(x.get("name", "") for x in (s.get("singer") or []))} for s in lst]


def playable(mid):
    try:
        r = json.loads(urllib.request.urlopen(
            "http://127.0.0.1:8787/vkey?mid=" + urllib.parse.quote(mid), timeout=15).read().decode())
        return bool((r.get("urls") or [""])[0])
    except Exception:
        return False


def clean_name(s):
    s = str(s or "").split("\n")[0].split("\r")[0].strip()
    s = re.sub(r"[（(].*?[)）]", "", s)
    s = re.sub(r"(王晰|Elvis\s*Wang)", "", s, flags=re.I)
    return re.sub(r"[\s/、,，·・]+$", "", s).strip()


def norm(s):
    return re.sub(r"[\s《》「」·・,，.。'\"\-/、]", "", str(s or "")).lower()


d = json.load(open(COMPACT, encoding="utf-8"))
items = d["songs"] if isinstance(d, dict) and "songs" in d else d
todo = [x for x in items if not str(x.get("uid", "")).startswith("L:")]
print("待补", len(todo))

fixed = failed = 0
for x in todo:
    nm = clean_name(x.get("name"))
    if not nm:
        continue
    try:
        cands = search("王晰 " + nm)
    except Exception:
        failed += 1
        continue
    hit = None
    for c in cands:
        if c["mid"] and "王晰" in c["singer"] and norm(c["name"]) == norm(nm):
            hit = c
            break
    if not hit:
        hit = next((c for c in cands if c["mid"] and "王晰" in c["singer"]), None)
    if not hit or not playable(hit["mid"]):
        print("  ✗", nm[:20], "（搜到但不可播）" if hit else "（无结果）")
        failed += 1
        continue
    x["uid"] = "L:" + hit["mid"]
    fixed += 1
    print("  ✓", nm[:18], "→", hit["name"][:18], hit["mid"])
    time.sleep(0.35)

json.dump(d, open(COMPACT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n补全 %d｜仍失败 %d" % (fixed, failed))
