#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首页音域摘要块（从实测 JSON 派生，禁手写）

问题背景：首页那句「10 首歌曲……3 首达 B1」是 v1 口径的手写残留，
与 voice.html 的 v2 结论（10 曲中 1 首、全量 72 曲中 4 首）直接矛盾，
生成式引擎会同时抓到两个数。本脚本把这句话变成派生块，随数据自动更新。

单一事实源：
  · data/archive_vocal.json        → 10 曲精测表结论（主区 / B1 曲目）
  · data/archive_vocal_albums.json → 72 曲全量实测（最低音 / B1 曲目数）

用法：
  python -X utf8 project_b/inject_vocal_summary.py          # 生成 + 注入
  python -X utf8 project_b/inject_vocal_summary.py --check  # 只校验（exit 1 = 不一致）
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "index.html"
START = "<!-- VOCAL-SUMMARY:START（由 project_b/inject_vocal_summary.py 生成，勿手改）-->"
END = "<!-- VOCAL-SUMMARY:END -->"


def build_block() -> str:
    vocal = json.loads((ROOT / "data" / "archive_vocal.json").read_text(encoding="utf-8"))
    alb = json.loads((ROOT / "data" / "archive_vocal_albums.json").read_text(encoding="utf-8"))
    c = vocal["conclusion"]
    sm = alb["summary"]

    b1_songs = [s["name"] for s in vocal["songs"] if (s.get("lowest_note") or "").startswith("B1")]
    album_b1 = [s["title"] for s in alb["songs"] if str(s.get("low") or "").startswith("B1")]

    body = (
        f'<p>王晰是华语流行乐坛少见的<strong>真·男低音（Bass）</strong>，音域可达 '
        f'<strong>Low C</strong>（大字组 C，约 65.4 Hz）<strong>及以下</strong>——本站人声分离实测：'
        f'{vocal["count"]} 曲精测表中最低稳定音主区在 <strong>{c["main_range"]}</strong>，'
        f'其中 <strong>{c["b1_count"]} 首</strong>（{"、".join("《" + x + "》" for x in b1_songs)}）达 '
        f'<strong>B1（约 61Hz，低于 Low C）</strong>；全量 <strong>{sm["songs"]} 首录音室曲目</strong>实测中 '
        f'<strong>{len(album_b1)} 首</strong>达 B1（{"、".join("《" + x + "》" for x in album_b1)}），'
        f'最低 {sm["lowest"]["note"]}（{sm["lowest"]["hz"]}Hz，《{sm["lowest"]["song"]}》）。'
        f'两者统计对象不同，请勿混读。详见 <a href="voice.html">🎼 音域实测页</a>。</p>'
    )
    return f"{START}\n{body}\n{END}"


def main() -> int:
    check = "--check" in sys.argv
    block = build_block()
    text = TARGET.read_text(encoding="utf-8")

    if START in text and END in text:
        new_text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: block, text, count=1, flags=re.S)
    else:
        # 首次运行：把旧的「人声分离实测」段落整体换成标记块
        m = re.search(r'<p>[^<]*?(?:<strong>[^<]*</strong>[^<]*?)*?本站人声分离实测.*?</p>', text, re.S)
        if not m:
            print("[FAIL] index.html 找不到「人声分离实测」段落，需人工确认锚点")
            return 1
        new_text = text[:m.start()] + block + text[m.end():]

    if check:
        if new_text != text:
            print("[FAIL] index.html 音域摘要与实测数据不一致（重跑 inject_vocal_summary.py）")
            return 1
        print("[OK] index.html 音域摘要与实测数据一致")
        return 0

    TARGET.write_text(new_text, encoding="utf-8", newline="")
    print("[OK] 已注入 index.html 音域摘要块")
    print("  " + re.sub(r"<[^>]+>", "", block.split("\n")[1])[:150] + "…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
