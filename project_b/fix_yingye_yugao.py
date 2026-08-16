# -*- coding: utf-8 -*-
"""补足「营业预告」期：tavern_transcripts / site_search_index / songs_meta / tavern_audio

QQ mid: 002bLErj1Mm8OW（王晰 - 营业预告：欢迎光临日木斤小酒馆！评论区给王晰留言~ (节目)）
"""
import json
import re
import urllib.request

ROOT = r"D:\wx409.github.io"
MID = "002bLErj1Mm8OW"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"}


def norm_name(s):
    return re.sub(r"[\s《》「」『』··]", "", (s or "")).lower()


def main():
    # 0. 反查 duration
    dur = 0
    try:
        url = "https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg?songmid=" + MID + "&format=json"
        req = urllib.request.Request(url, headers=UA)
        j = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore"))
        d0 = (j.get("data") or [None])[0]
        if d0:
            dur = d0.get("interval") or 0
            print("QQ interval:", dur, "秒 |", d0.get("name"))
    except Exception as e:
        print("反查 duration 失败:", e)

    # 1. tavern_transcripts.json
    tp = ROOT + r"\tavern\tavern_transcripts.json"
    tt = json.load(open(tp, encoding="utf-8"))
    e = tt["episodes"].get("营业预告")
    if e:
        e["songmid"] = MID
        e["duration_sec"] = dur
        json.dump(tt, open(tp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("[1] tavern_transcripts: 营业预告 songmid 已填")
    else:
        print("[1] 未找到营业预告期!")

    # 2. site_search_index.json：episode 与 (节目) song 条目补 mid
    sp = ROOT + r"\data\site_search_index.json"
    idx = json.load(open(sp, encoding="utf-8"))
    n = 0
    for it in idx:
        t = it.get("title") or ""
        if it.get("type") == "episode" and "营业预告" in t:
            it["mid"] = MID
            n += 1
        elif it.get("type") == "song" and t.endswith("(节目)"):
            it["mid"] = MID
            n += 1
    json.dump(idx, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("[2] site_search_index: 补 mid %d 条" % n)

    # 3. songs_meta.json：补营业预告条目（若无）
    mp = ROOT + r"\data\songs_meta.json"
    meta = json.load(open(mp, encoding="utf-8"))
    songs = meta["songs"]
    target = "营业预告：欢迎光临日木斤小酒馆！评论区给王晰留言~"
    if not any(v.get("name") == target for v in songs.values()):
        key = norm_name(target)
        songs[key] = {
            "name": target, "attr": "小酒馆音频", "release": "-", "latest": None,
            "mean30": None, "peak": None, "lyrics": [], "album": "日木斤深夜小酒馆|王晰哄你入睡",
            "show_count": 0, "cities": [], "live": [], "mid": "L:" + MID,
        }
        meta["song_count"] = len(songs)
        print("[3] songs_meta: 已补营业预告条目")
    else:
        print("[3] songs_meta: 已存在")
    json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 4. 重跑 tavern_audio 生成
    import subprocess, sys
    r = subprocess.run([sys.executable, ROOT + r"\project_b\build_tavern_audio.py"])
    print("[4] build_tavern_audio:", "OK" if r.returncode == 0 else "FAIL")

    # 5. 重跑 songs 页
    r2 = subprocess.run([sys.executable, ROOT + r"\project_b\build_songs_page.py"])
    print("[5] build_songs_page:", "OK" if r2.returncode == 0 else "FAIL")


if __name__ == "__main__":
    main()
