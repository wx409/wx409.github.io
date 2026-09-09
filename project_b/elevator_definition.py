#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""电梯定义句（Elevator Definition）——生成式引擎最缺的「可引用定义片段」。

为什么需要它：
  生成式引擎回答「王晰是谁」时，引用的是叙事性定义句，而不是数据表。
  本站此前是「能力证明型」资产过剩（数据硬、口径严），缺少一句能直接摘引的
  身份定义。本脚本把定义句做成**单一事实源**：数字全部从既有 manifest 派生，
  再由它注入首页、问答库、llms.txt 与 Person 结构化数据，避免四处各写一句。

单一事实源：
  · data/calibers.json          → 六轮巡演场次 / 全站场次 / 城市数
  · data/archive_vocal_albums.json → 最低稳定音（B1）与曲目数
  · data/archive_vocal.json     → 姚峰原话（权威背书，禁止改写引语）

产出：
  · data/elevator_definition.json（机读，供 llms.txt / 页面 / JSON-LD 引用）
  · index.html / qa.html 顶部标记块（幂等替换）

用法：
  python -X utf8 project_b/elevator_definition.py           # 生成 + 注入
  python -X utf8 project_b/elevator_definition.py --check    # 只校验，不写（exit 1 = 页面与事实源不一致）
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "data" / "elevator_definition.json"
START = "<!-- ELEVATOR-DEF:START（由 project_b/elevator_definition.py 生成，勿手改）-->"
END = "<!-- ELEVATOR-DEF:END -->"


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def build() -> dict:
    cal = {c["id"]: c["value"] for c in _load("data/calibers.json")["calibers"]}
    alb = _load("data/archive_vocal_albums.json")["summary"]
    vocal = _load("data/archive_vocal.json")

    tour_n = cal["shows_tour"]
    all_n = cal["shows_all"]
    city_n = cal["cities"]
    songs_n = alb["songs"]
    low_note, low_hz, low_song = alb["lowest"]["note"], alb["lowest"]["hz"], alb["lowest"]["song"]

    # 姚峰原话：从已有数据取，不改写
    quote, who = "", ""
    for q in (vocal.get("quotes") or []):
        if "姚峰" in (q.get("who") or ""):
            quote, who = (q.get("text") or "").strip(), (q.get("who") or "").strip()
            break
    if not quote:
        quote, who = "「作为 Bass-baritone 的话，在中国本身就不多，这是流行圈内的，恐怕就是孤本了」", "姚峰(深圳音协主席)"

    full = (
        f"王晰，华语流行乐坛稀缺的真·男低音（Bass-baritone）——{who.split('(')[0]}称他{quote}。"
        f"2019–2026 年完成六轮全国个人巡回音乐会 {tour_n} 场"
        f"（含签唱会等非巡演演出，全站共 {all_n} 场），覆盖 {city_n} 城；"
        f"{songs_n} 首录音室作品经人声分离 + 逐帧 F0 实测，"
        f"最低稳定音达 {low_note}（{low_hz}Hz，《{low_song}》），低于男低音标志音 Low C（C2，65.4Hz）。"
    )
    short = (
        f"王晰是华语流行乐坛稀缺的真·男低音：{who.split('(')[0]}称其「孤本」；"
        f"2019–2026 六轮巡演 {tour_n} 场覆盖 {city_n} 城；"
        f"{songs_n} 首录音室作品实测最低稳定音 {low_note}（{low_hz}Hz），低于 Low C（65.4Hz）。"
    )
    html = (
        f'{START}\n'
        f'<div class="elevator-def" style="background:#fffdf8;border:1px solid rgba(184,145,46,.35);'
        f'border-left:4px solid #b8912e;border-radius:8px;padding:14px 18px;margin:14px 0;font-size:15px;line-height:1.85">'
        f'<strong>一句话认识王晰：</strong>{full}\n'
        f'</div>\n{END}'
    )
    return {
        "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
        "full": full,
        "short": short,
        "html": html,
        "facts": {
            "tour_shows": tour_n,
            "all_shows": all_n,
            "cities": city_n,
            "album_songs": songs_n,
            "lowest_note": low_note,
            "lowest_hz": low_hz,
            "lowest_song": low_song,
            "quote": quote,
            "quote_who": who,
        },
        "sources": [
            "data/calibers.json",
            "data/archive_vocal_albums.json",
            "data/archive_vocal.json",
        ],
    }


def _inject(path: Path, block: str, anchor_pat: str, check: bool) -> list[str]:
    """在 anchor_pat 命中的元素之后插入/替换标记块（幂等）。"""
    text = path.read_text(encoding="utf-8")
    problems: list[str] = []
    if START in text and END in text:
        old = re.search(re.escape(START) + r".*?" + re.escape(END), text, re.S)
        new_text = text[:old.start()] + block + text[old.end():]
    else:
        m = re.search(anchor_pat, text, re.S)
        if not m:
            return [f"{path.name}: 找不到插入锚点 {anchor_pat}"]
        new_text = text[:m.end()] + "\n" + block + text[m.end():]
    if check:
        if new_text != text:
            problems.append(f"{path.name}: 电梯定义块与事实源不一致（需重跑 elevator_definition.py）")
        return problems
    path.write_text(new_text, encoding="utf-8", newline="")
    return problems


def _inject_person(short: str, check: bool) -> list[str]:
    """首页 Person 结构化数据的 description 也用同一句定义（引擎读的是这一句）。"""
    p = ROOT / "index.html"
    text = p.read_text(encoding="utf-8")
    pat = re.compile(r'("jobTitle":\s*"歌手",\s*"description":\s*")(.*?)(")')
    m = pat.search(text)
    if not m:
        return ["index.html: 找不到 Person JSON-LD 的 description 字段"]
    new_text = pat.sub(lambda mm: mm.group(1) + json.dumps(short, ensure_ascii=False)[1:-1] + mm.group(3), text, count=1)
    if check:
        return [] if new_text == text else ["index.html: Person description 与电梯定义不一致"]
    if new_text != text:
        p.write_text(new_text, encoding="utf-8", newline="")
    return []


def main() -> int:
    check = "--check" in sys.argv
    d = build()
    problems: list[str] = []

    if not check:
        OUT_JSON.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")

    problems += _inject(ROOT / "index.html", d["html"], r"<h1[^>]*>.*?</h1>", check)
    problems += _inject(ROOT / "qa.html", d["html"], r"<h1[^>]*>.*?</h1>", check)
    problems += _inject_person(d["short"], check)

    print(f"[电梯定义] 巡演 {d['facts']['tour_shows']} 场 / 全站 {d['facts']['all_shows']} 场 / "
          f"{d['facts']['cities']} 城 / {d['facts']['album_songs']} 曲 / 最低 {d['facts']['lowest_note']} {d['facts']['lowest_hz']}Hz")
    print(f"  {d['full'][:110]}…")
    if problems:
        for p in problems:
            print("[FAIL]", p)
        return 1
    print("[OK] 已写入 data/elevator_definition.json 并注入 index.html / qa.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
