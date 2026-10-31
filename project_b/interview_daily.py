"""每日采访/杂志巡检 → 汇总根表 + 站内通知

渠道（本地 cookie/公开接口）：
  1. 微博搜索：采访 / 专访 / 杂志 / 封面 / 内页（王晰）
  2. 微博大号「王晰Elvis-晰息相关」增量扫（杂志预告）
  3. 已有待补项的全文重试（有链接且未抓到的）
输出：
  E:\\wx\\私有\\王晰全文库\\采访目录\\采访杂志根表.json / .md
  E:\\wx\\私有\\王晰全文库\\采访目录\\待人工清单.md
通知：project_b/notify.record（站内通告）
"""
import json, os, re, ssl, time, urllib.parse, urllib.request
from datetime import date

BASE = r"E:\wx\私有\王晰全文库\采访目录"
ROOT_TABLE = os.path.join(BASE, "采访杂志根表.json")
TODO = os.path.join(BASE, "待人工清单.md")
FULLDIR = os.path.join(BASE, "全文")
os.makedirs(FULLDIR, exist_ok=True)

WB_CK = r"E:\wx\index_records\wb.txt"
XIXI_UID = "7215995153"
QUERIES = ["王晰 采访", "王晰 专访", "王晰 杂志", "王晰 封面"]
MAG = re.compile(r"杂志|封面|内页|写真|专访|采访|访谈|对话|刊")

def sk(path):
    try:
        return open(path, encoding="utf-8", errors="ignore").read().strip()
    except Exception:
        return ""

WBH = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
       "Referer": "https://m.weibo.cn/", "Cookie": sk(WB_CK), "X-Requested-With": "XMLHttpRequest"}
DOU_CK = sk(r"E:\wx\index_records\douban.txt")
if DOU_CK.lower().startswith("cookie:"):
    DOU_CK = DOU_CK.split(":", 1)[1].strip()
DH = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
      "Referer": "https://www.douban.com/", "Cookie": DOU_CK}
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE

def get(url, headers, timeout=25):
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout, context=ctx).read()
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", "ignore")

def text_of(h):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = h.replace("&nbsp;", " ").replace("&quot;", '"').replace("&amp;", "&")
    return "\n".join(x.strip() for x in h.splitlines() if len(x.strip()) >= 8)

def load_table():
    if os.path.exists(ROOT_TABLE):
        return json.load(open(ROOT_TABLE, encoding="utf-8"))
    return {"updated": "", "count": 0,
            "fields": ["名称", "类型", "时间", "链接", "全文路径", "字数", "渠道", "状态", "备注"],
            "items": []}

def key(it):
    return (it.get("名称", "")[:40], it.get("链接", ""))

table = load_table()
seen = {key(it) for it in table["items"]}
new_items = []

def add(名称, 类型, 时间, 链接, 渠道, 状态="待抓", 备注="", body=""):
    k = (名称[:40], 链接)
    if k in seen:
        return
    seen.add(k)
    it = {"名称": 名称.strip()[:80], "类型": 类型, "时间": 时间, "链接": 链接,
          "全文路径": "", "字数": 0, "渠道": 渠道, "状态": 状态, "备注": 备注}
    if body and len(body) >= 60:
        fn = re.sub(r"[\\/:*?\"<>|\s]+", "_", it["名称"])[:50] + ".txt"
        open(os.path.join(FULLDIR, fn), "w", encoding="utf-8").write(
            "名称：%s\n链接：%s\n时间：%s\n\n%s\n" % (it["名称"], 链接, 时间, body))
        it["全文路径"], it["字数"], it["状态"] = fn, len(body), "已存（微博原文）"
    new_items.append(it)

# 1) 微博搜索
for q in QUERIES:
    u = ("https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D1%26q%3D"
         + urllib.parse.quote(q) + "&page_type=searchall")
    try:
        r = json.loads(get(u, WBH))
    except Exception as e:
        print("搜索失败", q, type(e).__name__); continue
    for c in r.get("data", {}).get("cards", []):
        for g in (c.get("card_group") or [c]):
            m = g.get("mblog")
            if not m:
                continue
            txt = re.sub(r"<[^>]+>", "", m.get("text") or "")
            if "王晰" not in txt or not MAG.search(txt):
                continue
            dt = ""
            try:
                import email.utils
                dt = email.utils.parsedate_to_datetime(m.get("created_at", "")).strftime("%Y-%m-%d")
            except Exception:
                pass
            add(txt[:40].replace("\n", " "), "微博", dt,
                "https://m.weibo.cn/detail/%s" % m.get("id"), "微博搜索：%s" % q, body=txt)
    time.sleep(1.2)

# 2) 晰息大号增量（仅取最近一页，避免频繁）
try:
    r = json.loads(get("https://m.weibo.cn/api/container/getIndex?containerid=107603%s" % XIXI_UID, WBH))
    for c in r.get("data", {}).get("cards", []):
        m = c.get("mblog")
        if not m:
            continue
        txt = re.sub(r"<[^>]+>", "", m.get("text") or "")
        if not MAG.search(txt):
            continue
        import email.utils
        try:
            dt = email.utils.parsedate_to_datetime(m.get("created_at", "")).strftime("%Y-%m-%d")
        except Exception:
            dt = ""
        add(txt[:40].replace("\n", " "), "微博", dt,
            "https://m.weibo.cn/detail/%s" % m.get("id"), "晰息相关大号", body=txt)
except Exception as e:
    print("晰息扫描失败", type(e).__name__)

# 3) 待补项重试全文
for it in table["items"] + new_items:
    if it.get("状态", "").startswith("已存") or not it.get("链接"):
        continue
    u = it["链接"]
    try:
        h = get(u, DH if "douban" in u else WBH)
        body = text_of(h)
        if len(body) >= 800:
            fn = re.sub(r"[\\/:*?\"<>|\s]+", "_", it["名称"])[:50] + ".txt"
            open(os.path.join(FULLDIR, fn), "w", encoding="utf-8").write(
                "名称：%s\n链接：%s\n\n%s\n" % (it["名称"], u, body))
            it["全文路径"], it["字数"], it["状态"] = fn, len(body), "已存（自动抓取）"
    except Exception:
        pass

items = table["items"] + new_items
items.sort(key=lambda x: (x.get("时间") or "0000", x.get("名称", "")), reverse=True)
table = {"updated": date.today().isoformat(), "count": len(items),
         "fields": ["名称", "类型", "时间", "链接", "全文路径", "字数", "渠道", "状态", "备注"],
         "note": "每日自动巡检（微博搜索 + 晰息大号 + 待补重试）；全文落本地私有库",
         "items": items}
json.dump(table, open(ROOT_TABLE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

md = ["# 王晰 采访/杂志 根表", "", "更新：%s ｜ 共 %d 条" % (table["updated"], table["count"]), "",
      "| 时间 | 名称 | 类型 | 渠道 | 状态 | 链接 |", "|---|---|---|---|---|---|"]
for it in items:
    md.append("| %s | %s | %s | %s | %s | %s |" % (it["时间"] or "—", it["名称"][:36], it["类型"],
                                                    it["渠道"][:18], it["状态"], it["链接"][:60]))
open(os.path.join(BASE, "采访杂志根表.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")

todo = [it for it in items if not it.get("状态", "").startswith("已存")]
with open(TODO, "w", encoding="utf-8") as f:
    f.write("# 待人工清单（%d 条）\n\n需要手动打开/搜索的条目，按时间倒序：\n\n" % len(todo))
    for it in todo:
        f.write("- [%s] %s（%s）→ %s\n" % (it["时间"] or "—", it["名称"][:60], it["渠道"], it["链接"]))

print("根表 %d 条（新增 %d）｜待人工 %d｜已存全文 %d"
      % (len(items), len(new_items), len(todo),
         sum(1 for it in items if it.get("状态", "").startswith("已存"))))

try:
    import sys
    sys.path.insert(0, r"D:\wx409.github.io")
    from project_b import notify  # type: ignore
except Exception:
    try:
        sys.path.insert(0, r"D:\wx409.github.io\project_b")
        import notify  # type: ignore
    except Exception:
        notify = None

if notify:
    notify.record("采访/杂志日报 %s" % table["updated"],
                  "根表 %d 条（今日新增 %d）｜待人工 %d 条｜已存全文 %d 条"
                  % (len(items), len(new_items), len(todo),
                     sum(1 for it in items if it.get("状态", "").startswith("已存"))))
    print("已发站内通知")
