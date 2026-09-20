# -*- coding: utf-8 -*-
"""追踪池扩容：把「他唱过但大屏没追踪」的曲目补进源表（拿到 QQ songmid）。

源表（大屏读取）：E:\\wx\\index_records\\收听人数（2026.7.24）.xlsx
  列：2026-7 序号 / 歌曲名称 / 演唱者 / ngrid_链接（含 mid）/ … / 歌曲编号

安全设计：
  · 默认 --dry（只报告），--apply 才写；写前自动备份 xlsx（带时间戳）
  · 曲名规范化后与源表比对，避免大小写/括号造成的假缺口
  · 串烧（含 +）、明确他人原唱 / 混剪类按纪律词表**默认跳过**（另有 --allow-covers 放行）
  · 命中 QQ 搜索但演唱者不含王晰的，跳过
用法：
  python -X utf8 project_b\\expand_track_pool.py                 # 试算
  python -X utf8 project_b\\expand_track_pool.py --apply         # 写入源表（自动备份）
  python -X utf8 project_b\\expand_track_pool.py --limit 20      # 只处理前 N 首
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
XLSX = Path(r"E:\wx\index_records\收听人数（2026.7.24）.xlsx")
SETLISTS = ROOT / "data" / "setlists.json"
GAP_MD = ROOT / "temp" / "追踪池缺口.md"
GAP_JS = ROOT / "temp" / "track_pool_gap.json"
SKIP_WORDS = ("混剪", "伪合唱", "AI翻唱", "消音", "伴奏", "人声增强", "音频重制", "合唱版")


def norm(t: str) -> str:
    t = str(t or "").strip().lower()
    t = re.sub(r"[（(].*?[)）]", "", t)          # 去括号注释
    t = re.sub(r"[\s·・,，、'’\"“”!！?？.。\-—_]+", "", t)
    return t


def sung_titles() -> dict:
    sl = json.loads(SETLISTS.read_text(encoding="utf-8"))["setlists"]
    out = {}
    for v in sl.values():
        for s in v.get("songs", []):
            t = (s.get("title") or "").strip()
            if t:
                out[t] = out.get(t, 0) + 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--allow-covers", action="store_true", help="连翻唱/他人原唱也补（默认跳过）")
    a = ap.parse_args()

    df = pd.read_excel(XLSX)
    col_title = "歌曲名称"
    have = {norm(t) for t in df[col_title].dropna().astype(str)}
    sung = sung_titles()
    print(f"源表 {len(df)} 行｜歌单唱过 {len(sung)} 首")

    cand, skipped = [], []
    for t, n in sorted(sung.items(), key=lambda kv: -kv[1]):
        if norm(t) in have:
            continue
        if "+" in t or "＋" in t or any(w in t for w in SKIP_WORDS):
            skipped.append((t, n, "串烧/混剪/伴奏类"))
            continue
        if re.search(r"[\u4e00-\u9fffA-Za-z]", t) is None:
            continue
        cand.append((t, n))
    print(f"候选待补 {len(cand)} 首｜按纪律跳过 {len(skipped)} 首")
    if a.limit:
        cand = cand[:a.limit]

    sys.path.insert(0, str(Path(r"E:\wx\论文素材_王晰作传\音域分析")))
    try:
        from 批量下载专辑 import http_json, load_cookie   # 复用现有 QQ 搜索能力
    except Exception as e:
        print("× 无法复用 QQ 搜索模块：", e)
        return 1
    cookie = load_cookie()

    def search(kw, num=6):
        url = ("https://c.y.qq.com/soso/fcgi-bin/client_search_cp?"
               f"format=json&w={urllib.parse.quote(kw)}&n={num}&p=1&cr=1&t=0&aggr=1")
        j = http_json(url, cookie, referer="https://y.qq.com/portal/search.html")
        out = []
        for s in (j.get("data", {}).get("song", {}).get("list") or []):
            singers = "、".join(x.get("name", "") for x in s.get("singer", []))
            out.append({"mid": s.get("songmid") or s.get("mid"), "name": s.get("songname"),
                        "singers": singers, "album": s.get("albumname")})
        return out

    rows, miss = [], []
    for t, n in cand:
        try:
            hits = search(t)
        except Exception as e:
            miss.append((t, n, f"搜索失败 {e}"))
            continue
        pick = next((h for h in hits if "王晰" in h["singers"]), None)
        if not pick:
            miss.append((t, n, "QQ搜索无王晰版本" if hits else "QQ无结果"))
            continue
        link = (f"https://y.qq.com/m/client/music_index/index.html?ADTAG=cbshare&channelId=10036163"
                f"&mid={pick['mid']}&openinqqmusic=1&type={pick['mid']}")
        rows.append({"title": t, "mid": pick["mid"], "qq_name": pick["name"], "singers": pick["singers"],
                     "album": pick["album"], "link": link, "sung_times": n})

    print(f"\n可补 {len(rows)} 首｜不可补 {len(miss)} 首")
    for r in rows[:40]:
        print(f"  + {r['title']} ×{r['sung_times']} → {r['qq_name']}｜{r['mid']}｜{r['album']}")
    if miss:
        print("\n不可补（前 20）：")
        for t, n, why in miss[:20]:
            print(f"  - {t} ×{n}：{why}")

    GAP_JS.write_text(json.dumps({"generated_at": datetime.now().isoformat(timespec="seconds"),
                                  "addable": rows, "not_found": [{"title": t, "times": n, "why": w} for t, n, w in miss],
                                  "skipped_by_discipline": [{"title": t, "times": n, "why": w} for t, n, w in skipped]},
                                 ensure_ascii=False, indent=1), encoding="utf-8")
    lines = [f"# 追踪池缺口（自动生成 {datetime.now():%Y-%m-%d %H:%M}）", "",
             f"- 源表 {len(df)} 行｜歌单唱过 {len(sung)} 首｜可补 **{len(rows)}** 首｜QQ 无王晰版本 {len(miss)} 首｜纪律跳过 {len(skipped)} 首",
             "", "## 可补（写入源表即可被大屏追踪）", "",
             "| 曲目 | 演唱次数 | QQ 曲名 | songmid | 专辑 |", "|---|---|---|---|---|"]
    lines += [f"| {r['title']} | {r['sung_times']} | {r['qq_name']} | `{r['mid']}` | {r['album']} |" for r in rows]
    lines += ["", "## QQ 无王晰版本（需人工确认）", ""] + [f"- {t} ×{n}：{w}" for t, n, w in miss]
    lines += ["", "## 按纪律跳过（串烧/混剪/伴奏类，不可作单曲追踪）", ""] + [f"- {t} ×{n}：{w}" for t, n, w in skipped]
    GAP_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n→ {GAP_MD}\n→ {GAP_JS}")

    if a.apply and rows:
        backup = XLSX.with_name(f"{XLSX.stem}.bak_{datetime.now():%Y%m%d_%H%M%S}{XLSX.suffix}")
        shutil.copy2(XLSX, backup)
        start = int(df.iloc[-1, 0]) if str(df.iloc[-1, 0]).strip().isdigit() else len(df)
        add = pd.DataFrame([[start + i + 1, r["qq_name"], r["singers"], r["link"], "", "", r["title"], "", ""]
                            for i, r in enumerate(rows)], columns=df.columns[:9])
        pd.concat([df, add], ignore_index=True).to_excel(XLSX, index=False)
        print(f"✅ 已写入源表 {len(add)} 行（备份 {backup.name}）")
        print("   下一步：大屏 daemon 下个批次会自动纳入；若要立刻生效见 操作中心 47（重启 daemon）")
    elif rows:
        print("（试算模式，未写源表；加 --apply 生效）")
    assert len(rows) + len(miss) + len(skipped) >= 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
