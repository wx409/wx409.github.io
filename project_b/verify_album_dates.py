# -*- coding: utf-8 -*-
"""QQ 音乐专辑发行日期核验 —— 自动把 albums.json 的年月精度升级为精确日期。

背景：data/albums.json 的 release 只有「YYYY-MM」（如 2024-12），导致「巡演 × 专辑」
的时序判定在同月发行时无法定论（曾标「口径待核」）。本脚本用 QQ 音乐公开搜索接口
（c.y.qq.com/soso/fcgi-bin/client_search_cp，专辑搜索 t=8）取 `publicTime`（精确到日），
以 albumMID == albums.json 的 qq_mid 为主键匹配，回写：

  data/albums.json 每个专辑新增：
    release_date   精确发行日期（YYYY-MM-DD，QQ 音乐核验）
    release_source "QQ音乐 publicTime（albumMID 匹配）"
    release_verified_at 核验时间
  release 字段保持 YYYY-MM 不变（页面沿用，避免格式破坏）

并输出人读报告：data/album_release_verify.md

用法：
  python -X utf8 project_b/verify_album_dates.py            # 核验并回写
  python -X utf8 project_b/verify_album_dates.py --check    # 只报告差异，不写文件
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
ALBUMS = ROOT / "data" / "albums.json"
REPORT = ROOT / "data" / "album_release_verify.md"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
API = ("https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
       "?w={q}&format=json&t=8&p=1&n=10")


def search_albums(keyword: str) -> list[dict]:
    url = API.format(q=urllib.parse.quote(keyword))
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
    data = json.loads(raw.decode("utf-8", errors="replace"))
    return ((data.get("data") or {}).get("album") or {}).get("list") or []


def keywords_for(name: str) -> list[str]:
    """搜索关键词候选：全名 → 罗马数字转阿拉伯数字 → 首个词（应对「Ⅱ/2」「II」差异）。"""
    kws = [f"王晰 {name}"]
    norm = name.replace("Ⅱ", "2").replace("II", "2").replace("Ⅰ", "1")
    if norm != name:
        kws.append(f"王晰 {norm}")
    head = re.split(r"[\s（(]", name)[0]
    if head and head not in (name,):
        kws.append(f"王晰 {head}")
    seen, out = set(), []
    for k in kws:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def match_album(album: dict, items: list[dict]) -> dict | None:
    mid = str(album.get("qq_mid") or "")
    name = str(album.get("name") or "")
    if mid:
        for it in items:
            if str(it.get("albumMID")) == mid:
                return it
    for it in items:                      # 回退：同名 + 演唱者含王晰 + 歌曲数一致
        if str(it.get("albumName")) == name and "王晰" in str(it.get("singerName") or ""):
            if not album.get("songs") or len(album["songs"]) == it.get("song_count"):
                return it
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    doc = json.loads(ALBUMS.read_text(encoding="utf-8"))
    albums = doc.get("albums") or []
    rows, changed, failed = [], 0, []
    for a in albums:
        name = str(a.get("name") or "")
        hit = None
        try:
            for kw in keywords_for(name):
                items = search_albums(kw)
                hit = match_album(a, items)
                if hit:
                    break
                time.sleep(0.6)
        except Exception as e:
            failed.append(f"{name}（{type(e).__name__}）")
            hit = None
        old = a.get("release")
        if not hit:
            rows.append((name, old, "—", "未匹配", ""))
            failed.append(name)
            continue
        pub = str(hit.get("publicTime") or "").strip()
        ok = bool(re.match(r"^\d{4}-\d{2}-\d{2}$", pub))
        rows.append((name, old, pub or "—", "命中" if ok else "无日期", str(hit.get("albumMID") or "")))
        if ok and a.get("release_date") != pub and not args.check:
            a["release_date"] = pub
            a["release_source"] = "QQ音乐 publicTime（albumMID 匹配）"
            a["release_verified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            changed += 1
        time.sleep(1.0)

    md = ["# 专辑发行日期 · QQ 音乐核验", "",
          f"> 核验时间：{datetime.now():%Y-%m-%d %H:%M} ｜ 接口：QQ音乐专辑搜索 publicTime "
          f"｜ 主键：albumMID == data/albums.json 的 qq_mid", "",
          "| 专辑 | 原 release | QQ 音乐精确日期 | 状态 | albumMID |", "|---|---|---|---|---|"]
    md += [f"| {n} | {o} | {p} | {s} | {m} |" for n, o, p, s, m in rows]
    md += ["", "说明：`release` 保持年月格式供页面沿用；新增 `release_date` 为精确日期，"
              "供「巡演 × 专辑」时序判定与学术引用使用。", ""]
    if not args.check:
        doc["generated_at"] = doc.get("generated_at") or datetime.now().strftime("%Y-%m-%d %H:%M")
        doc["release_verified_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        ALBUMS.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        REPORT.write_text("\n".join(md), encoding="utf-8")

    for n, o, p, s, m in rows:
        print(f"  {n:<14} {o:<9} -> {p:<12} {s}")
    print(f"[OK] 命中 {len(rows) - len(set(failed))}/{len(rows)}｜更新 {changed} 条"
          + (f"｜未匹配：{', '.join(sorted(set(failed)))}" if failed else "")
          + ("（--check 未写盘）" if args.check else ""))
    return 0 if not failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
