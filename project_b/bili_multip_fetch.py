#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_multip_fetch.py —— 抓「分曲目（多 P）」投稿：一个 BV 里每个 P 是一首歌

之前 bili_best_fetch 只取 pages[0]，所以 29P / 35P 这种整场分曲投稿只收到 1 首。
本脚本按 P 循环：每 P 取 playurl 最高音轨 → 转 FLAC → 落到该场次目录，并逐条登记 Excel。

命名：[B站-<UP>]<P名>.flac（若 P 名重复/为空，用 P序号 补）
用法：
  python -X utf8 project_b/bili_multip_fetch.py --bv BV1zU6hBHEY8 --tour 五巡 --date 20260131 --city 杭州
  python -X utf8 project_b/bili_multip_fetch.py --bv BV18U6gYHEu3 --tour 五巡 --date 20241229 --city 南昌
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
sys.path.insert(0, str(ROOT / "project_b"))
import importlib.util


def load(n, p):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


AB = load("ab", str(ROOT / "project_b" / "bili_best_fetch.py"))
AB.VIDEO_POLICY = "none"
XLSX = AB.XLSX
OUT = AB.AUD_ROOT
STAGE = AB.STAGE
FFMPEG = AB.FFMPEG
FFPROBE = AB.FFPROBE


def safe(s, n=80):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", str(s or ""))[:n]


def get_audio(cid, bv, h):
    j = AB.get(f"https://api.bilibili.com/x/player/playurl?bvid={bv}&cid={cid}&qn=127&fnval=4048&fourk=1", h)
    dash = ((j or {}).get("data") or {}).get("dash") or {}
    pool = []
    if dash.get("flac") and dash["flac"].get("audio"):
        pool.append(("flac", dash["flac"]["audio"]))
    if dash.get("dolby"):
        pool += [("dolby", a) for a in dash["dolby"].get("audio") or []]
    pool += [("aac", a) for a in dash.get("audio") or []]
    if not pool:
        return None
    kind, best = max(pool, key=lambda t: int(t[1].get("bandwidth") or 0))
    return {"url": best.get("baseUrl") or best.get("base_url"),
            "kbps": round(int(best.get("bandwidth") or 0) / 1000), "kind": kind}


def download(url, dst, h):
    req = urllib.request.Request(url, headers={"User-Agent": h["User-Agent"], "Referer": h["Referer"]})
    with urllib.request.urlopen(req, timeout=180) as r, dst.open("wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    return dst.exists() and dst.stat().st_size > 10000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bv", required=True)
    ap.add_argument("--tour", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--city", required=True)
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 个 P（0=全部）")
    args = ap.parse_args()

    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    idx = {c.value: i for i, c in enumerate(ws[1])}
    have = {str(r[idx["目标路径"]]) for r in ws.iter_rows(min_row=2, values_only=True)
            if len(r) > idx["目标路径"] and r[idx["目标路径"]]}

    h = AB.headers()
    vj = AB.get(f"https://api.bilibili.com/x/web-interface/view?bvid={args.bv}", h)
    d = (vj or {}).get("data") or {}
    pages = d.get("pages") or []
    owner = (d.get("owner") or {}).get("name") or "B站"
    title = d.get("title") or args.bv
    print(f"{args.bv} | {title} | {len(pages)} P | UP={owner}", flush=True)

    dst_dir = OUT / args.tour / f"{args.date}_{args.city}"
    dst_dir.mkdir(parents=True, exist_ok=True)
    STAGE.mkdir(parents=True, exist_ok=True)

    todo = pages[: args.limit] if args.limit else pages
    ok = 0
    for p in todo:
        part = (p.get("part") or f"P{p.get('page')}").strip()
        name = f"[B站-{safe(owner, 20)}]{safe(part, 60)}.flac"
        dst = dst_dir / name
        if dst.exists() and dst.stat().st_size > 50000:
            print(f"  P{p.get('page')} 已存在，跳过 {name[:40]}", flush=True)
            continue
        q = get_audio(p.get("cid"), args.bv, h)
        if not q:
            print(f"  P{p.get('page')} 无音轨，跳过", flush=True); continue
        tmp = STAGE / f"{args.bv}_P{p.get('page')}.m4a"
        try:
            if not download(q["url"], tmp, h):
                print(f"  P{p.get('page')} 下载失败", flush=True); continue
        except Exception as e:
            print(f"  P{p.get('page')} 下载异常 {str(e)[:40]}", flush=True); continue
        r = subprocess.run([str(FFMPEG), "-y", "-loglevel", "error", "-i", str(tmp), "-vn", "-c:a", "flac", str(dst)],
                           capture_output=True)
        if r.returncode != 0:
            print(f"  P{p.get('page')} 转 FLAC 失败", flush=True); continue
        pr = subprocess.run([str(FFPROBE), "-v", "quiet", "-show_streams", "-select_streams", "a:0",
                             "-of", "json", str(dst)], capture_output=True, text=True)
        try:
            a = (json.loads(pr.stdout or "{}").get("streams") or [{}])[0]
        except Exception:
            a = {}
        row = {"巡次": args.tour, "日期": args.date, "城市": args.city,
               "来源": f"B站-{owner}", "级别": f"A(B站分P {q['kind']} {q['kbps']}kbps)",
               "文件名": dst.name, "目标路径": str(dst),
               "原始路径": f"https://www.bilibili.com/video/{args.bv}?p={p.get('page')}",
               "大小MB": round(dst.stat().st_size / 1048576, 1), "格式": "flac",
               "采样率": a.get("sample_rate"), "位深": a.get("bits_per_raw_sample"),
               "码率kbps": round(int(a.get("bit_rate") or 0) / 1000) or None,
               "时长秒": p.get("duration"), "BV": args.bv}
        if str(dst) not in have:
            ws.append([row.get(c.value) for c in ws[1]])
            have.add(str(dst))
        ok += 1
        print(f"  P{p.get('page')} {q['kbps']}kbps -> {name[:52]}", flush=True)
        time.sleep(1)
    wb.save(XLSX)
    print(f"\n完成 {ok} 个分P；目录 {dst_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
