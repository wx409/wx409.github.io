# -*- coding: utf-8 -*-
"""全面修正六巡广州场：2026-08-23 是已开票待举办的未来场次，不是取消。

错误来源："官宣未举办"被误读为取消；正确语义 = 已官宣、演出日期未到。
"""
import json
import re
import datetime

ROOT = r"D:\wx409.github.io"
NEW_SCENE = "广州（已开票·待举办）"
NEW_NOTE = "已开票·2026-08-23 19:30 广东艺术剧院"

def fix_json(path, fn):
    d = json.load(open(path, encoding="utf-8"))
    d = fn(d)
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[OK]", path)

def fix_text(path, pairs):
    h = open(path, encoding="utf-8").read()
    n = 0
    for old, new in pairs:
        if old in h:
            h = h.replace(old, new)
            n += 1
    open(path, "w", encoding="utf-8").write(h)
    print("[OK]", path, "替换 %d 处" % n)

# 1. cities.json
def f_cities(c):
    for name, v in c.get("cities", {}).items():
        for s in v.get("shows", []):
            if s.get("date") == "2026-08-23" and s.get("city") == "广州" or (
                    s.get("date") == "2026-08-23" and "广州" in (s.get("scene") or "")):
                s["scene"] = NEW_SCENE
                s["note"] = NEW_NOTE
                s["cancelled"] = False
    return c
fix_json(ROOT + r"\data\cities.json", f_cities)

# 2. city_guides.json
def f_cg(g):
    for name, v in g.items():
        if not isinstance(v, dict):
            continue
        for s in v.get("performances", []):
            if s.get("date") == "2026-08-23" and "广州" in (s.get("scene") or "") or \
               (s.get("date") == "2026-08-23" and name == "广州"):
                s["scene"] = NEW_SCENE
                s["cancelled"] = False
    return g
fix_json(ROOT + r"\data\city_guides.json", f_cg)

# 3. setlists.json
def f_sl(d):
    sls = d.get("setlists", d)
    for k, v in sls.items():
        if isinstance(v, dict) and v.get("date") == "2026-08-23":
            v["scene"] = NEW_SCENE
    return d
fix_json(ROOT + r"\data\setlists.json", f_sl)

# 4. timeline.json
def f_tl(lst):
    for t in lst:
        if t.get("date") == "2026-08-23":
            t["title"] = "六巡「回」广州站·已开票待举办（广东艺术剧院 19:30）"
            t["source"] = "官方通告"
    return lst
fix_json(ROOT + r"\data\timeline.json", f_tl)

# 5. live_repos.json
def f_repo(d):
    for date, items in d.get("repos", {}).items():
        for it in items:
            it["title"] = re.sub(r"未举办", "待举办", it.get("title") or "")
            if it.get("note"):
                it["note"] = re.sub(r"官宣后未举办", "已开票·待举办（2026-08-23 演出）", it["note"])
    return d
fix_json(ROOT + r"\data\live_repos.json", f_repo)

# 6. entity_index.json
def f_en(d):
    s = json.dumps(d, ensure_ascii=False)
    s = s.replace("广州（官宣未举办）", NEW_SCENE)
    return json.loads(s)
fix_json(ROOT + r"\entity_index.json", f_en)

# 7. site_search_index.json
fix_text(ROOT + r"\data\site_search_index.json",
         [("广州（官宣未举办）", NEW_SCENE)])

# 8. dashboard_data.json
fix_text(ROOT + r"\dashboard\dashboard_data.json",
         [("广州（官宣未举办）", NEW_SCENE)])

# 9. dashboard/index.html（内嵌数据）
fix_text(ROOT + r"\dashboard\index.html",
         [("广州（官宣未举办）", NEW_SCENE)])

# 10. 首页 FAQ 严重错误文本
fix_text(ROOT + r"\index.html",
         [("六巡「回」第二场原定广州站，2026年8月23日在广东艺术剧院举行，后官方宣布该场未举办。",
           "六巡「回」第二场广州站已开票，2026年8月23日19:30在广东艺术剧院举行（截至 2026-08-16 为待举办状态）。")])

# 11. llms-full.txt
fix_text(ROOT + r"\llms-full.txt",
         [("2026.08.23 广州 广东艺术剧院（官宣未举办）", "2026.08.23 广州 广东艺术剧院（已开票·待举办）")])

# 12. live/index.html
fix_text(ROOT + r"\live\index.html",
         [("广州（官宣未举办）", NEW_SCENE)])

# 13. map/index.html（含 badge）
fix_text(ROOT + r"\map\index.html",
         [("2026-08-23 · 六巡「回」 · <a href=\"/live/hui-回-广州-2026.html\">广东艺术剧院</a> <span class=\"badge cancel\">未举办</span>",
           "2026-08-23 · 六巡「回」 · <a href=\"/live/hui-回-广州-2026.html\">广东艺术剧院</a> <span class=\"badge data\">已开票·待举办</span>"),
          ("(s.cancelled ? '<span class=\"tag cancel\">未举办</span>' : '')",
           "(s.cancelled ? '<span class=\"tag cancel\">未举办</span>' : (s.date >= '2026-08-23' ? '<span class=\"tag data\">已开票·待举办</span>' : ''))")])

# 14. 广州实录页
fix_text(ROOT + r"\live\hui-回-广州-2026.html",
         [("官宣未举办", "已开票·待举办"), ("取消", "待举办")])

print("\n[完成] 六巡广州全面修正为「已开票·待举办」")
