# -*- coding: utf-8 -*-
"""watch_releases.py —— 新歌/专辑/单曲自动监测（diff 驱动）

数据源：QQ 音乐搜索接口（"王晰"），与 songs_meta.json / albums.json 对比。
默认只读输出新增清单；--apply 时自动入库（新增条目 + mid，随后由 fetch_credits_lyrics 补歌词班底）。

纪律：只收录 singer 含"王晰"的条目；伴奏/纯音乐过滤；不覆盖已有数据。
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

ROOT = r"D:\wx409.github.io"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"}
SEARCH_URL = ("https://c.y.qq.com/soso/fcgi-bin/client_search_cp?p=1&n=50&format=json&w=")
# 排除伴奏/纯音乐/节目音频/现场片段（小酒馆由 watch_tavern 单独管）
SKIP = re.compile(r"\(伴奏\)|伴奏版|\(纯音乐\)|Instrumental|\(KTV\)|第\d+期|【睡前故事与酒】|【王晰，请回答】|营业预告|收官福利|片段|生日快乐歌|海底捞", re.I)
LIVE = re.compile(r"\(Live\)|现场版|现场")
# 王晰 8 张专辑名（用于标注 album 归属）
ALBUM_NAMES = ["不说", "X自选集", "回望", "B面图景", "歌颂", "重游往昔", "Low C的诱惑Ⅱ", "Low C的诱惑", "Low C的诱惑2"]


def norm(s):
    return re.sub(r"[\s《》「」『』··]", "", (s or "")).lower()


def qq_search(kw, n=50):
    url = SEARCH_URL + urllib.parse.quote(kw)
    try:
        req = urllib.request.Request(url, headers=UA)
        d = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
        return json.loads(d).get("data", {}).get("song", {}).get("list", [])
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="将新增条目写入 songs_meta.json")
    ap.add_argument("--no-notify", action="store_true", help="不推送微信（由 auto_update 汇总统一推送）")
    ap.add_argument("--out", default=ROOT + r"\data\pending_releases.json",
                    help="只读模式输出路径")
    args = ap.parse_args()

    sm = json.load(open(ROOT + r"\data\songs_meta.json", encoding="utf-8"))
    songs = sm["songs"]
    known = {norm(v.get("name")) for v in songs.values()}

    found = []
    for kw in ("王晰", "王晰 最新", "王晰 单曲"):
        for s in qq_search(kw):
            name = s.get("songname") or ""
            if SKIP.search(name):
                continue
            singers = "、".join(x.get("name", "") for x in s.get("singer", []))
            if "王晰" not in singers:
                continue
            found.append({"name": name, "mid": s.get("songmid"),
                          "singer": singers, "album": s.get("albumname", "")})
        time.sleep(0.5)

    # 去重 + 与已知差集（正式作品与综艺现场版分级）
    seen, fresh, live_fresh = set(), [], []
    for f in found:
        k = (norm(f["name"]), f.get("mid"))
        if k in seen:
            continue
        seen.add(k)
        if norm(f["name"]) in known:
            continue
        (live_fresh if LIVE.search(f["name"]) else fresh).append(f)

    print("检索到王晰条目 %d 条，新增正式作品 %d 条、综艺现场版 %d 条"
          % (len(seen), len(fresh), len(live_fresh)))
    for f in fresh[:20]:
        print("  +", f["name"], "|", f["mid"], "|", f["album"])
    if live_fresh:
        print("  （综艺现场版 %d 条：%s）" % (len(live_fresh),
              "、".join(x["name"][:14] for x in live_fresh[:8])))

    if not args.apply:
        json.dump({"releases": fresh, "live": live_fresh},
                  open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("[只读] 新增清单 -> %s（--apply 只入库正式作品）" % args.out)
        return

    # --apply：自动入库
    n = 0
    added = []
    for f in fresh:
        key = norm(f["name"])
        if key in songs:
            continue
        album = f["album"] if f["album"] in ALBUM_NAMES or "小酒馆" not in f["album"] else None
        songs[key] = {"name": f["name"], "attr": None, "release": "-", "latest": None,
                      "mean30": None, "peak": None, "lyrics": [], "album": album,
                      "show_count": 0, "cities": [], "live": [], "mid": "L:" + f["mid"] if f["mid"] else None}
        added.append(f)
        n += 1
    sm["song_count"] = len(songs)
    json.dump(sm, open(ROOT + r"\data\songs_meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[apply] 已入库 %d 条（歌词/班底由 fetch_credits_lyrics.py 增量补充）" % n)

    # 落盘本次新增清单（无论是否推送），供 auto_update 汇总推送
    json.dump({"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
               "releases": fresh, "live": live_fresh},
              open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if n and not args.no_notify:
        try:
            sys.path.insert(0, ROOT + r"\project_b")
            import notify
            lines = "\n".join("- %s（mid: %s，%s）" % (f["name"], f["mid"], f["album"] or "单曲")
                              for f in added[:10])
            notify.send("🎵 王晰新歌已自动上架 %d 首" % n,
                        "已入库 songs_meta（uid 自动带好）：\n" + lines
                        + ("\n…等" if n > 10 else "")
                        + "\n\n歌词/班底将自动补充，站点已同步更新。")
        except Exception as e:
            print("[notify] 失败:", e)


if __name__ == "__main__":
    main()
