# -*- coding: utf-8 -*-
"""专辑层复核状态：把 A3 终裁（含低音层/QA 抽样）转成站点可用的 per-song / per-album 状态。

读：`E:\\wx\\论文素材_王晰作传\\音域分析\\轨迹\\A3复核交付表.json`
    `D:\\wx409.github.io\\data\\archive_vocal_albums.json`（72 曲专辑层汇总）
写：`D:\\wx409.github.io\\data\\album_verify_status.json`

口径：⚪ 待复核的读数**展示但三不许**（不进汇总计数／不进跨版统计／不进对外引用句）。
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
A3 = Path(r"E:\wx\论文素材_王晰作传\音域分析\轨迹\A3复核交付表.json")
ALB = ROOT / "data" / "archive_vocal_albums.json"
OUT = ROOT / "data" / "album_verify_status.json"


def norm_status(final: str) -> str:
    f = final or ""
    if "✅" in f:
        return "✅ 双引擎一致"
    if "🟡" in f:
        return "🟡 已取证"
    if "✕" in f:
        return "✕ 次谐波错误"
    return "⚪ 待复核"


def main() -> int:
    a3 = json.loads(A3.read_text(encoding="utf-8")) if A3.exists() else {"rows": []}
    song_status: dict[str, str] = {}
    how: dict[str, str] = {}
    for r in a3.get("rows", []):
        if r.get("kind") != "稳定音":
            continue
        name = str(r.get("file", "")).split("（")[0].strip()
        if not name:
            continue
        # 同一曲多次出现时取更好的状态（✅ > 🟡 > ⚪ > ✕）
        rank = {"✅": 3, "🟡": 2, "⚪": 1, "✕": 0}
        cur = song_status.get(name)
        new = norm_status(r.get("final", ""))
        if not cur or rank[new[0]] > rank[cur[0]]:
            song_status[name] = new
            how[name] = (r.get("how") or "")[:80]

    alb = json.loads(ALB.read_text(encoding="utf-8")) if ALB.exists() else {"albums": [], "songs": []}
    by_title = {s["title"]: s for s in alb.get("songs", [])}
    albums = []
    for a in alb.get("albums", []):
        low_song = a.get("low_song") or ""
        albums.append({
            "album": a.get("album"), "n": a.get("n"),
            "low": a.get("low"), "low_song": low_song,
            "status": song_status.get(low_song, "未复核"),
            "how": how.get(low_song, ""),
        })
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": "专辑层复核状态（A3 终裁派生）。⚪ 待复核：展示但三不许（不进汇总计数/跨版统计/对外引用句）。",
        "songs": [{"title": t, "status": song_status.get(t, "未复核"), "how": how.get(t, "")}
                  for t in sorted(by_title)],
        "albums": albums,
        "counts": {
            "songs_total": len(by_title),
            "verified": sum(1 for t in by_title if song_status.get(t, "").startswith(("✅", "🟡"))),
            "pending": sum(1 for t in by_title if not song_status.get(t, "").startswith(("✅", "🟡"))),
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    c = payload["counts"]
    print(f"[OK] {OUT.name}｜72 曲中已复核 {c['verified']}、待复核/未复核 {c['pending']}"
          f"（本轮 A3 覆盖 {len(song_status)} 曲）")
    for a in albums[:10]:
        print(f"   {a['album']:14s} 最低 {a['low']:>4s} 《{a['low_song']}》 → {a['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
