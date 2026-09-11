# -*- coding: utf-8 -*-
"""结构化数据审计（JSON-LD 语法 + GEO 必备类型 + 纪律用词红线）

检查项：
  1. 全站每个 <script type="application/ld+json"> 都能被 json 解析（语法错误=引擎直接丢弃）；
  2. voice.html / stage.html 必须同时具备 ResearchProject（含 isBasedOn 版本谱系）与 FAQPage；
  3. FAQ 答案不得为空，且不得出现已作废/违规措辞（声学指纹、生物指纹、机械级音准、华语最低、唯一、第一）；
  4. Dataset/ResearchProject 的 description 中若出现 C5 以上高音，必须同时出现「伴唱」或「和声」风险提示。

用法：python -X utf8 project_b/audit_jsonld.py     （有问题 exit 1）
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOCK = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
# 只拦「对王晰的排名/唯一性断言」，不拦引语与客观事实里的"唯一"（如"六首曲目中唯一的合作曲"）
BANNED = ["声学指纹", "生物指纹", "机械级音准", "华语最低", "华语第一", "国内唯一", "唯一一位", "排名第一", "第一人", "世界最低",
          # 过程稿措辞：读者只关心结论与现行方法，旧口径叙述只会引起误解（2026-09-09 决策）
          "旧口径", "v1 口径", "v1 曾", "v1 报告", "口径升级", "口径变更", "结论修正", "瞬时最低", "已作废", "NoneHz"]
REQUIRED = {
    "voice.html": ("ResearchProject", "FAQPage"),
    "stage.html": ("ResearchProject", "FAQPage"),
}


def walk_types(obj, out: list[dict]) -> None:
    if isinstance(obj, dict):
        if "@type" in obj:
            out.append(obj)
        for v in obj.values():
            walk_types(v, out)
    elif isinstance(obj, list):
        for v in obj:
            walk_types(v, out)


def main() -> int:
    problems: list[str] = []
    stats: dict[str, list[str]] = {}

    for html in sorted(ROOT.glob("*.html")):
        text = io.open(html, encoding="utf-8").read()
        blocks = BLOCK.findall(text)
        types: list[str] = []
        for i, b in enumerate(blocks):
            try:
                data = json.loads(b)
            except Exception as e:
                problems.append(f"{html.name} JSON-LD 第 {i + 1} 块语法错误: {str(e)[:80]}")
                continue
            nodes: list[dict] = []
            walk_types(data, nodes)
            for node in nodes:
                t = node.get("@type")
                if isinstance(t, list):
                    types.extend(t)
                elif t:
                    types.append(t)
                # 高音风险提示（Question 的 name 是提问本身，不参与判定）
                keys = ("description", "caption", "text") if node.get("@type") == "Question" else ("description", "caption", "text", "name")
                desc = " ".join(str(node.get(k) or "") for k in keys)
                if re.search(r"\bC[5-7]\b|C6|C5", desc) and ("伴唱" not in desc and "和声" not in desc and "需听辨" not in desc):
                    problems.append(f"{html.name} 结构化数据提到 C5+ 但未标注伴唱/和声风险：{desc[:60]}")
        stats[html.name] = sorted(set(types))

        for banned in BANNED:
            if banned in text:
                problems.append(f"{html.name} 出现违规/作废措辞「{banned}」")

        need = REQUIRED.get(html.name)
        if need:
            for t in need:
                if t not in types:
                    problems.append(f"{html.name} 缺少 {t} 结构化数据")

    # FAQ 质量
    for name in ("voice.html", "stage.html"):
        p = ROOT / name
        if not p.exists():
            continue
        for b in BLOCK.findall(io.open(p, encoding="utf-8").read()):
            try:
                data = json.loads(b)
            except Exception:
                continue
            if data.get("@type") == "FAQPage":
                items = data.get("mainEntity") or []
                if len(items) < 3:
                    problems.append(f"{name} FAQPage 问答对过少（{len(items)} < 3）")
                for q in items:
                    a = ((q.get("acceptedAnswer") or {}).get("text") or "").strip()
                    if len(a) < 20:
                        problems.append(f"{name} FAQ 答案过短：{q.get('name')}")

    print("[JSON-LD 审计] 各页类型：")
    for name, types in stats.items():
        print(f"  {name}: {', '.join(types) if types else '（无）'}")

    if problems:
        print(f"\n[FAIL] {len(problems)} 项问题：")
        for x in problems:
            print("  -", x)
        return 1
    print("\n[OK] 结构化数据审计通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
