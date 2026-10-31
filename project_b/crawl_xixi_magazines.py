"""搜「晰息」相关微博账号 → 抓其微博 → 抽杂志相关帖（预告/封面/期号）"""
import json, re, time, urllib.request, urllib.parse, email.utils

CK = open(r"E:\wx\index_records\wb.txt", encoding="utf-8").read().strip()
H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
     "Referer": "https://m.weibo.cn/", "Cookie": CK, "X-Requested-With": "XMLHttpRequest"}

def api(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=25).read().decode("utf-8", "ignore"))

# 1) 搜账号
users = {}
for q in ("晰息", "晰息TV"):
    u = "https://m.weibo.cn/api/container/getIndex?containerid=100103type%%3D3%%26q%%3D%s&page_type=searchall" % urllib.parse.quote(q)
    try:
        r = api(u)
    except Exception as e:
        print("搜", q, "失败", type(e).__name__); continue
    for c in r.get("data", {}).get("cards", []):
        for g in (c.get("card_group") or []):
            us = g.get("user") or {}
            if us.get("screen_name"):
                users[us["id"]] = us["screen_name"]
    time.sleep(1)

print("账号候选", len(users))
for uid, name in list(users.items())[:10]:
    print("  ", uid, name)

MAG = re.compile(r"杂志|封面|预售|开售|期|刊|写真|专访|内页|随刊|芭莎|ELLE|男人装|新周刊|北京青年|时尚|瑞丽|嘉人|红秀|OK!|风度|时装|乐活|南都|三联|人物")
hits = []
for uid, name in users.items():
    since = None
    for page in range(0, 40):
        u = "https://m.weibo.cn/api/container/getIndex?containerid=107603%s" % uid
        if since:
            u += "&since_id=%s" % since
        try:
            r = api(u)
        except Exception:
            break
        cards = r.get("data", {}).get("cards", [])
        if not cards:
            break
        got = 0
        for c in cards:
            m = c.get("mblog")
            if not m:
                continue
            got += 1
            txt = re.sub(r"<[^>]+>", "", m.get("text") or "")
            if MAG.search(txt):
                try:
                    dt = email.utils.parsedate_to_datetime(m.get("created_at", "")).strftime("%Y-%m-%d")
                except Exception:
                    dt = ""
                hits.append({"uid": uid, "account": name, "date": dt, "text": txt[:220],
                             "pics": [p.get("large", {}).get("url") or p.get("url") for p in (m.get("pics") or [])]})
        since = r.get("data", {}).get("cardlistInfo", {}).get("since_id")
        if not since:
            break
        time.sleep(0.8)
        if page > 25:
            break

print("杂志相关帖", len(hits))
for h in hits[:15]:
    print("  ", h["date"], h["account"], "|", h["text"][:60].replace("\n", " "))

out = r"E:\wx\私有\王晰全文库\采访目录\杂志预告帖.json"
json.dump({"generated": "2026-10-31", "count": len(hits), "accounts": users, "items": hits},
          open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("已存", out)
