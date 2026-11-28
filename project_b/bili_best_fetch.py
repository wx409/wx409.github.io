#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_best_fetch.py —— 一条视频、多份用途：最高质量视频 + 最高音质音频，一次抓全

第一性原理（用户明确）：**音频质量优先**（声学实测 + 未来 ASMR），大会员已就绪，能拿到的最好就全拿。

每条的产出：
  ① 视频：playurl 里 bandwidsth 最高的视频流（VIP 可 4K/HEVC）→ 与音轨 mux 成 .mp4
           存 E:\\wx\\王晰巡演_视频源\\<巡次>\\<YYYYMMDD_城市>\\[B站-<UP>]标题.mp4
           （视频只下一次，供 ASMR/画面/切片等其它用途复用）
  ② 音频：playurl 里最高的音频流（优先 flac > dolby > 普通 aac）→ 转 FLAC
           存 E:\\wx\\王晰巡演_最优音频\\<巡次>\\<YYYYMMDD_城市>\\[B站-<UP>]标题.flac
  ③ Excel：每个 BV 一行（按 BV 去重），登记视频路径、音频路径、视频码率/分辨率、音频码率

质量规则（替换策略）：
  - 同一 BV 若已有更差版本（音频码率更低），用新抓的覆盖，并更新该行
  - 绝不产生 `[B站-x][B站-x]` 这类重复前缀（名字统一由 title 生成，title 会先去掉已有前缀）
  - 只读 B站，不删除源；本脚本只覆盖自己目录下的产物

用法：
  python -X utf8 project_b/bili_best_fetch.py --bv BV17VjjziEht --up up2
  python -X utf8 project_b/bili_best_fetch.py --from-missing --top 12
  python -X utf8 project_b/bili_best_fetch.py --bvs-file temp/bv_list.txt
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
AUD_ROOT = Path(r"E:\wx\王晰巡演_最优音频")
VID_ROOT = Path(r"E:\wx\王晰巡演_视频源")
STAGE = ROOT / "temp" / "bili_best_stage"
FFMPEG = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffmpeg.exe")
FFPROBE = Path(r"C:\Users\yezhe\AppData\Local\video-to-skill\tools\ffprobe.exe")
QCACHE = ROOT / "temp" / "best_quality_cache"
for d in (STAGE, QCACHE):
    d.mkdir(parents=True, exist_ok=True)

ALIAS = {"一巡": ("Cherish", "珍晰", "一巡"), "二巡": ("二巡",), "三巡": ("图景", "三巡"),
         "四巡": ("肆益", "四巡"), "五巡": ("吾", "五巡"), "六巡": ("沉响与长歌", "「回」", "六巡")}
CITIES = [c.strip() for c in """
北京 上海 广州 深圳 杭州 南京 成都 武汉 西安 重庆 长沙 苏州 无锡 宁波 青岛 天津 厦门 郑州 沈阳 哈尔滨
海口 珠海 佛山 太原 南宁 昆明 鄂尔多斯 合肥 济南 福州 南昌 贵阳 兰州 银川 西宁 乌鲁木齐 呼和浩特 石家庄
长春 大连 常州 徐州 南通 温州 嘉兴 绍兴 金华 台州 泉州 东莞 惠州 中山 汕头 烟台 潍坊 洛阳 桂林 遵义
莫斯科
""".split()]


def load(n, p):
    import importlib.util
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


DL = load("dl", str(ROOT / "project_b" / "download_bilibili.py"))


VIDEO_POLICY = "auto"


from ingest_filters import excluded  # noqa: E402


BLACKLIST = {}
_bl = DATA / "ingest_blacklist.json"
if _bl.exists():
    try:
        BLACKLIST = {x["bv"]: x.get("reason", "") for x in json.loads(_bl.read_text(encoding="utf-8"))}
    except Exception:
        BLACKLIST = {}


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


def strip_prefix(name: str) -> str:
    return re.sub(r"^(?:\[B站-[^\]]+\])+", "", name)


def clean_flac_name(name: str) -> str:
    n = strip_prefix(name)
    n = re.sub(r"(?:\.flac)+$", "", n, flags=re.I)
    return n.strip()


def parse(text):
    m = re.search(r"(20\d{2})(\d{2})(\d{2})", text)
    date8 = m.group(0) if m else ""
    tour = next((t for t, ws in ALIAS.items() if any(w in text for w in ws)), "")
    city = next((c for c in sorted(CITIES, key=len, reverse=True) if c in text), "")
    return date8, tour, city


def safe(s, n=80):
    return re.sub(r'[\\/:*?"<>|\s]+', "_", s)[:n]


def streams(bv, h, force=False):
    """返回 dict：video 最优、audio 最优（优先 flac/dolby）、标题、时长。

    注意：playurl 里的 CDN 地址会过期（约 2 小时），所以缓存只存 30 分钟；
    过期后重新取，避免复用死链导致 HTTP 403。
    """
    p = QCACHE / (bv + ".json")
    if p.exists() and not force:
        try:
            if time.time() - p.stat().st_mtime < 1800:
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
    vids = dash.get("video") or []
    auds = list(dash.get("audio") or [])
    hi = []
    if dash.get("flac") and dash["flac"].get("audio"):
        hi.append(("flac", dash["flac"]["audio"]))
    if dash.get("dolby") and (dash["dolby"].get("audio") or []):
        hi += [("dolby", a) for a in dash["dolby"]["audio"]]
    vmax = {"1080p": 1080, "max": 9999, "auto": 1080, "none": 0}[VIDEO_POLICY]
    pool_v = [v for v in vids if (v.get("height") or 0) <= vmax] or vids
    best_v = max(pool_v, key=lambda v: int(v.get("bandwidth") or 0)) if pool_v else None
    pool = hi or [("aac", a) for a in auds]
    best_a = max(pool, key=lambda t: int(t[1].get("bandwidth") or 0)) if pool else None
    out = {
        "title": d.get("title"), "dur": d.get("duration"),
        "v_url": (best_v or {}).get("baseUrl") or (best_v or {}).get("base_url"),
        "v_kbps": round(int((best_v or {}).get("bandwidth") or 0) / 1000),
        "v_w": (best_v or {}).get("width"), "v_h": (best_v or {}).get("height"),
        "v_codec": (best_v or {}).get("codecs"),
        "a_url": (best_a or (None, {}))[1].get("baseUrl") or (best_a or (None, {}))[1].get("base_url"),
        "a_kbps": round(int(((best_a or (None, {}))[1]).get("bandwidth") or 0) / 1000),
        "a_kind": (best_a or ("?",))[0],
        "a_codec": ((best_a or (None, {}))[1]).get("codecs"),
    }
    p.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def download(url, dst, h, retries=2):
    if not url:
        return False
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": h["User-Agent"], "Referer": h["Referer"],
                "Origin": "https://www.bilibili.com", "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=180) as r, dst.open("wb") as f:
                while True:
                    b = r.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            if dst.exists() and dst.stat().st_size > 20000:
                return True
        except Exception as e:
            print(f"    下载失败({type(e).__name__}:{getattr(e, 'code', '')}) 第 {attempt+1} 次", flush=True)
            time.sleep(3)
    return False


def upsert(ws, idx, bv, row):
    for r in ws.iter_rows(min_row=2):
        src = str(r[idx["原始路径"]].value or "")
        if bv in src:
            for k, v in row.items():
                r[idx[k]].value = v
            return "updated"
    ws.append([row.get(c.value) for c in ws[1]])
    return "appended"


def fetch(bv, up, h, ws, idx, dry=False):
    q = streams(bv, h)
    if not q or not q.get("a_url"):
        return None
    if bv in BLACKLIST:
        print(f"  跳过：黑名单（{BLACKLIST[bv]}）", flush=True)
        return None
    why = excluded(q.get("title") or "")
    if why:
        print(f"  跳过：{why} — {str(q.get('title'))[:40]}", flush=True)
        return None
    title = clean_flac_name(q.get("title") or bv)
    d8, tour, city = parse(title)
    tour = tour or "未标注"
    label = f"{d8 or '日期未知'}_{city or '城市未知'}"
    aud_dir = AUD_ROOT / tour / label
    vid_dir = VID_ROOT / tour / label
    base = f"[B站-{safe(up, 20)}]{safe(title)}"
    aud = aud_dir / (base + ".flac")
    vid = vid_dir / (base + ".mp4")
    if dry:
        print(f"  [dry] {q['a_kbps']}kbps/{q['a_kind']} 视频{q['v_kbps']}kbps {q['v_w']}x{q['v_h']} -> {tour}/{label}")
        return {"a": aud, "v": vid}
    aud_dir.mkdir(parents=True, exist_ok=True)
    vid_dir.mkdir(parents=True, exist_ok=True)

    # 音频
    tmp_a = STAGE / f"{bv}.m4a"
    if not (aud.exists() and aud.stat().st_size > 100000):
        ok = download(q["a_url"], tmp_a, h)
        if not ok:
            q2 = streams(bv, h, force=True)      # 链接可能过期，重新取一次
            ok = download((q2 or {}).get("a_url"), tmp_a, h)
        if not ok:
            print("  音频下载失败（已重试）", flush=True); return None
        r = subprocess.run([str(FFMPEG), "-y", "-loglevel", "error", "-i", str(tmp_a),
                            "-vn", "-c:a", "flac", str(aud)], capture_output=True)
        if r.returncode != 0:
            print("  转 FLAC 失败"); return None
    # 视频：按策略决定是否下载（none=只存音频；auto=仅整场留 1080p；1080p/max=按上限）
    keep_video = VIDEO_POLICY in ("1080p", "max") or (
        VIDEO_POLICY == "auto" and (int(q.get("dur") or 0) >= 2400
                                    or any(k in title for k in ("全场", "上半场", "下半场", "整场", "完整"))))
    if keep_video and not (vid.exists() and vid.stat().st_size > 1000000):
        tmp_v = STAGE / f"{bv}.v.m4s"
        if download(q["v_url"], tmp_v, h):
            subprocess.run([str(FFMPEG), "-y", "-loglevel", "error", "-i", str(tmp_v),
                            "-i", str(tmp_a) if tmp_a.exists() else str(aud),
                            "-c", "copy", "-map", "0:v:0", "-map", "1:a:0", str(vid)], capture_output=True)
            try:
                tmp_v.unlink()
            except Exception:
                pass
    # 探测音频参数
    pr = subprocess.run([str(FFPROBE), "-v", "quiet", "-show_streams", "-select_streams", "a:0",
                         "-of", "json", str(aud)], capture_output=True, text=True)
    try:
        a = (json.loads(pr.stdout or "{}").get("streams") or [{}])[0]
    except Exception:
        a = {}
    row = {"巡次": tour, "日期": d8, "城市": city, "来源": f"B站-{up}",
           "级别": f"A(B站 {q['a_kind']} {q['a_kbps']}kbps / 视频{q['v_kbps']}kbps {q['v_w']}x{q['v_h']})",
           "文件名": aud.name, "目标路径": str(aud),
           "原始路径": f"https://www.bilibili.com/video/{bv}",
           "大小MB": round(aud.stat().st_size / 1048576, 1), "格式": "flac",
           "采样率": a.get("sample_rate"), "位深": a.get("bits_per_raw_sample"),
           "码率kbps": round(int(a.get("bit_rate") or 0) / 1000) or None, "时长秒": q.get("dur")}
    act = upsert(ws, idx, bv, row)
    print(f"  {q['a_kbps']}kbps {q['a_kind']} 视频{q['v_kbps']}kbps {q['v_w']}x{q['v_h']} [{act}] {aud.name[:56]}")
    return {"a": aud, "v": vid}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bv", default="")
    ap.add_argument("--up", default="B站")
    ap.add_argument("--bvs-file", default="")
    ap.add_argument("--from-missing", action="store_true")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--video", default="auto", choices=["auto", "none", "1080p", "max"],
                    help="视频策略：auto=整场留1080p、单曲不留；none=只存音频；1080p/max=按指定上限")
    args = ap.parse_args()

    global VIDEO_POLICY
    VIDEO_POLICY = args.video
    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb["最优音频"]
    idx = {c.value: i for i, c in enumerate(ws[1])}
    h = headers()

    targets = []
    if args.bv:
        targets = [(args.bv, args.up)]
    elif args.bvs_file:
        for ln in Path(args.bvs_file).read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln.startswith("BV"):
                parts = ln.split()
                targets.append((parts[0], parts[1] if len(parts) > 1 else "B站"))
    elif args.from_missing:
        miss = json.loads((ROOT / "temp" / "up_missing.json").read_text(encoding="utf-8"))["missing"]
        miss.sort(key=lambda x: ((x.get("src_w") or 0) * (x.get("src_h") or 0), x.get("play") or 0), reverse=True)
        targets = [(x["bv"], x["up"]) for x in miss[: args.top]]

    print(f"目标 {len(targets)} 条", flush=True)
    ok = 0
    for i, (bv, up) in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {bv} ({up})", flush=True)
        if fetch(bv, up, h, ws, idx, dry=args.dry_run):
            ok += 1
        if not args.dry_run:
            wb.save(XLSX)
        time.sleep(2)
    if not args.dry_run:
        wb.save(XLSX)
    print(f"\n完成 {ok}/{len(targets)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
