#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_audio_fetch.py —— 只取 B站「最高音质」音轨（不下载视频），转 FLAC 入最优音频 + 记 Excel

为什么不用 download_bilibili.py：
  它走老 durl 接口（匿名 480p），音轨只有 64–128 kbps；且下载整段视频很慢。
  要音质，正确做法是 playurl 的 dash.audio 里挑**码率最高**的那条（大会员可拿到 Dolby 448k），
  只下音频流（几 MB），再转 FLAC。

质量判据（唯一）：dash.audio 的最高 bandwidth（kbps）
  448k = 杜比全景声/高码率；192k = 标准最好；132k/64k = 一般。

用法：
  python -X utf8 project_b/bili_audio_fetch.py --from-missing --top 30 --min-audio 190
  python -X utf8 project_b/bili_audio_fetch.py --bv BV17VjjziEht --up up2
  python -X utf8 project_b/bili_audio_fetch.py --redo-existing      # 把已入库的 8 条换成高音质
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
DATA = ROOT / "data"
XLSX = DATA / "最优音频清单.xlsx"
OUT_ROOT = Path(r"E:\wx\王晰巡演_最优音频")
STAGE = ROOT / "temp" / "bili_audio_stage"
FFMPEG = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffmpeg.exe")
FFPROBE = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffprobe.exe")
QCACHE = ROOT / "temp" / "audio_quality_cache"
QCACHE.mkdir(parents=True, exist_ok=True)
STAGE.mkdir(parents=True, exist_ok=True)

TOURS = ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡", "签唱会")
ALIAS = {"一巡": ("Cherish", "珍晰", "一巡"), "二巡": ("二巡",), "三巡": ("图景", "三巡"),
         "四巡": ("肆益", "四巡"), "五巡": ("吾", "五巡"), "六巡": ("沉响与长歌", "「回」", "六巡")}
CITIES = [c.strip() for c in """
北京 上海 广州 深圳 杭州 南京 成都 武汉 西安 重庆 长沙 苏州 无锡 宁波 青岛 天津 厦门 郑州 沈阳 哈尔滨
海口 珠海 佛山 太原 南宁 昆明 鄂尔多斯 合肥 济南 福州 南昌 贵阳 兰州 银川 西宁 乌鲁木齐 呼和浩特 石家庄
长春 大连 常州 徐州 南通 温州 嘉兴 绍兴 金华 台州 泉州 东莞 惠州 中山 汕头 烟台 潍坊 洛阳 桂林 遵义
""".split()]


def load(n, p):
    import importlib.util
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


DL = load("dl", str(ROOT / "project_b" / "download_bilibili.py"))


def headers():
    ck = (DL.get_session_cookie() or "")
    extra = DL.load_bili_cookie() or ""
    if extra:
        ck = ck + "; " + extra
    return {"User-Agent": DL.UA, "Cookie": ck, "Referer": "https://www.bilibili.com/"}


def get(url, h, tries=3):
    wait = 15
    for _ in range(tries):
        try:
            return DL.http_get_json(url, headers=h)
        except Exception:
            time.sleep(wait); wait *= 2
    return None


def parse(text):
    d8 = re.search(r"(20\d{2})(\d{2})(\d{2})", text)
    date8 = d8.group(0) if d8 else ""
    tour = next((t for t, ws in ALIAS.items() if any(w in text for w in ws)), "")
    city = next((c for c in sorted(CITIES, key=len, reverse=True) if c in text), "")
    return date8, tour, city


def best_audio(bv, h):
    """返回 (audio_url, kbps, 是否杜比)。带缓存。"""
    p = QCACHE / (bv + ".json")
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    vj = get(f"https://api.bilibili.com/x/web-interface/view?bvid={bv}", h)
    if not vj or not vj.get("data"):
        return {}
    d = vj["data"]
    cid = ((d.get("pages") or [{}])[0]).get("cid")
    pj = get(f"https://api.bilibili.com/x/player/playurl?bvid={bv}&cid={cid}&qn=127&fnval=4048&fourk=1", h)
    dash = ((pj or {}).get("data") or {}).get("dash") or {}
    auds = list(dash.get("audio") or [])
    if dash.get("dolby") and (dash["dolby"].get("audio") or []):
        auds += dash["dolby"]["audio"]
    if dash.get("flac") and dash["flac"].get("audio"):
        auds += [dash["flac"]["audio"]]
    if not auds:
        return {}
    best = max(auds, key=lambda a: int(a.get("bandwidth") or 0))
    info = {"title": d.get("title"), "dur": d.get("duration"),
            "a_kbps": round(int(best.get("bandwidth") or 0) / 1000),
            "url": best.get("baseUrl") or best.get("base_url"),
            "codec": best.get("codecs"), "mime": best.get("mimeType")}
    p.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    return info


def download(url, dst, h):
    req = urllib.request.Request(url, headers={"User-Agent": h["User-Agent"], "Referer": h["Referer"]})
    with urllib.request.urlopen(req, timeout=120) as r, dst.open("wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    return dst.exists() and dst.stat().st_size > 10000


def safe(s):
    return re.sub(r'[\\/:*?"<>|]+', "_", s)[:88]


def upsert_row(ws, idx, src_key, row):
    for r in ws.iter_rows(min_row=2):
        if str(r[idx["原始路径"]].value or "").startswith(src_key):
            for k in ("巡次", "日期", "城市", "来源", "级别", "文件名", "目标路径",
                      "原始路径", "大小MB", "格式", "采样率", "位深", "码率kbps", "时长秒"):
                r[idx[k]].value = row.get(k)
            return "update"
    ws.append([row.get(c.value) for c in ws[1]])
    return "append"


def fetch_one(bv, h, up, title, ws, idx):
    q = best_audio(bv, h)
    if not q or not q.get("url"):
        return None
    d8, tour, city = parse(title or q.get("title") or "")
    tour = tour or "未标注"
    label = f"{d8 or '日期未知'}_{city or '城市未知'}"
    dst_dir = OUT_ROOT / tour / label
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"[B站-{safe(up)}]{safe(title or q.get('title') or bv)}.flac"
    tmp = STAGE / f"{bv}.m4a"
    if not download(q["url"], tmp, h):
        return None
    if not dst.exists():
        rr = subprocess.run([str(FFMPEG), "-y", "-loglevel", "error", "-i", str(tmp),
                             "-vn", "-c:a", "flac", str(dst)], capture_output=True)
        if rr.returncode != 0:
            return None
    pr = subprocess.run([str(FFPROBE), "-v", "quiet", "-show_streams", "-select_streams", "a:0",
                         "-of", "json", str(dst)], capture_output=True, text=True)
    try:
        a = (json.loads(pr.stdout or "{}").get("streams") or [{}])[0]
    except Exception:
        a = {}
    row = {"巡次": tour, "日期": d8, "城市": city, "来源": f"B站-{up}",
           "级别": f"A(B站音轨 {q.get('a_kbps')}kbps)", "文件名": dst.name,
           "目标路径": str(dst), "原始路径": f"https://www.bilibili.com/video/{bv}",
           "大小MB": round(dst.stat().st_size / 1048576, 1), "格式": "flac",
           "采样率": a.get("sample_rate"), "位深": a.get("bits_per_raw_sample"),
           "码率kbps": round(int(a.get("bit_rate") or 0) / 1000) or None,
           "时长秒": q.get("dur")}
    action = upsert_row(ws, idx, bv, row)
    print(f"  {q.get('a_kbps')}kbps {tour}/{label} [{action}] {dst.name[:60]}", flush=True)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-missing", action="store_true")
    ap.add_argument("--bv", default="")
    ap.add_argument("--up", default="B站")
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--min-audio", type=int, default=190)
    ap.add_argument("--redo-existing", action="store_true")
    args = ap.parse_args()

    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    idx = {c.value: i for i, c in enumerate(ws[1])}
    h = headers()

    targets = []
    if args.bv:
        targets = [(args.bv, args.up, args.bv)]
    elif args.redo_existing:
        for r in ws.iter_rows(min_row=2, values_only=True):
            src = str(r[idx["原始路径"]] or "")
            dstp = str(r[idx["目标路径"]] or "")
            nm = str(r[idx["文件名"]] or "")
            if not str(r[idx["来源"]] or "").startswith("B站-"):
                continue
            m = (re.search(r"(BV[0-9A-Za-z]+)", src)
                 or re.search(r"(BV[0-9A-Za-z]+)", dstp)
                 or re.search(r"(BV[0-9A-Za-z]+)", nm))
            if m:
                targets.append((m.group(1), str(r[idx["来源"]] or "B站-").replace("B站-", ""), nm))
    elif args.from_missing:
        miss = json.loads((ROOT / "temp" / "up_missing.json").read_text(encoding="utf-8"))["missing"]
        miss.sort(key=lambda x: ((x.get("src_w") or 0) * (x.get("src_h") or 0), x.get("play") or 0), reverse=True)
        targets = [(x["bv"], x["up"], x["title"]) for x in miss[: args.top]]

    print(f"目标 {len(targets)} 条；音频门槛 {args.min_audio} kbps", flush=True)
    done, low = 0, 0
    for i, (bv, up, title) in enumerate(targets, 1):
        q = best_audio(bv, h)
        ak = (q or {}).get("a_kbps") or 0
        print(f"[{i}/{len(targets)}] {bv} 音轨 {ak}kbps | {str(title)[:40]}", flush=True)
        if ak and ak < args.min_audio and not args.redo_existing:
            low += 1
            time.sleep(2)
            continue
        if fetch_one(bv, h, up, title, ws, idx):
            done += 1
        time.sleep(2)
    wb.save(XLSX)
    print(f"\n完成 {done} 条（音轨不足跳过 {low}）；Excel={XLSX}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
