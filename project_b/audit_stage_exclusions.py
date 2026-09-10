# -*- coding: utf-8 -*-
"""排除项回归审计：防止生成器把已排除素材/错误曲名/旧样本数"回吞"上线。

背景（2026-09-10）：`生成他人主导报告.py` 会重写 data/archive_stage.json，
手工清理会被覆盖（同类病第三次：build_nav 覆盖页面、指纹本地线上、生成器回吞）。
本审计把"生成器回吞"从发现型故障变成拦截型故障。

黑名单与红线（改动需同步 他人主导\\_excluded.json 台账）：
  · 已排除素材 bvid：BV1mT4y117g4（《她真漂亮》王晰and高杨）
  · 错误曲名「我的爱对你说」不得出现在 stage 数据/页面（王晰另有同名正当曲目，仅限舞台条目）
  · 样本数不得回 33（应为 32）且 analyzed 必须等于 items 数
退出码：1 = 拦下
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "data" / "archive_stage.json"
PAGE = ROOT / "stage.html"
LEDGER = Path(r"E:\wx\论文素材_王晰作传\音域分析\他人主导\_excluded.json")
SCAN = Path(r"E:\wx\论文素材_王晰作传\音域分析\他人主导\音频_分析")

BAD_BVIDS = {"BV1mT4y117g4"}
BAD_TEXT = ["我的爱对你说"]
EXPECT_ITEMS = 32


def main() -> int:
    problems = []
    if LEDGER.exists():
        try:
            _cfg = json.loads(LEDGER.read_text(encoding="utf-8"))
            for e in _cfg.get("excluded", []):
                if e.get("bvid"):
                    BAD_BVIDS.add(e["bvid"])
                if e.get("title_match"):
                    globals()['BAD_TEXT'].append(e["title_match"])
            globals()['EXPECT_ITEMS'] = int((_cfg.get("red_lines") or {}).get("expect_items", EXPECT_ITEMS))
            for _t in (_cfg.get("red_lines") or {}).get("forbidden_text", []):
                if _t not in globals()['BAD_TEXT']:
                    globals()['BAD_TEXT'].append(_t)
        except Exception as ex:
            problems.append(f"排除清单不可读：{ex}")
    else:
        problems.append("缺 排除清单.json（SSOT）")

    if not STAGE.exists():
        problems.append("缺 data/archive_stage.json")
    else:
        d = json.loads(STAGE.read_text(encoding="utf-8"))
        items = d.get("items") or []
        n = len(items)
        print(f"stage 条目 {n}｜source.analyzed {d.get('source', {}).get('analyzed')}")
        if n == 33 or d.get("source", {}).get("analyzed") == 33:
            problems.append(f"样本数回退到 33（应为 {EXPECT_ITEMS}）——生成器把排除项复活了")
        if d.get("source", {}).get("analyzed") not in (None, n):
            problems.append("source.analyzed 与 items 数不一致")
        for it in items:
            if it.get("bvid") in BAD_BVIDS:
                problems.append(f"已排除素材重新出现：{it.get('bvid')}")
            blob = json.dumps(it, ensure_ascii=False)
            for bad in BAD_TEXT:
                if bad in blob:
                    problems.append(f"错误曲名「{bad}」出现在 stage 数据：{it.get('bvid')}")

    if PAGE.exists():
        h = PAGE.read_text(encoding="utf-8", errors="replace")
        for bad in ("她真漂亮",) + tuple(BAD_TEXT):
            if bad in h:
                problems.append(f"页面出现黑名单文本：{bad}")

    # 结构性检查：被排除素材的分析产物必须不在扫描路径内
    for bv in BAD_BVIDS:
        hits = [p for p in SCAN.rglob(f"*{bv}*") if "_excluded" not in p.parts]
        if hits:
            problems.append(f"被排除素材的分析产物仍在扫描路径：{hits[0].name}")

    print("-" * 62)
    if problems:
        for p in problems:
            print("  ✕", p)
        print(f"结论：排除项回归 {len(problems)} 处 —— 修在生成器数据装配处，别再用后处理 ❌")
        return 1
    print("结论：排除项未被回吞 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
