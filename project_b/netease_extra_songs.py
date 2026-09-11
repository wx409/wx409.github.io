# -*- coding: utf-8 -*-
"""网易云独有曲目 → 取源 + 实测（网易云有音源、QQ 无或未测的曲目）。

背景（用户 2026-09-11 指示）：网易云有几首**独有**曲目（如《三十三》2022-05-01 电视剧《好好说话》插曲），
QQ 音源拿不到，需要走网易云取源再进声学实测。

复用：网易云外链直链 `https://music.163.com/song/media/outer/url?id=<id>.mp3`
      （同 音域分析\\轨迹\\网易云取源复测.py 的做法，不另造轮子）
      + 既有测量引擎 音域分析\\批量专辑音域.py --root <网易云独有\\音频>

产物：
  音域分析\\网易云独有\\音频\\<曲名>.mp3        取源音频
  音域分析\\网易云独有\\音频_分析\\*_stats.json  逐曲指标（--measure）
  音域分析\\网易云独有\\音频_汇总.json          汇总（供 data/vocal_measurements.json 的 single 层）
  data\\netease_only.json                       独有曲目清单（站点可引用，元数据）

用法：
  python -X utf8 project_b/netease_extra_songs.py --list               # 列清单（不下载）
  python -X utf8 project_b/netease_extra_songs.py --download 5         # 取源 5 首
  python -X utf8 project_b/netease_extra_songs.py --measure            # 对已取源曲目实测并汇总
  python -X utf8 project_b/netease_extra_songs.py --limit 5 --all      # 取源+实测一条龙
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ANA = Path(r"E:\wx\论文素材_王晰作传\音域分析")
WORK = ANA / "网易云独有"
# ⚠ 批量专辑音域.py 把 --root 的**每个子目录当作一张专辑**，所以这里多一层：
#   <root=网易云独有\音频> / 网易云独有（专辑名） / <曲名>.mp3
AUDIO = WORK / "音频" / "网易云独有"
OUT_JSON = DATA / "netease_only.json"
PY = sys.executable
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36")
# 排除：Live/综艺/晚会/合辑（非独有录音室作品）
EXCLUDE = re.compile(r"live|现场|我是歌手|声入人心|追光吧|超级歌单|晚会|盛典|音乐节|春晚|中秋|合辑|群星|央视|新年", re.I)


def measured() -> set[str]:
    out = set()
    for key in ("songs", "items"):
        for s in (json.loads((ANA / "专辑音域汇总.json").read_text(encoding="utf-8")).get(key) or []):
            t = str(s.get("title") or s.get("name") or "").strip()
            if t:
                out.add(t)
    return out


def candidates() -> list[dict]:
    cat = (json.loads((DATA / "netease_catalog.json").read_text(encoding="utf-8")).get("songs") or {})
    have = measured()
    out = []
    for k, v in cat.items():
        name = str(v.get("name") or k)
        album = str(v.get("album") or "")
        if "王晰" not in str(v.get("artists") or ""):
            continue
        if EXCLUDE.search(name) or EXCLUDE.search(album):
            continue
        if name in have:
            continue
        out.append({"song": name, "id": v.get("id"), "album": album})
    return sorted(out, key=lambda x: str(x["album"]))


def download(items: list[dict]) -> int:
    AUDIO.mkdir(parents=True, exist_ok=True)
    ok = 0
    for it in items:
        dst = AUDIO / f"{it['song']}.mp3"
        if dst.exists() and dst.stat().st_size > 200_000:
            print(f"   [--] 已存在 {it['song']}")
            ok += 1
            continue
        url = f"https://music.163.com/song/media/outer/url?id={it['id']}.mp3"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://music.163.com/"})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
            if len(data) < 200_000:
                print(f"   [FAIL] {it['song']}：直链返回过小（{len(data)}B，可能需会员）")
                continue
            dst.write_bytes(data)
            print(f"   [OK] {it['song']}（{len(data)/1024/1024:.1f} MB，{it['album'][:20]}）")
            ok += 1
        except Exception as e:
            print(f"   [FAIL] {it['song']}：{type(e).__name__} {e}")
    return ok


def measure() -> bool:
    r = subprocess.run([PY, "-X", "utf8", str(ANA / "批量专辑音域.py"), "--root", str(AUDIO)],
                       cwd=str(ANA), capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-6:]
    for l in tail:
        print("   ", l)
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--download", type=int, default=0, metavar="N")
    ap.add_argument("--songs", default="", help="只处理指定曲目（逗号分隔），优先级高于 --download")
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--all", action="store_true", help="取源 + 实测一条龙")
    a = ap.parse_args()

    cand = candidates()
    print(f"=== 网易云独有（未测、排除 Live/综艺）{len(cand)} 首 ===")
    for it in cand:
        print(f"   {it['song']:<18} | {str(it['album'])[:34]} | id {it['id']}")
    OUT_JSON.write_text(json.dumps({
        "schema": 1, "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": "网易云有音源、QQ 无或未测的曲目（独有单曲/OST）。取源后进声学实测，归入「单曲层」。",
        "count": len(cand),
        "items": [{"song": x["song"], "album": x["album"], "netease_id": x["id"]} for x in cand],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {OUT_JSON}")
    if a.list or not (a.download or a.all):
        print("（--download N 取源；--all 取源+实测一条龙）")
        return 0

    n = a.download or (a.limit if a.all else 0)
    picks = cand[:n]
    if a.songs:
        want = [s.strip() for s in a.songs.split(",") if s.strip()]
        picks = [c for c in cand if c["song"] in want]
        missing = [w for w in want if w not in {c["song"] for c in cand}]
        if missing:
            print(f"[注意] 指定曲目不在候选中（可能已测或非独有）：{missing}")
    print(f"\n取源 {len(picks)} 首：")
    ok = download(picks)
    print(f"取源成功 {ok}/{len(picks)}")
    if a.all or a.measure:
        print("\n实测（复用 批量专辑音域.py）：")
        measure()
        print("下一步：python -X utf8 project_b/build_vocal_longtable.py  # 归入 single 层")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
