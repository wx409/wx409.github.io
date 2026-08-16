# -*- coding: utf-8 -*-
"""批量验证：117 首有 mid 的歌曲，哪些真能拿到免费试听直链
输出：data/playable_songs.json {songmid: {name, playable: bool}}
"""
import json
import urllib.parse
import urllib.request

META = r"D:\wx409.github.io\data\songs_meta.json"
OUT = r"D:\wx409.github.io\data\playable_songs.json"


def get_vkey(songmid):
    param = {
        "guid": "10000" + str(abs(hash(songmid)) % 10**10),
        "songmid": [songmid],
        "songtype": [0],
        "uin": "0",
        "loginflag": 1,
        "platform": "20",
    }
    data = json.dumps({"req_0": {"module": "vkey.GetVkeyServer", "method": "CgiGetVkey", "param": param}})
    url = "https://u.y.qq.com/cgi-bin/musicu.fcg?format=json&data=" + urllib.parse.quote(data)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"})
    with urllib.request.urlopen(req, timeout=15) as r:
        j = json.loads(r.read().decode("utf-8"))
    info = j.get("req_0", {}).get("data", {}).get("midurlinfo", [])
    return (info[0] or {}).get("purl") if info else None


def main():
    meta = json.load(open(META, encoding="utf-8"))["songs"]
    candidates = [(v["name"], v["mid"]) for v in meta.values() if v.get("mid")]
    print(f"待验证: {len(candidates)} 首")

    result = {"generated_at": "", "total": 0, "playable": {}, "vip": {}}
    playable = {}
    vip = {}
    for name, mid in candidates:
        mid_clean = mid.replace("L:", "")
        try:
            purl = get_vkey(mid_clean)
            if purl:
                playable[mid_clean] = {"name": name, "playable": True}
            else:
                vip[mid_clean] = {"name": name, "playable": False}
        except Exception as e:
            vip[mid_clean] = {"name": name, "playable": False, "error": str(e)[:50]}
        print(f"  {'✅' if mid_clean in playable else '❌'} {name}")

    import datetime
    result["generated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    result["total"] = len(candidates)
    result["playable"] = playable
    result["vip"] = vip
    json.dump(result, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\n可播: {len(playable)} | VIP/不可播: {len(vip)}")
    print(f"可播歌曲: {[v['name'] for v in playable.values()]}")


if __name__ == "__main__":
    main()
