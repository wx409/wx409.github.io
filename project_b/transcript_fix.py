# -*- coding: utf-8 -*-
"""转写专有名词纠错词典（ASR 热词校正层）

用法：
  from transcript_fix import apply_fixes, count_fixes
  text2 = apply_fixes(text)

维护说明：
- FIXES 每项 = (正确词, [ASR 错误变体...])；apply_fixes 将错误变体全部替换为正确词。
- 只收录**高置信度**专有名词/数字纠错；口语乱词（无确定正确形式）不收录。
- 新增错词：把 (正确词, [错词]) 追加到 FIXES 即可。
"""
import re

FIXES = [
    ("王洛宾", ["王露斌", "王露宾", "王璐宾"]),
    ("田歌", ["田哥"]),
    ("琼库什台", ["穷库石台"]),
    ("星海音乐学院", ["县海军院", "星海音乐学员"]),
    ("草原之夜", ["草莹之夜", "草原之业", "草茵之夜"]),
    ("像雾像雨又像风", ["香不香又香风", "像雾像雨又像雨"]),
    ("月半弯", ["月板板", "月半板"]),
    ("卡朋特", ["卡彭特", "卡朋特乐队"]),
    ("张信哲", ["张旭有", "张旭友"]),          # 待核：玉置浩二歌曲的华语翻唱者
    ("哈萨克族", ["哈萨特族", "哈沙克族"]),
    ("发烧友", ["发商友", "发骚友"]),
    ("2018", ["1918"]),                        # 语境：2018 歌手节目
    ("夜色", ["叶子"]),                        # 语境：邓丽君的一首温暖的歌
    ("王晰", ["往昔"]),                        # 语境：2018 年通过这首歌认识王晰
]

# 编译：错误变体 → 正确词（按变体长度降序替换，避免子串误伤）
_PAIRS = sorted(((w, c) for c, ws in FIXES for w in ws), key=lambda x: -len(x[0]))


def apply_fixes(text):
    """把文本中所有已知 ASR 错词替换为正确词，返回修正后的文本。"""
    if not text:
        return text
    for wrong, correct in _PAIRS:
        if wrong in text:
            text = text.replace(wrong, correct)
    return text


def count_fixes(text, fixed):
    """返回 (替换总数, [(错词→正确词, 次数)...])，用于统计/审计。"""
    pairs = []
    total = 0
    for wrong, correct in _PAIRS:
        n = text.count(wrong)
        if n:
            pairs.append((f"{wrong}→{correct}", n))
            total += n
    return total, pairs


if __name__ == "__main__":
    import io, sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    # 自测
    t = "王露斌先生、穷库石台、县海军院、草莹之夜、香不香又香风、月板板、卡彭特、哈萨特族、发商友、1918年、田哥先生、叶子、认识往昔的今天"
    n, pairs = count_fixes(t, None)
    fixed = apply_fixes(t)
    print(f"测试替换 {n} 处：")
    for p in pairs:
        print("  ", p)
    print("修正后:", fixed)
