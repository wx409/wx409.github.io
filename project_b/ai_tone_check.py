#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 腔体检：中文社媒文案的规则化自查（本地、离线、零依赖）。

来源与定位：
  规则思路参考开源项目 lieflat-less-ai-tone（正则 + 大语料统计，特征如「翻案腔」「顿号罗列」）。
  但那套语料是论文/长文，本脚本只保留可迁移到社媒的几条，并全部本地实现，不联网、不改写。

它只做一件事：**告诉你哪几句像机器写的**。改写仍然要人来。
用法：
  python -X utf8 project_b/ai_tone_check.py "D:\\path\\文案.md"
  python -X utf8 project_b/ai_tone_check.py --text "要检查的一段话"
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# (规则名, 正则, 权重, 建议)
RULES = [
    ("翻案腔", r"(?:不是|并非|不在于)[^，。！？\n]{1,20}[，]?(?:而是|而在于)", 3,
     "「不是…而是…」是 AI 最爱的句式，一段最多一次，多了就换说法"),
    ("顿号罗列过密", r"[^，。！？；：、\n]{1,14}、[^，。！？；：、\n]{1,14}、[^，。！？；：、\n]{1,14}", 2,
     "三项以上顿号并列，读起来像清单；改成短句"),
    ("总结腔", r"(?:综上|由此可见|值得注意的是|换句话说|总而言之|一言以蔽之|不难看出)", 3,
     "直接删掉，或改成「所以说」「那」"),
    ("翻译腔", r"(?:的的|进行了[^，。]{0,6}|对于[^，。]{0,10}而言|在一定程度上|起到了[^，。]{0,6}作用)", 2,
     "中文不这么说话，换成动词"),
    ("空话词", r"(?:赋能|抓手|闭环|生态位|维度上|层面上|范式|颗粒度|底层逻辑)", 3,
     "这些词在社媒里等于没说"),
    ("首先其次", r"首先[^。]{0,40}其次[^。]{0,40}(?:最后|再者)", 3,
     "三段式列举是汇报腔，改成讲故事顺序"),
    ("形容词堆砌", r"(?:极其|非常|十分|格外|尤为)[^，。]{0,6}(?:极其|非常|十分|格外|尤为)", 2,
     "一个形容词就够了"),
    ("排比收尾", r"(?:，)([^，。]{4,12})，\1", 2, "重复结构像模板"),
]

# 密度类（按每千字计）
DENSITY = [
    ("破折号", r"——", 3.0, "每千字超过 3 个就有点用力"),
    ("感叹号", r"[！!]", 2.0, "情感靠内容，不靠标点"),
    ("分数式对比", r"从[^，。]{0,8}到[^，。]{0,8}，", 2.0, "「从A到B」连用会显套路"),
]


def check(text: str) -> dict:
    n = max(len(text), 1)
    hits = []
    score = 0.0
    for name, pat, w, advice in RULES:
        ms = re.findall(pat, text)
        if ms:
            score += w * len(ms)
            hits.append({"rule": name, "count": len(ms),
                         "samples": [m if isinstance(m, str) else m[0] for m in ms[:3]],
                         "advice": advice})
    for name, pat, per_k, advice in DENSITY:
        c = len(re.findall(pat, text))
        dens = c / n * 1000
        if dens > per_k:
            score += (dens - per_k)
            hits.append({"rule": name, "count": c, "density_per_k": round(dens, 1), "advice": advice})
    per_k = round(score / n * 1000, 2)
    level = "干净" if per_k < 3 else ("轻微 AI 味" if per_k < 8 else "明显 AI 味")
    return {"chars": n, "score": round(score, 1), "per_1000": per_k, "level": level, "hits": hits}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--text", default="")
    a = ap.parse_args()

    if a.text:
        text = a.text
    elif a.path:
        p = Path(a.path)
        text = p.read_text(encoding="utf-8")
        # 去掉代码块与标题标记，只看正文
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        text = re.sub(r"^#+\s*", "", text, flags=re.M)
        text = re.sub(r"^\|.*\|$", "", text, flags=re.M)
    else:
        print("用法: ai_tone_check.py <文件> | --text \"...\"")
        sys.exit(1)

    r = check(text)
    print(f"字数 {r['chars']}｜得分 {r['score']}｜每千字 {r['per_1000']}｜{r['level']}")
    if not r["hits"]:
        print("✅ 没命中规则")
        return
    for h in r["hits"]:
        extra = f"×{h['count']}" if "count" in h else ""
        print(f"  [{h['rule']}] {extra}  {h['advice']}")
        for s in h.get("samples", []):
            print(f"      ↳ {s}")


if __name__ == "__main__":
    main()
