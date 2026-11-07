#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""删除「另一个王晰」（QQ音乐 singer mid 000MQGf60P0Kmn）名下的歌。

依据：用 musicu 搜索接口按 singer mid 精确识别，得到 4 个标题（7 条重复）：
  最美的情歌送给最美的女孩 / 我爱的姑娘，她在远方 / 小巷故里 / 等候

做法
  1) 写进 data/excluded_songs.json（mid + 名称双保险），让大屏生成器下次构建时自动剔除；
  2) 就地清理「非生成物」的数据文件（先备份到 data/_deleted_backup/同名王晰_20261108/）；
  3) 生成物（dashboard_data/view/lite、tavern/songs_compact、各页面）交给重建。
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
BACKUP = DATA / "_deleted_backup" / "同名王晰_20261108"
OTHER_MID = "000MQGf60P0Kmn"
TITLES = ["最美的情歌送给最美的女孩", "我爱的姑娘，她在远方", "小巷故里", "等候"]

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def get_mids() -> dict[str, list[str]]:
    """用搜索接口取这些标题在另一个王晰名下的 mid。"""
    import urllib.request
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    CK = Path(r"E:\wx\index_records\qqmusic.txt").read_text(encoding="utf-8", errors="ignore").strip()
    H = {"User-Agent": UA, "Referer": "https://y.qq.com/", "Cookie": CK, "Content-Type": "application/json"}
    out: dict[str, list[str]] = {}
    for page in range(1, 13):
        p = {"comm": {"ct": 19, "cv": 1859, "uin": "0"},
             "req": {"module": "music.search.SearchCgiService",
                     "method": "DoSearchForQQMusicDesktop",
                     "param": {"num_per_page": 60, "page_num": page,
                               "query": "王晰", "search_type": 0}}}
        req = urllib.request.Request("https://u.y.qq.com/cgi-bin/musicu.fcg",
                                     data=json.dumps(p).encode(), headers=H)
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore"))
        except Exception:
            break
        lst = ((((d.get("req") or {}).get("data") or {}).get("body") or {}).get("song") or {}).get("list") or []
        if not lst:
            break
        for s in lst:
            if OTHER_MID in [x.get("mid") for x in (s.get("singer") or [])]:
                nm = (s.get("name") or "").strip()
                if nm in TITLES and s.get("mid"):
                    out.setdefault(nm, []).append(s["mid"])
    return out


def match_name(v) -> bool:
    return any(t in str(v) for t in TITLES)


def prune(obj, path=""):
    removed = []
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            nv, rm = prune(v, f"{path}/{k}")
            out[k] = nv
            removed += rm
        return out, removed
    if isinstance(obj, list):
        out = []
        for i, v in enumerate(obj):
            if isinstance(v, dict):
                names = [v.get(k) for k in ("name", "title", "song", "歌曲名称", "歌名", "track")]
                if any(match_name(n) for n in names if n):
                    removed.append(f"{path}[{i}] {names[:1]}")
                    continue
            out.append(v)
        return out, removed
    return obj, removed


STATIC = ["song_aliases.json", "song_playable.json", "qq_singer_songs.json",
          "singles_inventory.json", "audio_assets.json", "netease_catalog.json",
          "netease_only.json", "research/singles_analysis.json", "research/singles_bpm.json"]


def main() -> int:
    mids = get_mids()
    print("另一个王晰名下命中：", {k: v for k, v in mids.items()})

    # 1) 排除清单
    ex_p = DATA / "excluded_songs.json"
    ex = json.loads(ex_p.read_text(encoding="utf-8"))
    have_uids = {i.get("uid") for i in ex.get("items", []) if i.get("uid")}
    names = set(ex.get("names") or [])
    added = 0
    for t in TITLES:
        for mid in mids.get(t, []):
            uid = "L:" + mid
            if uid in have_uids:
                continue
            ex.setdefault("items", []).append({
                "mid": mid, "name": t,
                "reason": "同名歌手（QQ音乐 singer mid %s，另一位王晰）" % OTHER_MID,
            })
            have_uids.add(uid)
            added += 1
        if t not in names:
            names.add(t)
            ex.setdefault("names", []).append(t)
    ex_p.write_text(json.dumps(ex, ensure_ascii=False, indent=1), encoding="utf-8")
    print("排除清单新增 mid %d 条、名称 %d 个" % (added, len(TITLES)))

    # 2) 静态数据文件就地清理（先备份）
    BACKUP.mkdir(parents=True, exist_ok=True)
    log = {"at": datetime.now().isoformat(timespec="seconds"), "singer_mid": OTHER_MID,
           "titles": TITLES, "files": []}
    for rel in STATIC:
        p = DATA / rel
        if not p.exists():
            continue
        raw = p.read_text(encoding="utf-8")
        if not any(t in raw for t in TITLES):
            continue
        bak = BACKUP / rel.replace("/", "__")
        bak.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, bak)
        obj = json.loads(raw)
        new, removed = prune(obj)
        p.write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding="utf-8")
        log["files"].append({"file": rel, "removed": len(removed), "sample": removed[:3]})
        print("  %-38s 删除 %d 条" % (rel, len(removed)))

    (BACKUP / "_删除日志.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    print("备份与日志：", BACKUP)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
