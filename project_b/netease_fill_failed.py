#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""QQ 无直链的曲目 → 网易云补：搜索（限王晰）→ 外链 mp3 下载到 网易云补_单曲/。

用法：python -X utf8 project_b/netease_fill_failed.py [--limit N] [--dry]
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(r"E:\wx\论文素材_王晰作传\音域分析")
OUT = ROOT / "网易云补_单曲"
LIST = ROOT / "专辑下载清单.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
H = {"User-Agent": UA, "Referer": "https://music.163.com/"}


def search(name: str):
    q = urllib.parse.quote(name)
    url = f"https://music.163.com/api/search/get?s={q}&type=1&limit=10"
    try:
        req = urllib.request.Request(url, headers=H)
        d = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore"))
        return (d.get("result") or {}).get("songs") or []
    except Exception:
        return []


def pick(name, songs):
    for s in songs:
        artists = "/".join(a.get("name", "") for a in (s.get("artists") or []))
        if "王晰" in artists or "王晰" in (s.get("name") or ""):
            return s
    return songs[0] if songs else None


def download(sid: int, dest: Path):
    url = f"https://music.163.com/song/media/outer/url?id={sid}.mp3"
    try:
        req = urllib.request.Request(url, headers=H)
        with urllib.request.urlopen(req, timeout=90) as r:
            data = r.read()
        if len(data) < 500_000:
            return 0
        dest.write_bytes(data)
        return len(data)
    except Exception:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()

    items = json.loads(LIST.read_text(encoding="utf-8"))
    items = items if isinstance(items, list) else (items.get("items") or [])
    fails = [i for i in items if isinstance(i, dict) and str(i.get("status", "")).lower().startswith("fail")]
    titles = [i.get("title") or i.get("name") for i in fails]
    titles = [t for t in titles if t]
    if a.limit:
        titles = titles[: a.limit]
    print(f"待补 {len(titles)} 首")

    OUT.mkdir(parents=True, exist_ok=True)
    ok, miss = [], []
    for i, t in enumerate(titles, 1):
        dest = OUT / f"{t}.mp3"
        if dest.exists() and dest.stat().st_size > 500_000:
            ok.append((t, "已存在")); print(f"[{i}/{len(titles)}] 跳过 {t}"); continue
        s = pick(t, search(t))
        if not s:
            miss.append(t); print(f"[{i}/{len(titles)}] 未搜到 {t}"); continue
        artists = "/".join(x.get("name", "") for x in (s.get("artists") or []))
        if "王晰" not in artists:
            miss.append(t); print(f"[{i}/{len(titles)}] 非王晰版 {t} → {artists}"); continue
        if a.dry:
            ok.append((t, "dry")); print(f"[{i}/{len(titles)}] [dry] {t} → {s.get('name')} / {artists}"); continue
        n = download(s["id"], dest)
        if n:
            ok.append((t, f"{n/1e6:.1f}MB")); print(f"[{i}/{len(titles)}] OK {t} ({n/1e6:.1f}MB)")
        else:
            miss.append(t); print(f"[{i}/{len(titles)}] 下载失败 {t}")
        time.sleep(0.6)

    print(f"\n成功 {len(ok)}｜未拿到 {len(miss)}")
    (ROOT / "网易云补_结果.json").write_text(json.dumps(
        {"ok": ok, "miss": miss}, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
