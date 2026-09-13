# -*- coding: utf-8 -*-
"""声学三页整合 · 旧页加归档提示 + 三级读数制度文本块（瘦身 2.0 · 第六阶段 + 6.3）

方案 A（旧页不删内容）：旧页冻结为完整快照，**只加提示链接，不删任何表格**。
因此 archive-index.html 承诺的「完整快照」成立：
  · 6.2 重复数据块 → 在各处旁加「此表最新版本见 vocal.html / live.html」提示；
  · 6.3 三级读数制度文本块 → 逐页复制粘贴到 voice/stage/skill/vocal 四页（本仓库禁用 Jekyll，不用 include）。

幂等：所有插入块用 HTML 注释标记包裹，重复运行结果一致。

用法：
  python -X utf8 project_b/build_legacy_notes.py            # 写入
  python -X utf8 project_b/build_legacy_notes.py --check     # 只检查
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TIER_START = "<!-- TIER-CALIBER:START（三级读数制度统一文本块，勿手改）-->"
TIER_END = "<!-- TIER-CALIBER:END -->"

TIER_BLOCK = TIER_START + """
<div style="max-width:1000px;margin:14px auto 0;padding:12px 16px;background:#fff8f0;border:1px solid #eddcc0;border-radius:8px;font-size:14px;line-height:1.9">
<strong>三级读数制度（本站声学数据统一口径，全站一致）</strong>
<ul style="margin:6px 0 0;padding-left:22px">
<li><strong>稳定音（能力口径）</strong>：过复核门槛的最低音，可作能力结论，可进标题和对外引用句。</li>
<li><strong>触达音</strong>：实际到过的最低 F0，但未满足持续时长/复核门槛——展示但<strong>不作能力依据</strong>，不进汇总计数、不进标题。</li>
<li><strong>低音带读数</strong>：归属未完全确认（人声/乐器/念诵），标<strong>仅供参考</strong>，三不许：不进汇总、不进统计、不进对外引用句。</li>
</ul>
</div>
""" + TIER_END

# 归档提示（6.2）：(页面, 锚点文本, 提示文字, 标记名)
NOTES = [
    ("voice.html", "六、录音室 vs 现场", "现场 vs 录音室对照的最新版本见 live.html",
     "NOTE-SVL-LIVE"),
    ("voice.html", "五、情境对比", "与他人对照（同管线同口径）的最新版本见 vocal.html",
     "NOTE-CMP-VOCAL"),
    ("skill.html", "五、跨素材精测与取证状态",
     "跨素材精测与取证状态表的最新版本见 vocal.html", "NOTE-STRICT-VOCAL"),
    ("stage.html", "同曲对照 A", "现场↔录音室同曲对照的最新版本见 live.html", "NOTE-SVL-LIVE-STAGE"),
]


def note_html(text, tag):
    return (f'<!-- {tag}:START（归档提示，勿手改）-->\n'
            f'<div style="max-width:1000px;margin:8px auto;padding:8px 14px;background:#faf6ee;'
            f'border-left:3px solid #b8912e;border-radius:6px;font-size:13px;color:#6b5b3a">'
            f'📌 <strong>内容已归档</strong>：{text}。<em>本页表格一律保留为完整快照，不删内容。</em></div>\n'
            f'<!-- {tag}:END -->')


def insert_after_heading(txt, heading_key, block, marker):
    """在首个包含 heading_key 的 h2/h3 所在行之后插入 block（幂等）。"""
    if f"{marker}:START" in txt:
        return txt, False
    m = re.search(r'[ \t]*<h[23][^>]*>[^<]*' + re.escape(heading_key) + r'[^<]*</h[23]>', txt)
    if not m:
        return txt, None                    # None = 锚点未找到（需报告）
    # 插到该标题所在行末尾之后
    line_end = txt.find("\n", m.end())
    if line_end < 0:
        line_end = m.end()
    return txt[:line_end] + "\n" + block + txt[line_end:], True


def insert_tier_block(txt, marker_tag):
    if TIER_START in txt:
        return txt, False
    # 插到第一个数据表之前；无表格则插到 body 之后
    m = re.search(r'[ \t]*<table', txt)
    if m:
        line_start = txt.rfind("\n", 0, m.start()) + 1
        return txt[:line_start] + TIER_BLOCK + "\n" + txt[line_start:], True
    b = re.search(r"<body[^>]*>", txt, re.I)
    if not b:
        return txt, None
    return txt[:b.end()] + "\n" + TIER_BLOCK + txt[b.end():], True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    print("=" * 70)
    print("旧页归档提示 + 三级读数制度文本块（第六阶段 / 6.3）")
    print("=" * 70)

    files = {}
    for page in ("voice.html", "stage.html", "skill.html", "vocal.html"):
        p = os.path.join(ROOT, page)
        if not os.path.exists(p):
            print("  [skip] %s 不存在" % page)
            continue
        files[page] = io.open(p, encoding="utf-8", errors="ignore").read()

    plan = []          # (page, new_text, kind, ok)
    # 1) 归档提示
    for page, anchor, text, tag in NOTES:
        if page not in files:
            continue
        new, ch = insert_after_heading(files[page], anchor, note_html(text, tag), tag)
        if ch is None:
            print("  [!] %s 未找到锚点「%s」" % (page, anchor))
            continue
        plan.append((page, new, "提示(%s)" % tag, ch))
        if ch:
            files[page] = new
    # 2) 三级口径块
    for page in ("voice.html", "stage.html", "skill.html", "vocal.html"):
        if page not in files:
            continue
        new, ch = insert_tier_block(files[page], "TIER")
        if ch is None:
            print("  [!] %s 未找到插入点" % page)
            continue
        plan.append((page, new, "三级口径块", ch))
        if ch:
            files[page] = new

    seen = {}
    for page, new, kind, ch in plan:
        seen.setdefault(page, True)
        print("  %-14s %-16s %s" % (page, kind, "已插入" if ch else "已存在 ✅"))

    changed = [p for p in seen if files[p] != io.open(os.path.join(ROOT, p), encoding="utf-8").read()]
    if not changed:
        print("\n[OK] 全部已一致")
        return 0
    if args.check:
        print("\n[FAIL] 需更新：%s" % ", ".join(changed))
        return 1
    for p in changed:
        io.open(os.path.join(ROOT, p), "w", encoding="utf-8").write(files[p])
    print("\n[OK] 已更新：%s" % ", ".join(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
