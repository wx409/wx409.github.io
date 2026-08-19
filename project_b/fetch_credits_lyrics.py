# -*- coding: utf-8 -*-
"""为 albums.json 与 songs_meta.json 补充创作班底（词/曲/编曲/制作人/原唱）+ 歌词

数据源：QQ 歌词接口 LRC。信息行（"词：xxx"）→ credits 字段；正文行 → lyrics（仅当原本没有歌词时）。
已有歌词保留不覆盖；纯音乐/无歌词标记跳过。
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

# 创作班底分类（按优先级匹配，值取第一个非空）
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
# 其他信息行（不进歌词正文，进 extra）
GENERIC_INFO = re.compile(r"^[\u4e00-\u9fa5A-Za-z·/]{1,10}[:：]")
TITLE_LINE = re.compile(r"^.{1,45} - 王晰.{0,20}$")
TIME_TAG = re.compile(r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]")


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
    """返回 (credits dict, lyrics fragments list)"""
    credits = {}
    extra = []
    frags = []
    seen = set()
    for line in lrc.splitlines():
        t = TIME_TAG.sub("", line).strip()
        if not t:
            continue
        if META_LINE.match(t):
            continue
        matched = False
        for pat, field in CREDIT_RULES:
            m = re.match(pat, t)
            if m:
                val = m.group(len(m.groups())).strip()  # 取最后一个捕获组（值）
                if field not in credits and val:
                    credits[field] = val
                matched = True
                break
        if matched:
            continue
        if GENERIC_INFO.match(t) and len(t) < 60:
            extra.append(t)
            continue
        if t in seen:
            continue
        seen.add(t)
        frags.append({"text": t, "moods": []})
    # 第一行 "歌名 - 王晰" 标题去除
    if frags and TITLE_LINE.match(frags[0]["text"].strip()):
        frags = frags[1:]
    if extra:
        credits["extra"] = extra
    return credits, frags


def main():
    albums_path = ROOT + r"\data\albums.json"
    meta_path = ROOT + r"\data\songs_meta.json"

    albums = json.load(open(albums_path, encoding="utf-8"))
    meta = json.load(open(meta_path, encoding="utf-8"))

    # 汇总需要抓的 mid（albums 72 + songs_meta 117，去重）
    jobs = {}  # mid -> 描述
    for a in albums["albums"]:
        for s in a.get("songs", []):
            if s.get("mid") and s["mid"] not in jobs:
                jobs[s["mid"]] = "专辑 %s《%s》" % (a["name"], s.get("title"))
    for k, v in meta["songs"].items():
        m = (v.get("mid") or "")
        if m.startswith("L:") and m[2:] not in jobs:
            jobs[m[2:]] = "歌曲库 %s" % v.get("name")
    print("待抓 mid 数: %d" % len(jobs))

    result = {}
    for i, (mid, desc) in enumerate(jobs.items(), 1):
        lrc = fetch_lrc(mid)
        if lrc:
            credits, frags = parse_lrc(lrc)
            result[mid] = {"credits": credits, "lyrics": frags}
            print("[%d/%d] %s | credits=%s lyrics=%d行" % (
                i, len(jobs), desc, list(credits.keys()), len(frags)))
        else:
            result[mid] = None
            print("[%d/%d] %s | 无歌词" % (i, len(jobs), desc))
        time.sleep(0.4)

    # 写回 albums.json
    for a in albums["albums"]:
        for s in a.get("songs", []):
            r = result.get(s.get("mid"))
            if not r:
                continue
            if r["credits"]:
                s["credits"] = r["credits"]
            # 合规：albums.json 也不再写完整歌词，只存定位句+标签
            if r["lyrics"] and not s.get("lyric_snippet"):
                frags0 = r["lyrics"][0].get("text", "")[:60] if r["lyrics"] else ""
                s["lyric_snippet"] = frags0
    json.dump(albums, open(albums_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # 写回 songs_meta.json（credits 一律补；合规：不再写完整歌词，只提取标签/定位句）
    n_credit = 0
    n_tags = 0
    for k, v in meta["songs"].items():
        m = (v.get("mid") or "")
        if not m.startswith("L:"):
            continue
        r = result.get(m[2:])
        if not r:
            continue
        if r["credits"]:
            v["credits"] = r["credits"]
            n_credit += 1
        if r["lyrics"] and not v.get("lyric_tags"):
            # 合规：只提取关键词标签 + 定位句（首句≤60字），不存完整歌词
            frags = r["lyrics"]
            tags = []
            for f in frags[:6]:
                for w in re.findall(r"[A-Za-z\u4e00-\u9fff]{2,}", f.get("text", "")):
                    w = w.lower()
                    if w not in tags:
                        tags.append(w)
            v["lyric_tags"] = tags[:6]
            if frags:
                v["lyric_snippet"] = frags[0].get("text", "")[:60]
            n_tags += 1
    json.dump(meta, open(meta_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("\n[OK] songs_meta: 补 credits %d 首, 补 lyric_tags %d 首（已合规，不存完整歌词）" % (n_credit, n_tags))
    print("albums.json: 已写回 credits/lyrics")


if __name__ == "__main__":
    main()
