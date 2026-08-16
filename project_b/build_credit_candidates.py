# -*- coding: utf-8 -*-
"""为 songs_meta 中无 mid 的歌曲生成 QQ 候选匹配清单（人工确认用）

对每首歌搜索 "歌名 王晰"，取前 5 条，按匹配度分级：
- HIGH: 歌名完全一致 + 歌手含王晰
- MID:  歌名包含/被包含 + 歌手含王晰
- LOW:  歌名完全一致但歌手不含王晰（可能是原唱版，需人工判断）
输出：temp/歌词班底候选清单.md（不修改任何数据文件）
"""
import json
import re
import time
import urllib.parse
import urllib.request

ROOT = r"D:\wx409.github.io"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"}


def qq_search(kw, n=5):
    url = ("https://c.y.qq.com/soso/fcgi-bin/client_search_cp?p=1&n=" + str(n)
           + "&format=json&w=" + urllib.parse.quote(kw))
    try:
        req = urllib.request.Request(url, headers=UA)
        d = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", "ignore")
        j = json.loads(d)
        return j.get("data", {}).get("song", {}).get("list", [])
    except Exception:
        return []


def norm(s):
    return re.sub(r"[\s《》「」『』··]", "", (s or "")).lower()


def strip_suffix(name):
    """去掉（版本2）/（Live）等后缀用于匹配"""
    return re.sub(r"[（(](版本\d+|Live|现场|伴奏)[）)]$", "", name).strip()


def main():
    sm = json.load(open(ROOT + r"\data\songs_meta.json", encoding="utf-8"))
    songs = sm["songs"]
    todo = [v for v in songs.values() if not (v.get("mid") or "").startswith("L:")]
    print("无 mid 歌曲: %d 首" % len(todo))

    rows = []
    n_high = n_mid = n_low = n_none = 0
    for i, v in enumerate(todo, 1):
        name = v.get("name", "")
        base = strip_suffix(name)
        hits = qq_search("%s 王晰" % base) or qq_search("王晰 %s" % base)
        best = None
        nname = norm(base)
        for s in hits:
            sn = norm(s.get("songname", ""))
            singers = "、".join(x.get("name", "") for x in s.get("singer", []))
            has_wx = "王晰" in singers
            if sn == nname:
                level = "HIGH" if has_wx else "LOW"
            elif has_wx and (sn in nname or nname in sn):
                level = "MID"
            else:
                continue
            cand = {
                "song": name, "qq_name": s.get("songname"), "mid": s.get("songmid"),
                "singer": singers, "album": s.get("albumname", ""), "level": level,
            }
            if best is None or (level == "HIGH" and best["level"] != "HIGH"):
                best = cand
            if level == "HIGH":
                break
        if best:
            rows.append(best)
            if best["level"] == "HIGH":
                n_high += 1
            elif best["level"] == "MID":
                n_mid += 1
            else:
                n_low += 1
        else:
            rows.append({"song": name, "qq_name": "", "mid": "", "singer": "",
                         "album": "", "level": "NONE"})
            n_none += 1
        if i % 20 == 0:
            print("  进度 %d/%d" % (i, len(todo)))
        time.sleep(0.4)

    # 输出 Markdown 清单
    lines = ["# 歌词/班底候选匹配清单（人工确认）", ""]
    lines.append("共 %d 首无 mid 歌曲：HIGH %d / MID %d / LOW %d / 未找到 %d" % (
        len(todo), n_high, n_mid, n_low, n_none))
    lines.append("")
    lines.append("| 置信 | 歌曲库歌名 | QQ歌名 | mid | 歌手 | 专辑 |")
    lines.append("|---|---|---|---|---|---|")
    for r in rows:
        if r["level"] == "NONE":
            lines.append("| - | %s | （未找到） | | | |" % r["song"].replace("|", "\\|"))
        else:
            lines.append("| %s | %s | %s | %s | %s | %s |" % (
                r["level"], r["song"].replace("|", "\\|"), r["qq_name"].replace("|", "\\|"),
                r["mid"], r["singer"].replace("|", "\\|"), r["album"].replace("|", "\\|")))
    lines.append("")
    lines.append("说明：HIGH=歌名完全一致且歌手为王晰（可直接采用）；MID=名称近似且歌手为王晰（建议抽查）；LOW=歌名一致但歌手非王晰（可能是原唱版，需确认王晰是否翻唱过）；- = 未找到匹配。")
    out_path = ROOT + r"\temp\歌词班底候选清单.md"
    import io
    io.open(out_path, "w", encoding="utf-8").write("\n".join(lines))
    print("\n[OK] -> %s" % out_path)
    print("HIGH %d / MID %d / LOW %d / NONE %d" % (n_high, n_mid, n_low, n_none))


if __name__ == "__main__":
    main()
