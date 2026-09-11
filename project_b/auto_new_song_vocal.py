# -*- coding: utf-8 -*-
"""新歌/新专辑 → 声学记录 自动链路（检测 到 下载 到 实测 到 站点数据）。

补上的那一段空白：`watch_releases.py` 每天能**发现**新歌（写 data/pending_releases.json），
`一键音域实测.py` 能**一次跑完**下载+测量+报告，但两者之间原来是人工（要手敲
`添加待测曲目.py "歌名"`）。本脚本把这一步接上，于是「有新歌 → 有声学记录」变成每日自动。

流程（幂等，无新歌时秒退）：
  1) 读 data/pending_releases.json（发行 + Live 两条线）
  2) 与 音域分析\\专辑音域汇总.json 已测曲目比对 → 找出未测的
  3) 过「排除词表」把关（混剪/伴奏/AI翻唱等一律拒绝入库）
  4) 追加进 音域分析\\待测清单.json
  5) 跑 批量下载专辑.py --extra → 批量专辑音域.py → 生成专辑音域报告.py
     （站点 JSON/页面由 deploy_all 的既有步骤接管）

用法：
  python -X utf8 project_b/auto_new_song_vocal.py            # 自动处理（无新歌则秒退）
  python -X utf8 project_b/auto_new_song_vocal.py --check    # 只报告差异，不下载不测量
  python -X utf8 project_b/auto_new_song_vocal.py --limit 5  # 每次最多处理 5 首（默认 8）
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ANA = Path(r"E:\wx\论文素材_王晰作传\音域分析")
PENDING = DATA / "pending_releases.json"
EXTRA = ANA / "待测清单.json"
SUMMARY = ANA / "专辑音域汇总.json"
PY = sys.executable


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def measured_titles() -> set[str]:
    out = set()
    for key in ("songs", "items"):
        for s in (load(SUMMARY, {}) or {}).get(key) or []:
            t = str(s.get("title") or s.get("name") or "").strip()
            if t:
                out.add(t)
    return out


def excluded_hits(text: str) -> list[str]:
    try:
        sys.path.insert(0, str(ANA))
        from 排除词表 import hit_words          # type: ignore
        return list(hit_words(text) or [])
    except Exception:
        # 词表不可用时用最小内置集兜底（宁可少收，不可收污染样本）
        import re
        pat = re.compile(r"混剪|伪合唱|AI翻唱|消音|伴奏|人声增强|音频重制|铃声|串烧", re.I)
        return pat.findall(text)


def candidates(limit: int) -> tuple[list[dict], list[dict], list[dict]]:
    """返回 (可入录音室层的未测新发行, 待人工决定的 Live 版, 被排除词表拦下的)。

    层级纪律：录音室层（archive_vocal_albums.json）只收**录音室发行**；
    他人主导的 Live（声入人心/我是歌手/追光吧…）不进这一层，否则会污染 72 曲全量统计，
    它们走「现场/舞台」层（archive_stage*）——故此处只登记不自动测量（--include-live 可强制）。
    """
    pend = load(PENDING, {}) or {}
    have = measured_titles()
    listed = {str(x.get("mid") or "") for x in (load(EXTRA, {}) or {}).get("items") or []}
    fresh, live_hold, rejected = [], [], []
    for kind in ("releases", "live"):
        for it in pend.get(kind) or []:
            title = str(it.get("name") or "").strip()
            mid = str(it.get("mid") or "").strip()
            album = str(it.get("album") or "").strip()
            if not title or not mid or mid in listed:
                continue
            base = title.replace(" (Live)", "").strip()
            if kind == "releases" and (title in have or base in have):
                continue
            hits = excluded_hits(f"{title} {album}")
            row = {"album": album or ("Live 现场" if kind == "live" else "单曲"),
                   "title": title, "mid": mid, "kind": kind,
                   "note": "auto_new_song_vocal 自动登记"}
            if hits:
                rejected.append({**row, "hits": hits})
            elif kind == "live":
                live_hold.append(row)
            else:
                fresh.append(row)
    return fresh[:limit], live_hold[:limit], rejected


def run(cmd: list[str], desc: str) -> bool:
    r = subprocess.run(cmd, cwd=str(ANA), capture_output=True, text=True, encoding="utf-8", errors="replace")
    ok = r.returncode == 0
    print(f"  [{'OK' if ok else 'FAIL'}] {desc}" + ("" if ok else f"｜{(r.stderr or r.stdout or '')[-200:]}"))
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--include-live", action="store_true",
                    help="把他人主导 Live 版也并入待测（默认只登记不测，避免污染录音室层统计）")
    args = ap.parse_args()

    fresh, live_hold, rejected = candidates(args.limit)
    print(f"=== 新歌入声学记录｜{datetime.now():%Y-%m-%d %H:%M} ===")
    print(f"录音室新发行待处理 {len(fresh)} 首｜他人主导 Live 待决定 {len(live_hold)} 首｜排除词表拦下 {len(rejected)} 首")
    for x in fresh:
        print(f"  + [录音室] {x['title']}（{x['album']}）{x['mid'][:12]}")
    for x in live_hold:
        print(f"  - [Live·走现场层] {x['title']}（{x['album']}）{x['mid'][:12]}")
    for x in rejected:
        print(f"  x {x['title']}（命中排除词 {'/'.join(x['hits'])}）")
    if args.include_live:
        fresh = fresh + live_hold
        print("  （--include-live：Live 版一并并入待测）")
    if not fresh:
        print("录音室层无新发行，秒退（不下载不测量）")
        return 0
    if args.check:
        return 0

    doc = load(EXTRA, {}) or {"schema": 1, "items": []}
    items = doc.setdefault("items", [])
    added = 0
    for x in fresh:
        if any(str(i.get("mid")) == x["mid"] for i in items):
            continue
        items.append({"album": x["album"], "title": x["title"], "mid": x["mid"], "note": x["note"]})
        added += 1
    doc["note"] = doc.get("note") or "补充待测曲目（不在站点 data/albums.json 里的单曲/EP/现场版/翻唱等）"
    EXTRA.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] 待测清单 +{added} 条 → {EXTRA}")

    ok = run([PY, "-X", "utf8", str(ANA / "批量下载专辑.py"), "--extra"], "下载新曲音频（QQ音乐 320k）")
    if ok:
        run([PY, "-X", "utf8", str(ANA / "批量专辑音域.py")], "人声分离 + 逐帧 F0 实测")
        run([PY, "-X", "utf8", str(ANA / "生成专辑音域报告.py")], "生成专辑音域报告 + 站点数据")
    print("站点页面重建由 deploy_all 的既有步骤接管（refresh_vocal_pages + voice/skill）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
