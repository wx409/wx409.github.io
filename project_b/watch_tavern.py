# -*- coding: utf-8 -*-
"""watch_tavern.py —— 日木斤深夜小酒馆新期次自动监测（diff 驱动）

数据源：QQ 专辑 004KBBo20lgZiK（日木斤深夜小酒馆|王晰哄你入睡）歌曲列表。
与 tavern_audio.json / tavern_transcripts.json 对比，输出新增期次；--apply 自动入库。

纪律：节目音频（非歌曲）只进 tavern_audio/tavern_transcripts，不进 songs_meta 的"歌曲"语义。
"""
import argparse
import json
import re
import sys
import time
import urllib.request

ROOT = r"D:\wx409.github.io"
ALBUM_MID = "004KBBo20lgZiK"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"}
# QQ 专辑歌曲列表（musicu.fcg 无需签名即可用）
FCG_URL = ("https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg?songmid={mid}&format=json")


def get_song(mid):
    try:
        req = urllib.request.Request(FCG_URL.format(mid=mid), headers=UA)
        d = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
        j = json.loads(d)
        s = (j.get("data") or [None])[0]
        if s:
            return {"name": s.get("name"), "mid": mid,
                    "duration_sec": s.get("interval") or 0,
                    "album": (s.get("album") or {}).get("name", "")}
    except Exception:
        pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="写入 tavern_audio.json")
    args = ap.parse_args()

    # 现状
    ta = json.load(open(ROOT + r"\data\tavern_audio.json", encoding="utf-8"))
    known = {it.get("mid") for it in ta.get("items", [])}

    # 搜索专辑内全部歌曲（翻页抓全；按专辑 mid 归属 + 曲名特征过滤噪声）
    import urllib.parse
    name_ok = re.compile(r"第\d+期|【睡前故事与酒】|【王晰，请回答】|营业预告|收官福利")
    album_songs = []
    for page in (1, 2, 3):
        url = ("https://c.y.qq.com/soso/fcgi-bin/client_search_cp?p=%d&n=50&format=json&w=" % page
               + urllib.parse.quote("日木斤深夜小酒馆"))
        req = urllib.request.Request(url, headers=UA)
        d = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
        hits = json.loads(d).get("data", {}).get("song", {}).get("list", [])
        if not hits:
            break
        for s in hits:
            if (s.get("albummid") or "") != ALBUM_MID:
                continue
            nm = s.get("songname") or ""
            if not name_ok.search(nm):
                continue  # 过滤搜索噪声（如关联推荐影片等）
            album_songs.append(s)
        time.sleep(0.4)
    print("专辑内检索到 %d 条（现有 %d 条）" % (len(album_songs), len(known)))

    fresh = []
    for s in album_songs:
        mid = s.get("songmid")
        if not mid or mid in known:
            continue
        info = get_song(mid) or {"name": s.get("songname"), "mid": mid, "duration_sec": 0,
                                 "album": "日木斤深夜小酒馆|王晰哄你入睡"}
        fresh.append(info)
        time.sleep(0.3)

    print("新增期次 %d 条:" % len(fresh))
    for f in fresh:
        print("  +", f["name"], "|", f["mid"], "| %ds" % f["duration_sec"])

    if not args.apply:
        print("[只读] 未写入（--apply 才入库）")
        return

    items = ta.get("items", [])
    have = {it.get("mid") for it in items}
    for f in fresh:
        if f["mid"] not in have:
            items.append(f)
    items.sort(key=lambda x: x.get("name") or "")
    ta["items"] = items
    ta["count"] = len(items)
    json.dump(ta, open(ROOT + r"\data\tavern_audio.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[apply] tavern_audio.json 现有 %d 条" % len(items))
    if fresh:
        try:
            sys.path.insert(0, ROOT + r"\project_b")
            import notify
            lines = "\n".join("- %s（%ds）" % (f["name"], f["duration_sec"]) for f in fresh[:10])
            notify.send("🍷 小酒馆新期次 %d 条" % len(fresh),
                        "已自动入库，可试听：\n" + lines)
        except Exception as e:
            print("[notify] 失败:", e)
    # 提示：tavern_transcripts 逐字稿仍人工补充，但 songmid 可由 build_tavern_audio 反查


if __name__ == "__main__":
    main()
