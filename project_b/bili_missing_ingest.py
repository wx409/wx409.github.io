#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_missing_ingest.py —— 从未收录清单里挑高码率视频：取码率 → 下载 → 抽 FLAC → 入最优音频 → 追加 Excel

输入：temp/up_missing.json（bili_up_audit 空间扫描得到的未收录清单）
步骤：
  1 对候选按「源分辨率×播放量」排序，取前 N 条逐个查 playurl 真实码率（带登录 cookie）
  2 按码率降序，每个 UP 最多取 --per-up 条，且 ≥ --min-mbps
  3 download_bilibili.py 下载视频 → ffmpeg 抽 FLAC
  4 复制到 E:\\wx\\王晰巡演_最优音频\\<巡次>\\<YYYYMMDD_城市>\\[B站-<UP>]标题.flac
  5 追加 Excel（data/最优音频清单.xlsx）

只读源，不删除任何文件。已存在目标/已登记则跳过。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
MISSING = ROOT / "temp" / "up_missing.json"
QOUT = ROOT / "temp" / "up_missing_quality.json"
XLSX = DATA / "最优音频清单.xlsx"
OUT_ROOT = Path(r"E:\wx\王晰巡演_最优音频")
STAGE = ROOT / "temp" / "bili_stage"
FFMPEG = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffmpeg.exe")
FFPROBE = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffprobe.exe")
QCACHE = ROOT / "temp" / "up_quality_cache"
QCACHE.mkdir(parents=True, exist_ok=True)

TOURS = ("一巡", "二巡", "三巡", "四巡", "五巡", "六巡", "签唱会")
CITIES = [c.strip() for c in """
北京 上海 广州 深圳 杭州 南京 成都 武汉 西安 重庆 长沙 苏州 无锡 宁波 青岛 天津 厦门 郑州 沈阳 哈尔滨
海口 珠海 佛山 太原 南宁 昆明 鄂尔多斯 合肥 济南 福州 南昌 贵阳 兰州 银川 西宁 乌鲁木齐 呼和浩特 石家庄
长春 大连 常州 徐州 南通 温州 嘉兴 绍兴 金华 台州 泉州 东莞 惠州 中山 汕头 烟台 潍坊 洛阳 桂林 遵义
""".split()]


def load(name, path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


DL = load("dl", str(ROOT / "project_b" / "download_bilibili.py"))
AUD = load("aud", str(ROOT / "project_b" / "bili_up_audit.py"))


def headers():
    ck = (DL.get_session_cookie() or "")
    extra = DL.load_bili_cookie() or ""
    if extra:
        ck = ck + "; " + extra
    return {"User-Agent": DL.UA, "Cookie": ck, "Referer": "https://www.bilibili.com/"}


def parse(text):
    date8 = ""
    for pat in (r"(20\d{2})(\d{2})(\d{2})", r"(20\d{2})[.\-_/年](\d{1,2})[.\-_/月](\d{1,2})"):
        for m in re.finditer(pat, text):
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
                date8 = f"{y}{mo:02d}{d:02d}"
                break
        if date8:
            break
    tour = next((x for x in TOURS if x in text), "")
    city = next((c for c in sorted(CITIES, key=len, reverse=True) if c in text), "")
    return date8, tour, city


def probe(bv, h):
    p = QCACHE / (bv + ".json")
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    vj = AUD.get(DL, f"https://api.bilibili.com/x/web-interface/view?bvid={bv}", h, tries=2)
    if not vj or not vj.get("data"):
        return {}
    d = vj["data"]
    cid = ((d.get("pages") or [{}])[0]).get("cid")
    if not cid:
        return {}
    pj = AUD.get(DL, f"https://api.bilibili.com/x/player/playurl?bvid={bv}&cid={cid}&qn=127&fnval=4048&fourk=1", h, tries=2)
    q = {"dur": d.get("duration"), "title": d.get("title")}
    vids = (((pj or {}).get("data") or {}).get("dash") or {}).get("video") or []
    auds = (((pj or {}).get("data") or {}).get("dash") or {}).get("audio") or []
    if vids:
        best = max(vids, key=lambda v: int(v.get("bandwidth") or 0))
        q.update({"v_kbps": round(int(best.get("bandwidth") or 0) / 1000),
                  "w": best.get("width"), "h": best.get("height"),
                  "codec": {7: "H.264", 12: "HEVC", 13: "AV1"}.get(int(best.get("codecid") or 0), "?"),
                  "a_kbps": round(max((int(a.get("bandwidth") or 0) for a in auds), default=0) / 1000) or None})
    p.write_text(json.dumps(q, ensure_ascii=False), encoding="utf-8")
    return q


def safe(s):
    return re.sub(r'[\\/:*?"<>|]+', "_", s)[:90]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", type=int, default=24)
    ap.add_argument("--per-up", type=int, default=2)
    ap.add_argument("--min-mbps", type=float, default=2.0)
    ap.add_argument("--max", type=int, default=12)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    d = json.loads(MISSING.read_text(encoding="utf-8"))
    items = d.get("missing") or []
    items.sort(key=lambda x: ((x.get("src_w") or 0) * (x.get("src_h") or 0), x.get("play") or 0), reverse=True)
    cand = items[: args.probe]
    h = headers()
    print(f"待查码率 {len(cand)} 条（未收录共 {len(items)}）", flush=True)

    for i, it in enumerate(cand, 1):
        q = probe(it["bv"], h)
        it.update(q or {})
        print(f"[{i}/{len(cand)}] {it['bv']} {(it.get('v_kbps') or 0)/1000:.2f} Mbps "
              f"{it.get('w')}x{it.get('h')} {it.get('codec')} | {it['title'][:36]}", flush=True)
        time.sleep(5)
    QOUT.write_text(json.dumps(cand, ensure_ascii=False, indent=1), encoding="utf-8")

    ok = [x for x in cand if (x.get("v_kbps") or 0) / 1000 >= args.min_mbps]
    ok.sort(key=lambda x: x.get("v_kbps") or 0, reverse=True)
    picked, seen = [], {}
    for x in ok:
        u = x["up"]
        if seen.get(u, 0) >= args.per_up:
            continue
        seen[u] = seen.get(u, 0) + 1
        picked.append(x)
        if len(picked) >= args.max:
            break
    print(f"\n≥{args.min_mbps} Mbps：{len(ok)} 条；本次取 {len(picked)} 条", flush=True)
    for x in picked:
        print(f"  {(x['v_kbps'])/1000:5.2f} Mbps {x['up']:8} {x['bv']} {x['title'][:40]}", flush=True)
    if args.dry_run or not picked:
        return 0

    # 登记已有
    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    cols = [c.value for c in ws[1]]
    existing = {str(r[7]) for r in ws.iter_rows(min_row=2, values_only=True) if r and r[7]}

    STAGE.mkdir(parents=True, exist_ok=True)
    added = 0
    for x in picked:
        bv = x["bv"]
        txt = STAGE / f"{bv}.txt"
        txt.write_text(bv, encoding="utf-8")
        print(f"\n下载 {bv} …", flush=True)
        r = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "project_b" / "download_bilibili.py"),
                            str(txt), "--out", str(STAGE)], cwd=str(ROOT))
        mp4 = next((p for p in STAGE.glob(f"{bv}_*.mp4")), None)
        if r.returncode != 0 or not mp4:
            print("  下载失败/找不到文件，跳过", flush=True)
            continue
        if str(mp4) in existing:
            print("  已登记过，跳过", flush=True)
            continue
        d8, tour, city = parse(x["title"])
        tour = tour or "未标注"
        dst_dir = OUT_ROOT / tour / f"{d8 or '日期未知'}_{city or '城市未知'}"
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / f"[B站-{safe(x['up'])}]{safe(x['title'])}.flac"
        if not dst.exists():
            rr = subprocess.run([str(FFMPEG), "-y", "-loglevel", "error", "-i", str(mp4),
                                 "-vn", "-c:a", "flac", str(dst)], capture_output=True)
            if rr.returncode != 0:
                print("  抽音频失败", flush=True); continue
        pr = subprocess.run([str(FFPROBE), "-v", "quiet", "-show_streams", "-select_streams", "a:0",
                             "-of", "json", str(dst)], capture_output=True, text=True)
        try:
            a = (json.loads(pr.stdout or "{}").get("streams") or [{}])[0]
        except Exception:
            a = {}
        row = {"巡次": tour, "日期": d8, "城市": city, "来源": f"B站-{x['up']}",
               "级别": f"B(B站 {x['v_kbps']/1000:.1f}Mbps {x.get('w')}x{x.get('h')})",
               "文件名": dst.name, "目标路径": str(dst), "原始路径": str(mp4),
               "大小MB": round(dst.stat().st_size / 1048576, 1), "格式": "flac",
               "采样率": a.get("sample_rate"), "位深": a.get("bits_per_raw_sample"),
               "码率kbps": round(int(a.get("bit_rate") or 0) / 1000) or None, "时长秒": round(float(x.get("dur") or 0), 1)}
        ws.append([row.get(k) for k in cols])
        existing.add(str(mp4))
        added += 1
        print(f"  -> {dst.relative_to(OUT_ROOT)}", flush=True)
    wb.save(XLSX)
    print(f"\n完成：新增 {added} 条；Excel={XLSX}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
