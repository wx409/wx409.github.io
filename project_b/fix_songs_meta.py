# -*- coding: utf-8 -*-
"""修正 songs_meta.json：
1. 补 21 首确认候选的歌词+班底（QQ 歌词接口）
2. 用 albums.json 权威专辑归属修正 album 字段
3. 清理歌词中的 AI 字幕污染行（"本字幕由TME AI技术生成" 等）
4. 小酒馆音频条目（tavern_audio 中的 mid）清空 lyrics（AI 字幕非歌词）
"""
import base64
import json
import re
import time
import urllib.request

ROOT = r"D:\wx409.github.io"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Referer": "https://y.qq.com/"}
LYRIC_URL = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?songmid={mid}&format=json"

# 21 首人工确认候选
CONFIRMED = {
    "Dear Friend": "002AZbZf0D5f9K",
    "Love Me Tender": "001d8wuK3NkMoB",
    "她来听我的演唱会": "002Ry7dd0QfJ4Z",
    "抗风桐": "001SeF2a2clOID",
    "月牙湾": "00439OFo0NgDE5",
    "爱你": "000i3sr11eCkqU",
    "红豆": "004755mF4SqxzM",
    "被遗忘的时光": "0031YMXJ26qJkD",
    "你不要担心": "0023qsmR3NtVHj",
    "如果云知道": "003uTAEk3rSZu4",
    "崇拜": "001asydE32IsRo",
    "心动": "000C8IUa2fPnjJ",
    "往日时光": "001ztWi21eAS3S",
    "女人花": "003Lx5eU1tPBsO",
    "永不失联的爱": "000wsZHy0hC108",
    "海阔天空": "003n3qr82BdXeT",
    "爱的箴言": "000AwoQJ1HHo9t",
    "矜持": "000Ii99Z1om0ex",
    "送别": "000Oo4Z20umzjL",
    "月亮代表我的心": "001Dq2mi2GvOef",
    "给电影人的情书": "003UW5rX3cCt9P",
}

CREDIT_RULES = [
    (r"^(作词|词)\s*[:：]\s*(.+)$", "lyricist"),
    (r"^中文词\s*[:：]\s*(.+)$", "lyricist"),
    (r"^Lyrics by\s*[:：]\s*(.+)$", "lyricist"),
    (r"^(作曲|曲)\s*[:：]\s*(.+)$", "composer"),
    (r"^Composed by\s*[:：]\s*(.+)$", "composer"),
    (r"^Music by\s*[:：]\s*(.+)$", "composer"),
    (r"^编曲\s*[:：]\s*(.+)$", "arranger"),
    (r"^Arranged by\s*[:：]\s*(.+)$", "arranger"),
    (r"^制作人\s*[:：]\s*(.+)$", "producer"),
    (r"^Produced by\s*[:：]\s*(.+)$", "producer"),
    (r"^原唱\s*[:：]\s*(.+)$", "original"),
    (r"^原曲\s*[:：]\s*(.+)$", "original"),
]
META_LINE = re.compile(r"^\[(ti|ar|al|by|offset|length|re|ve|co|la|total|language)\s*:", re.I)
GENERIC_INFO = re.compile(r"^[\u4e00-\u9fa5A-Za-z·/]{1,10}[:：]")
TITLE_LINE = re.compile(r"^.{1,45} - 王晰.{0,20}$")
TIME_TAG = re.compile(r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]")
# AI 字幕污染
SUB_LINE = re.compile(r"^(本字幕|字幕|由TME|AI技术生成|TME AI|以上歌词|本歌词)")
TAVERN_MID = set()


def fetch_lrc(mid):
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(LYRIC_URL.format(mid=mid), headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read().decode("utf-8", "ignore")
            j = json.loads(raw)
            if j.get("retcode") not in (0, None) or not j.get("lyric"):
                return None
            return base64.b64decode(j["lyric"]).decode("utf-8", "ignore")
        except Exception:
            time.sleep(1.2)
    return None


def parse_lrc(lrc):
    credits, extra, frags, seen = {}, [], [], set()
    for line in lrc.splitlines():
        t = TIME_TAG.sub("", line).strip()
        if not t or META_LINE.match(t):
            continue
        matched = False
        for pat, field in CREDIT_RULES:
            m = re.match(pat, t)
            if m:
                val = m.group(len(m.groups())).strip()
                if field not in credits and val:
                    credits[field] = val
                matched = True
                break
        if matched:
            continue
        if GENERIC_INFO.match(t) and len(t) < 60:
            extra.append(t)
            continue
        if SUB_LINE.match(t):
            continue  # AI 字幕污染行
        if t in seen:
            continue
        seen.add(t)
        frags.append({"text": t, "moods": []})
    if frags and TITLE_LINE.match(frags[0]["text"].strip()):
        frags = frags[1:]
    if extra:
        credits["extra"] = extra
    return credits, frags


def norm_name(s):
    return re.sub(r"[\s《》「」『』··]", "", (s or "")).lower()


def main():
    meta = json.load(open(ROOT + r"\data\songs_meta.json", encoding="utf-8"))
    songs = meta["songs"]

    # 0. 读取小酒馆 mid 集合
    try:
        ta = json.load(open(ROOT + r"\data\tavern_audio.json", encoding="utf-8"))
        TAVERN_MID.update(it.get("mid") for it in ta.get("items", []) if it.get("mid"))
    except Exception:
        pass

    # 1. 补 21 首歌词+班底
    by_name = {norm_name(v.get("name")): (k, v) for k, v in songs.items()}
    n_fill = 0
    for name, mid in CONFIRMED.items():
        key = by_name.get(norm_name(name))
        if not key:
            print("未找到歌曲库条目:", name)
            continue
        k, v = key
        lrc = fetch_lrc(mid)
        if not lrc:
            print("无歌词:", name)
            continue
        credits, frags = parse_lrc(lrc)
        v["mid"] = "L:" + mid
        if credits:
            v["credits"] = credits
        if frags:
            v["lyrics"] = frags
        n_fill += 1
        print("补全 %s (%d行, credits=%s)" % (name, len(frags), list(credits.keys())))
        time.sleep(0.4)
    print("21 首补全完成: %d" % n_fill)

    # 2. albums.json 权威修正 album 字段
    albums = json.load(open(ROOT + r"\data\albums.json", encoding="utf-8"))
    title2album = {}
    for a in albums["albums"]:
        for s in a.get("songs", []):
            title2album[norm_name(s.get("title"))] = a["name"]
    n_album_fix = 0
    for k, v in songs.items():
        correct = title2album.get(norm_name(v.get("name")))
        if correct and v.get("album") != correct:
            print("修正专辑: %s: %s -> %s" % (v.get("name"), v.get("album"), correct))
            v["album"] = correct
            n_album_fix += 1
    print("专辑修正: %d 首" % n_album_fix)

    # 3. 清理字幕污染行（所有歌词）
    n_sub = 0
    for k, v in songs.items():
        if not v.get("lyrics"):
            continue
        before = len(v["lyrics"])
        v["lyrics"] = [f for f in v["lyrics"] if not SUB_LINE.match((f.get("text") or "").strip())]
        n_sub += before - len(v["lyrics"])
    print("字幕污染行移除: %d" % n_sub)

    # 4. 小酒馆音频条目清空 lyrics（AI 字幕非歌词）
    n_tavern_clear = 0
    for k, v in songs.items():
        m = (v.get("mid") or "")
        if m.startswith("L:") and m[2:] in TAVERN_MID and v.get("lyrics"):
            v["lyrics"] = []
            n_tavern_clear += 1
    print("小酒馆音频歌词清空: %d 首" % n_tavern_clear)

    json.dump(meta, open(ROOT + r"\data\songs_meta.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    n_lyr = sum(1 for v in songs.values() if v.get("lyrics"))
    print("[OK] songs_meta 更新完成 | 有歌词: %d" % n_lyr)


if __name__ == "__main__":
    main()
