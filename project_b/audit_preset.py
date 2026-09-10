# -*- coding: utf-8 -*-
"""audit_preset.py —— 审计「维护者预设」与站点实际口径是否一致

为什么需要它
------------
`D:\\DSH\\.dsh\\.agent-presets\\wx409-maintainer\\agent.cordis.yml` 是**每次对话都会加载的操作说明书**，
但它不在任何审计的覆盖范围内 —— 2026-09-10 就发现它还写着：
  · 指数年度值 1013/880/862/686（映射修正后应为 1011.5/881.1/861.5/685.6）
  · 口径登记表「22 项」（实际 21 项）
本脚本把这类"说明书漂移"变成可自动发现的问题。

检查项：
  A 预设文件存在可读 / YAML 可解析（容错 !js 标签）
  B 年度值与 data/archive_baseline.json 一致
  C 口径项数与 data/calibers.json 一致
  D 事故后新增的自动化是否在预设里登记（看门狗/每日刷新/立刻补跑/验收总检/补录口径）

用法：
    python project_b\\audit_preset.py                      # 自动查找预设
    python project_b\\audit_preset.py --preset <路径>
退出码：0 = 一致（未找到预设记 SKIP）；1 = 有漂移。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = [
    Path(r"D:\DSH\.dsh\.agent-presets\wx409-maintainer\agent.cordis.yml"),
    Path(r"C:\Users\yezhe\.dsh\.agent-presets\wx409-maintainer\agent.cordis.yml"),
    ROOT / "dsh-config-portable" / ".dsh" / ".agent-presets" / "wx409-maintainer" / "SKILL.md",
]
SITE_BASELINE = ROOT / "data" / "archive_baseline.json"
CALIBERS = ROOT / "data" / "calibers.json"

OK, WARN, FAIL = "OK", "WARN", "FAIL"
problems: list[str] = []


def say(status: str, name: str, evidence: str = "") -> None:
    print("  %s %s%s" % ({OK: "✅", WARN: "⚠️", FAIL: "❌"}[status], name,
                         (" — " + evidence) if evidence else ""))
    if status == FAIL:
        problems.append(name)


def find_preset(explicit: str | None) -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    for p in CANDIDATES:
        if p.exists():
            return p
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    print("=" * 68)
    print("维护者预设 与 站点实际口径 一致性审计")
    print("=" * 68)
    p = find_preset(args.preset)
    if p is None:
        say(WARN, "预设文件未找到（跳过）", "候选：%s" % "；".join(str(x) for x in CANDIDATES[:2]))
        return 0
    say(OK, "预设文件存在", str(p))

    text = p.read_text(encoding="utf-8", errors="ignore")
    try:
        import yaml

        class L(yaml.SafeLoader):
            pass

        L.add_multi_constructor("tag:yaml.org,2002:js", lambda l, s, n: None)
        L.add_multi_constructor("!js", lambda l, s, n: None)
        d = yaml.load(text, Loader=L)
        say(OK, "YAML 可解析", ("list %d 项" % len(d)) if isinstance(d, list) else type(d).__name__)
    except Exception as e:
        say(FAIL, "YAML 可解析", str(e)[:120])

    # B) 年度值
    try:
        site = json.loads(SITE_BASELINE.read_text(encoding="utf-8"))
        ann = {a["year"]: a["mean"] for a in site.get("annual", [])}
    except Exception as e:
        say(FAIL, "站点基线可读", str(e)[:120])
        ann = {}
    for y, v in ann.items():
        # 预设里写法形如 "2023=1011.5"
        if re.search(r"%s\s*=\s*%s\b" % (y, re.escape(str(v))), text):
            continue
        m = re.search(r"%s\s*=\s*([0-9.]+)" % y, text)
        say(FAIL, "年度值 %s 与基线一致" % y,
            "预设写 %s，基线为 %s" % (m.group(1) if m else "未写", v))
    if ann and all(re.search(r"%s\s*=\s*%s\b" % (y, re.escape(str(v))), text) for y, v in ann.items()):
        say(OK, "年度值与基线全部一致", " · ".join("%s=%s" % kv for kv in ann.items()))

    # C) 口径项数
    try:
        cal = json.loads(CALIBERS.read_text(encoding="utf-8"))
        n = cal.get("count") or len(cal.get("calibers", []))
        found = re.findall(r"\*\*(\d+) 项\*\*", text)
        if not found:
            say(WARN, "预设未声明口径项数", "（登记表 %d 项）" % n)
        for f in set(found):
            say(OK if int(f) == n else FAIL, "口径项数声明一致",
                "预设 %s 项 vs 登记表 %d 项" % (f, n))
    except Exception as e:
        say(FAIL, "口径登记表可读", str(e)[:120])

    # D) 事故后自动化是否登记
    need = {"看门狗": "watchdog_batches", "每日刷新": "refresh_index_baseline",
            "立刻补跑": "run_batch_now", "验收总检": "acceptance_check",
            "补录口径": "抓取日 D+1"}
    missing = [k for k, kw in need.items() if kw not in text]
    say(OK if not missing else FAIL, "事故后自动化已在预设登记",
        "缺：" + "、".join(missing) if missing else "看门狗/每日刷新/立刻补跑/验收总检/补录口径 均在")

    print("-" * 68)
    if problems:
        print("结论：发现 %d 处漂移 —— 预设是每次对话的说明书，必须修正 ❌" % len(problems))
        for x in problems:
            print("   -", x)
        return 1
    print("结论：预设与站点实际口径一致 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
