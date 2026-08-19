# -*- coding: utf-8 -*-
"""补全 songs_meta.json 歌词 —— 所有有 QQ mid 但无歌词的歌曲，从 QQ 音乐歌词接口抓取。

- 只补 songs_meta.json 中有 mid（"L:xxx" = QQ songmid）且 lyrics 为空的歌
- 保留已有手动收集的歌词片段（不覆盖）
- LRC 解析为行数组，格式与现有一致：{"text": "行文本", "moods": []}
- 限速 + 失败重试；纯音乐/无歌词标记跳过
"""
import base64
import json
import re
import time
import urllib.parse
import urllib.request

ROOT = r"D:\wx409.github.io"
META = ROOT + r"\data\songs_meta.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "Referer": "https://y.qq.com/"}

LYRIC_URL = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg?songmid={mid}&format=json"


def fetch_lyric_lrc(songmid):
    """返回 LRC 文本；无歌词/失败返回 None"""
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(LYRIC_URL.format(mid=songmid), headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                raw = r.read().decode("utf-8", "ignore")
            j = json.loads(raw)
            if j.get("retcode") not in (0, None) or not j.get("lyric"):
                return None  # 无歌词（纯音乐/VIP 未授权等）
            lyric = j["lyric"]
            # 接口返回 base64 编码的 LRC
            lrc = base64.b64decode(lyric).decode("utf-8", "ignore")
            return lrc
        except Exception:
            time.sleep(1.2)
    return None


def lrc_to_fragments(lrc):
    """LRC → [{text, moods:[]}]：去掉时间戳，过滤元信息行，压缩空行，副歌重复行去重"""
    frags = []
    seen = set()
    meta_line = re.compile(r"^\[(ti|ar|al|by|offset|length|re|ve|co|la|total|language)\s*:", re.I)
    for line in lrc.splitlines():
        t = re.sub(r"\[\d{1,2}:\d{2}(?:[.:]\d{1,3})?\]", "", line).strip()
        if not t or meta_line.match(t):
            continue  # 空行 / LRC 元信息行（ti/ar/al/by 等）
        if t in seen:
            continue  # 副歌重复行去重，控制体积
        seen.add(t)
        frags.append({"text": t, "moods": []})
    return frags


def main():
    meta = json.load(open(META, encoding="utf-8"))
    songs = meta["songs"]

    todo = [k for k, v in songs.items() if (v.get("mid") or "").startswith("L:")
            and not v.get("lyric_tags")]
    print("待补歌词标签（有QQ mid且无歌词标签）: %d 首" % len(todo))

    ok, skip, fail = 0, 0, 0
    for i, key in enumerate(todo, 1):
        mid = songs[key]["mid"][2:]  # 去掉 "L:" 前缀
        lrc = fetch_lyric_lrc(mid)
        if lrc:
            frags = lrc_to_fragments(lrc)
            if frags:
                # 合规：只提取关键词标签 + 首句定位句（≤60字），不存完整歌词
                tags = []
                for f in frags[:6]:
                    for w in re.findall(r"[A-Za-z\u4e00-\u9fff]{2,}", f.get("text", "")):
                        w = w.lower()
                        if w not in tags:
                            tags.append(w)
                songs[key]["lyric_tags"] = tags[:6]
                songs[key]["lyric_snippet"] = frags[0].get("text", "")[:60]
                ok += 1
                print("[%d/%d] %s: +%d 标签" % (i, len(todo), key, len(tags)))
            else:
                skip += 1
                print("[%d/%d] %s: 解析为空" % (i, len(todo), key))
        else:
            skip += 1
            print("[%d/%d] %s: 无歌词" % (i, len(todo), key))
        time.sleep(0.5)

    meta["lyrics_count"] = sum(1 for v in songs.values() if v.get("lyric_tags"))
    json.dump(meta, open(META, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("\n[完成] 成功 %d | 无歌词 %d | 失败 %d（已合规，仅存标签/定位句，不存完整歌词）" % (ok, skip, fail))
    print("现在有歌词标签: %d 首" % meta["lyrics_count"])


if __name__ == "__main__":
    main()
