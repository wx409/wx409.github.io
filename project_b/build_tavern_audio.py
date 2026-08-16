# -*- coding: utf-8 -*-
"""生成 data/tavern_audio.json —— 日木斤深夜小酒馆音频清单（105 条，可试听）

数据源：tavern/tavern_transcripts.json（每期 songmid + 主题）
QQ 反查曲名（"第X期01 【睡前故事与酒】主题" 等），专辑《日木斤深夜小酒馆|王晰哄你入睡》
"""
import json
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"}
ROOT = r"D:\wx409.github.io"


def song_by_mid(mid):
    url = "https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg?songmid=" + mid + "&format=json"
    try:
        req = urllib.request.Request(url, headers=UA)
        d = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
        j = json.loads(d)
        data = j.get("data") or []
        if data:
            s = data[0]
            return {
                "name": s.get("name"),
                "album": (s.get("album") or {}).get("name", ""),
                "duration_sec": (s.get("interval") or 0),
            }
    except Exception:
        pass
    return None


def main():
    tt = json.load(open(ROOT + r"\tavern\tavern_transcripts.json", encoding="utf-8"))
    items = []
    for key, e in tt["episodes"].items():
        mid = e.get("songmid")
        if not mid:
            continue
        info = song_by_mid(mid) or {}
        items.append({
            "name": info.get("name") or (e.get("theme") or key),
            "mid": mid,
            "album": info.get("album", ""),
            "duration_sec": info.get("duration_sec", e.get("duration_sec")),
            "episode": key,
            "category": e.get("category"),
            "theme": e.get("theme"),
        })
        time.sleep(0.3)

    items.sort(key=lambda x: x.get("name") or "")
    out = {
        "generated_at": "",
        "album": "日木斤深夜小酒馆|王晰哄你入睡",
        "count": len(items),
        "items": items,
    }
    import datetime
    out["generated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    json.dump(out, open(ROOT + r"\data\tavern_audio.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[OK] %d 条 -> data/tavern_audio.json" % len(items))
    for it in items[:5]:
        print("  ", it["name"], "|", it["mid"])


if __name__ == "__main__":
    main()
