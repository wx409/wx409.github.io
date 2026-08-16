# -*- coding: utf-8 -*-
"""生成 data/albums.json —— 8 张专辑完整曲目（QQ 搜索按专辑名归属，严格王晰过滤）

数据源：QQ 音乐搜索接口（albumname 字段归属专辑），仅收录 歌手含"王晰" 且 albumname 精确匹配的曲目。
每首歌带 mid（供试听）、网易云链接可后续补。
"""
import json
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Referer": "https://y.qq.com/"}

ALBUMS = [
    {"name": "不说", "release": "2024-12", "qq_mid": "002YkWTV2BcuP5", "wyy_id": 258538091},
    {"name": "X自选集", "release": "2022-12", "qq_mid": "000bAQWo0jiS2s", "wyy_id": None},
    {"name": "回望", "release": "2021-12", "qq_mid": "0033GUYO3pK9by", "wyy_id": None},
    {"name": "B面图景", "release": "2021-11", "qq_mid": "0008dZFl1rXQWB", "wyy_id": 138048648},
    {"name": "歌颂", "release": "2020-08", "qq_mid": "003q8VG43Rb9Nf", "wyy_id": 146261596},
    {"name": "重游往昔", "release": "2017-11", "qq_mid": "002OTM4N17x9Qa", "wyy_id": None},
    {"name": "Low C的诱惑Ⅱ", "alias": "Low C的诱惑2", "release": "2016-05", "qq_mid": "0039mRki2zXB8x", "wyy_id": 36030702},
    {"name": "Low C的诱惑", "release": "2014", "qq_mid": "003rX9Zh0RAxcA", "wyy_id": 3145126},
]


def qq_search(kw, n=30):
    url = ("https://c.y.qq.com/soso/fcgi-bin/client_search_cp?p=1&n=" + str(n)
           + "&format=json&w=" + urllib.parse.quote(kw))
    req = urllib.request.Request(url, headers={**UA, "Referer": "https://y.qq.com/"})
    with urllib.request.urlopen(req, timeout=15) as r:
        j = json.loads(r.read().decode("utf-8"))
    return j.get("data", {}).get("song", {}).get("list", [])


def norm_album(s):
    """归一化专辑名：Ⅱ→2、去空格、全半角"""
    return (s or "").replace("Ⅱ", "2").replace("II", "2").replace(" ", "").strip()


def main():
    out = {"generated_at": "", "albums": []}
    for alb in ALBUMS:
        name = alb["name"]
        hits = qq_search(f"王晰 {alb.get('alias', name)}")
        # 过滤：歌手含王晰 + albumname 精确匹配
        songs = []
        seen = set()
        for s in hits:
            singer = "、".join(x.get("name", "") for x in s.get("singer", []))
            album = norm_album(s.get("albumname"))
            if "王晰" not in singer or album != norm_album(name):
                continue
            mid = s.get("songmid")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            songs.append({"title": s.get("songname"), "mid": mid, "singer": singer})
        out["albums"].append({**alb, "songs": songs})
        print(f"{name}: {len(songs)} 首 -> {[s['title'] for s in songs]}")
        time.sleep(0.8)  # 礼貌间隔

    import datetime
    out["generated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    json.dump(out, open(r"D:\wx409.github.io\data\albums.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("\n[OK] -> data/albums.json")


if __name__ == "__main__":
    main()
