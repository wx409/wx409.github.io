# -*- coding: utf-8 -*-
"""watch_netease.py —— 王晰网易云音乐新歌/新专辑监测（diff 驱动）

数据源：网易云音乐搜索接口（music.163.com 公开 API，无需登录）。
与 data/netease_catalog.json 对比，输出新增条目；--apply 入库。

纪律：只收录 singer 含"王晰"的条目；与 QQ 渠道（watch_releases.py）互补，
      覆盖网易云独家/首发内容。
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "netease_catalog.json"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "http://music.163.com/"}
SEARCH_URL = "http://music.163.com/api/search/get/web?type=1&limit=50&offset=0&s="

# 过滤：综艺现场版/翻唱节目音频（正式作品另过滤）
SKIP = re.compile(r"\(Live\)|live|现场版|第\d+期|伴奏|纯音乐|Instrumental|KTV|Cover", re.I)


def netease_search(kw, limit=50):
    url = SEARCH_URL + urllib.parse.quote(kw)
    try:
        req = urllib.request.Request(url, headers=UA)
        d = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
        return json.loads(d).get("result", {}).get("songs", [])[:limit]
    except Exception:
        return []


def norm(s):
    return re.sub(r"[\s《》「」『』··]", "", (s or "")).lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="入库到 netease_catalog.json")
    args = ap.parse_args()

    # 读旧目录
    cat = {"generated_at": "", "songs": {}}
    if OUT.exists():
        try:
            cat = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            cat = {"generated_at": "", "songs": {}}
    known = {norm(v.get("name")) for v in cat.get("songs", {}).values()}

    # 多关键词检索（王晰 + 组合）
    found = []
    for kw in ("王晰", "王晰 新歌", "王晰 单曲", "王晰 专辑"):
        for s in netease_search(kw):
            name = s.get("name") or ""
            artists = "/".join(a.get("name", "") for a in s.get("artists", []))
            if "王晰" not in artists:
                continue
            found.append({
                "name": name,
                "id": s.get("id"),
                "artists": artists,
                "album": (s.get("album") or {}).get("name", ""),
            })
        time.sleep(0.5)

    # 去重 + 与已知 diff（过滤综艺/翻唱现场版）
    seen, fresh = set(), []
    for f in found:
        k = (norm(f["name"]), f.get("id"))
        if k in seen:
            continue
        seen.add(k)
        if SKIP.search(f["name"]):
            continue
        if norm(f["name"]) in known:
            continue
        fresh.append(f)

    print("网易云检索到王晰条目 %d 条，新增 %d 条" % (len(seen), len(fresh)))
    for f in fresh[:20]:
        print("  +", f["name"], "| 专辑:", f["album"])

    if args.apply:
        songs = cat.setdefault("songs", {})
        for f in fresh:
            songs[norm(f["name"])] = {
                "name": f["name"], "id": f["id"], "artists": f["artists"], "album": f["album"],
            }
        cat["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        OUT.write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[apply] 已入库 %d 条 -> data/netease_catalog.json" % len(fresh))
    else:
        # 只读：仍输出 pending 供查看
        pend = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "rule": "网易云新增候选（只读），--apply 入库", "fresh": fresh}
        (ROOT / "data" / "pending_netease.json").write_text(
            json.dumps(pend, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[只读] 新增清单 -> data/pending_netease.json")

    # 通知（新增时）
    if fresh:
        try:
            sys.path.insert(0, str(ROOT / "project_b"))
            import notify
            lines = "\n".join("- %s（%s）" % (f["name"], f["album"] or "单曲") for f in fresh[:10])
            notify.send("🎵 网易云发现王晰新歌 %d 首" % len(fresh),
                        "网易云新增：\n" + lines
                        + ("\n…等" if len(fresh) > 10 else "")
                        + "\n\n已记录 data/netease_catalog.json（--apply 才入库）。")
        except Exception as e:
            print("[notify] 失败:", e)


if __name__ == "__main__":
    main()
