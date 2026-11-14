#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从本地「含时间戳逐字稿」里，为每期金句定位真实时间码。

输入：E:\\wx\\私有\\王晰全文库\\小酒馆逐字稿\\深夜小酒馆_全部107期文案_含时间戳.txt（本地，私有不外传）
      tavern/tavern_summaries.json（站内已有的摘要与金句）
输出：tavern/quote_times.json  {期名: {金句: "mm:ss"}}

做法：把每期的 [mm:ss.cc] 行拼成带偏移的字符流，用金句做滑窗匹配，取匹配段起点时间。
合规：只输出「金句 + 时间码」，不导出任何逐字稿正文。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
SRC = Path(r"E:\wx\私有\王晰全文库\小酒馆逐字稿\深夜小酒馆_全部107期文案_含时间戳.txt")
SUMMARIES = ROOT / "tavern" / "tavern_summaries.json"
OUT = ROOT / "tavern" / "quote_times.json"

EP_RE = re.compile(r"^(\d{2,3})\u3000(.+)$")
PART_RE = re.compile(r"第(\d+)期\s*(\d+)")
TS_RE = re.compile(r"^\[(\d{2}):(\d{2})\.(\d{2})\](.*)$")


def parse():
    """→ {ep_title: [(秒, 文本), ...]}"""
    eps, cur, cur_title = {}, None, None
    for raw in SRC.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        m = EP_RE.match(line)
        if m:
            t = m.group(2).strip()
            pm = PART_RE.search(t)
            if pm:
                cur_title = "EP%02d_P%d" % (int(pm.group(1)), int(pm.group(2)))
            elif t.startswith("营业预告"):
                cur_title = "营业预告"
            else:
                cur_title = t.split("：")[0].strip()
            cur = eps.setdefault(cur_title, [])
            continue
        m = TS_RE.match(line)
        if m and cur is not None:
            sec = int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 100
            cur.append((sec, m.group(4)))
    return eps


def norm(s: str) -> str:
    return re.sub(r"[\s，。、！？；：“”‘’（）()·…—\-]", "", s or "")


def find_time(lines, quote):
    """在 [(sec,text)] 里找金句起点，返回 "mm:ss" 或 None。"""
    target = norm(quote)
    if not target:
        return None
    # 拼接字符流，记录每个字符的时间
    chars, times = [], []
    for sec, txt in lines:
        for ch in norm(txt):
            chars.append(ch)
            times.append(sec)
    stream = "".join(chars)
    pos = stream.find(target)
    if pos >= 0:
        sec = times[pos]
        return "%02d:%02d" % (sec // 60, int(sec) % 60)
    # 退化：取金句前 8 字匹配
    if len(target) >= 8:
        pos = stream.find(target[:8])
        if pos >= 0:
            sec = times[pos]
            return "%02d:%02d" % (sec // 60, int(sec) % 60)
    return None


def main():
    eps = parse()
    print("解析期数:", len(eps))
    d = json.loads(SUMMARIES.read_text(encoding="utf-8"))
    out, hit, miss = {}, 0, 0
    for key, v in (d.get("episodes") or {}).items():
        ep = v.get("episode", key)
        lines = eps.get(ep) or eps.get(key) or []
        quotes = v.get("quotes") or []
        if not lines or not quotes:
            continue
        m = {}
        for q in quotes:
            t = find_time(lines, q)
            if t:
                m[q] = t
                hit += 1
            else:
                miss += 1
        if m:
            out[ep] = m
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"命中 {hit} / 未命中 {miss}｜覆盖 {len(out)} 期 → {OUT}")
    # 抽样
    for k in list(out)[:2]:
        print(" ", k, list(out[k].items())[:2])


if __name__ == "__main__":
    main()
