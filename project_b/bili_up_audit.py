#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bili_up_audit.py —— 按 UP 主巡检「一到六巡高质量视频」，用码率给质量打分（可断点续跑）

质量判据（不靠标题党）：
  1. view 接口取 cid
  2. playurl（qn=127, fnval=4048）取 DASH 全部档位：width/height、codecid、bandwidth
  3. 以**最高档视频码率**为主：H.264 1080p ≥ 4 Mbps 算好料；HEVC/AV1 同画质码率可低 30%
  4. 音频码率单列（B站常见 128/192/320 kbps）

筛选：标题必须含「王晰」+ 巡演词；排除 混剪/剪辑/合集/群像/reaction/专访/花絮/预告
缓存：空间结果按 UP 存 temp/up_cache/<up>.json（24h）；码率按 BV 存 temp/up_quality_cache/<bv>.json
断点：每处理完一个 UP 就落盘一次 data/bili_up_audit.json

用法：
  python -X utf8 project_b/bili_up_audit.py --pages 2 --limit 40
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import urllib.parse
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data"
CACHE = ROOT / "temp" / "up_cache"
QCACHE = ROOT / "temp" / "up_quality_cache"
for d in (CACHE, QCACHE):
    d.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "project_b"))
from bili_rules import exclude_reason  # noqa: E402

MIDS = {
    "一只小陆_": "2031444",
    "up2": "98558549",
    "up3": "399411353",
    "up4": "417218821",
    "up5": "25283687",
    "up6": "485389682",
    "up7": "484404700",
    "up8": "438328208",
    "up9": "2702331",
}
TOUR_WORDS = ("巡演", "一巡", "二巡", "三巡", "四巡", "五巡", "六巡", "音乐会", "现场", "直拍", "点歌", "纯享", "live", "Live")
BAD_WORDS = ("混剪", "剪辑", "合集", "群像", "reaction", "盘点", "专访", "访谈", "花絮", "预告", "片段合集")
GAP = 8.0
OUT = DATA / "bili_up_audit.json"


# ---------- wbi 签名（0.2.2 起空间接口必须签名，否则返回 0 条） ----------
_TAB = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,
        37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]
_MK = {"key": None, "ts": 0.0}


def _wbi_mixin(m):
    if _MK["key"] and time.time() - _MK["ts"] < 3600:
        return _MK["key"]
    j = m.http_get_json("https://api.bilibili.com/x/web-interface/nav", headers={"User-Agent": m.UA})
    w = ((j.get("data") or {}).get("wbi_img") or {})
    img = (w.get("img_url") or "").rsplit("/", 1)[-1].split(".")[0]
    sub = (w.get("sub_url") or "").rsplit("/", 1)[-1].split(".")[0]
    raw = img + sub
    mi = "".join(raw[i] for i in _TAB)[:32]
    _MK["key"] = mi
    _MK["ts"] = time.time()
    return mi


def _wbi_sign(params, mk):
    params = dict(params)
    params["wts"] = round(time.time())
    p = dict(sorted(params.items()))
    q = urllib.parse.urlencode(p, quote_via=urllib.parse.quote)
    return q + "&w_rid=" + hashlib.md5((q + mk).encode()).hexdigest()


def load_dl():
    spec = importlib.util.spec_from_file_location("dl", str(ROOT / "project_b" / "download_bilibili.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def headers(m):
    ck = (m.get_session_cookie() or "")
    extra = m.load_bili_cookie() or ""
    if extra:
        ck = ck + "; " + extra
    return {"User-Agent": m.UA, "Cookie": ck, "Referer": "https://www.bilibili.com/"}


def get(m, url, h, tries=3):
    wait = 25
    for _ in range(tries):
        try:
            j = m.http_get_json(url, headers=h)
        except Exception as e:
            print("    exc", str(e)[:50], flush=True)
            time.sleep(wait); wait *= 2
            continue
        code = j.get("code")
        if code == 0:
            return j
        if code in (-799, -352, -403):
            print(f"    限流 {code}，等 {wait}s", flush=True)
            time.sleep(wait); wait *= 2
            continue
        return None
    return None


def space(m, h, mid, pages):
    out = []
    for pn in range(1, pages + 1):
        j = None
        try:
            mk = _wbi_mixin(m)
            q = _wbi_sign({"mid": mid, "ps": 50, "pn": pn, "order": "pubdate"}, mk)
            j = get(m, f"https://api.bilibili.com/x/space/wbi/arc/search?{q}", h)
        except Exception as e:
            print("    wbi 失败:", str(e)[:60], flush=True)
        if not j:
            j = get(m, f"https://api.bilibili.com/x/space/arc/search?mid={mid}&ps=50&pn={pn}&order=pubdate", h)
        if not j:
            break
        vl = ((j.get("data") or {}).get("list") or {}).get("vlist") or []
        out += vl
        cnt = ((j.get("data") or {}).get("page") or {}).get("count") or 0
        if len(out) >= cnt or not vl:
            break
        time.sleep(GAP)
    return out


def quality(m, h, bv, cid):
    p = QCACHE / (bv + ".json")
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    j = get(m, f"https://api.bilibili.com/x/player/playurl?bvid={bv}&cid={cid}&qn=127&fnval=4048&fourk=1", h, tries=2)
    q = {"v_kbps": None, "w": None, "h": None, "codec": None, "a_kbps": None}
    if j:
        dash = ((j.get("data") or {}).get("dash") or {})
        vids = dash.get("video") or []
        auds = (dash.get("audio") or [])
        if vids:
            best = max(vids, key=lambda v: int(v.get("bandwidth") or 0))
            q = {"v_kbps": round(int(best.get("bandwidth") or 0) / 1000),
                 "w": best.get("width"), "h": best.get("height"),
                 "codec": {7: "H.264", 12: "HEVC", 13: "AV1"}.get(int(best.get("codecid") or 0), "?"),
                 "a_kbps": (round(max(int(a.get("bandwidth") or 0) for a in auds) / 1000) if auds else None)}
    p.write_text(json.dumps(q, ensure_ascii=False), encoding="utf-8")
    return q


def local_bvs():
    s = set()
    try:
        led = json.loads(Path(r"E:\wx\论文素材_王晰作传\音域分析\场次音频\来源台账.json").read_text(encoding="utf-8"))
        s |= {x.get("bv") for x in (led.get("items") or []) if x.get("bv")}
    except Exception:
        pass
    for d in (Path(r"E:\wx\论文素材_王晰作传\B站\精选"), Path(r"E:\wx\论文素材_王晰作传\B站\官方空间")):
        if d.exists():
            s |= {p.name.split("_", 1)[0] for p in d.glob("*.mp4")}
    return {x for x in s if x}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=2)
    ap.add_argument("--limit", type=int, default=40)
    args = ap.parse_args()

    m = load_dl()
    h = headers(m)
    have = local_bvs()
    print(f"本地已有 BV {len(have)} 个", flush=True)

    doc = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "candidates": [], "ups": {}}
    if OUT.exists():
        try:
            doc = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            pass

    for name, mid in MIDS.items():
        cp = CACHE / (name + ".json")
        vids = None
        if cp.exists():
            try:
                d = json.loads(cp.read_text(encoding="utf-8"))
                if (time.time() - d.get("_ts", 0)) / 3600 < 24:
                    vids = d.get("videos") or []
                    print(f"[{name}] 缓存 {len(vids)} 条", flush=True)
            except Exception:
                pass
        if vids is None:
            vids = space(m, h, mid, args.pages)
            cp.write_text(json.dumps({"_ts": time.time(), "videos": vids}, ensure_ascii=False), encoding="utf-8")
            print(f"[{name}] 抓到 {len(vids)} 条", flush=True)
            time.sleep(GAP)

        picked = 0
        for v in vids:
            bv = v.get("bvid"); title = (v.get("title") or "").strip()
            if not bv or "王晰" not in title:
                continue
            if any(w in title for w in BAD_WORDS) or not any(w in title for w in TOUR_WORDS):
                continue
            if bv in have or any(c["bvid"] == bv for c in doc["candidates"]):
                continue
            if exclude_reason(title, bv):
                continue
            if picked >= 6:
                break
            cid = None
            vj = get(m, f"https://api.bilibili.com/x/web-interface/view?bvid={bv}", h, tries=2)
            if vj:
                d = vj.get("data") or {}
                cid = ((d.get("pages") or [{}])[0]).get("cid")
                dur = d.get("duration")
            else:
                dur = None
            q = quality(m, h, bv, cid) if cid else {}
            doc["candidates"].append({"bvid": bv, "title": title, "up": name, "mid": mid,
                                      "duration": dur, "play": v.get("play"), **q})
            picked += 1
            print(f"   + {bv} {q.get('v_kbps')}kbps {q.get('w')}x{q.get('h')} {q.get('codec')} {title[:34]}", flush=True)
            time.sleep(GAP)
        doc["ups"][name] = {"mid": mid, "videos": len(vids)}
        doc["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    cands = doc["candidates"]
    cands.sort(key=lambda c: (c.get("v_kbps") or 0), reverse=True)
    md = ["# UP 主巡检：一到六巡高质量候选", "", f"> {doc['generated_at']}｜候选 {len(cands)} 条", "",
          "| Mbps | 分辨率 | 编码 | 音频kbps | UP | 时长 | 标题 | BV |", "|---|---|---|---|---|---|---|---|"]
    for c in cands[:40]:
        md.append(f"| {(c.get('v_kbps') or 0)/1000:.2f} | {c.get('w')}x{c.get('h')} | {c.get('codec')} | {c.get('a_kbps')} | "
                  f"{c['up']} | {c.get('duration')}s | {c['title'][:40]} | {c['bvid']} |")
    (DATA / "bili_up_audit.md").write_text("\n".join(md), encoding="utf-8")
    print("\n写出 data/bili_up_audit.json / .md", flush=True)
    for c in cands[:10]:
        print(f"  {(c.get('v_kbps') or 0)/1000:5.2f} Mbps {c.get('h')}p {c.get('codec')} {c['bvid']} {c['title'][:40]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
