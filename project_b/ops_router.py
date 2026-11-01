"""把自然语言意图映射到操作中心编号（读 docs/操作中心全图.md）

用法：
  python -X utf8 project_b/ops_router.py --ask "补一下昨天的指数"
  python -X utf8 project_b/ops_router.py --ask "把视频转成文字"
  python -X utf8 project_b/ops_router.py --list          # 打印全部意图
"""
import argparse
import json
import math
import os
import re

MAP = r"D:\wx409.github.io\docs\操作中心全图.md"

# 意图 → (关键词, 推荐编号列表, 说明)
INTENTS = [
    (["指数", "数据没进来", "补日", "缺日", "长表"], ["64", "45", "44", "225"],
     "指数入库链路：先补源→建矩阵→重建基线（225 看断言）"),
    (["大屏", "看板", "不更新", "卡住"], ["47", "48"], "重启 daemon → 结构三查"),
    (["微博", "抓微博", "采集"], ["1", "2"], "本人 / 工作室 微博抓取"),
    (["视频转文字", "转写", "转录", "转成文字"], ["248", "249"], "单条链接 248 / 批量 249"),
    (["一条链接", "全流程", "链接入库"], ["259"], "下载→转写→切分→切句→重建"),
    (["金句", "入池", "词句", "文本入池"], ["260"], "从文本文件入池（给路径+出处）"),
    (["谁在说", "说话人", "切分"], ["254"], "启发式说话人切分"),
    (["字幕", "硬字幕", "校对字幕"], ["255", "256"], "字幕 OCR 校正（贵）+ 说明书"),
    (["采访", "杂志", "巡检"], ["247"], "采访/杂志巡检 → 根表 + 待人工清单"),
    (["小酒馆", "播放", "不出声", "不能播"], ["258", "257"], "先查状态 258，没跑按 257"),
    (["审计", "检查一遍", "全绿"], ["242"], "六项审计一键"),
    (["推一下", "发布", "commit", "push"], ["39"], "git add/commit/push"),
    (["演出", "场次", "补录演出"], [str(n) for n in range(13, 26)], "B 组：演出反馈/评论/歌单"),
    (["音域", "重测", "F0"], [str(n) for n in range(51, 56)], "H 组：人声分离+F0+白皮书"),
    (["去重", "重复"], ["252"], "转写/语料去重"),
    (["模型", "turbo", "small"], ["251"], "看可用模型 + 转写索引"),
    (["早间", "没跑", "错过"], ["253"], "早间任务补跑检查"),
]


def load_menu():
    rows = {}
    if not os.path.exists(MAP):
        return rows
    for line in open(MAP, encoding="utf-8").read().splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|\s*([^|]+)\|\s*([^|]*)\|\s*([^|]*)\|", line)
        if m:
            rows[m.group(1)] = (m.group(2).strip(), m.group(3).strip(), m.group(4).strip())
    return rows


def score(q, keys):
    hits = sum(1 for k in keys if k in q)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ask", default="")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    menu = load_menu()

    if a.list:
        for keys, nums, why in INTENTS:
            print("%-22s → %s\t%s" % ("/".join(keys[:3]), ",".join(nums[:4]), why))
        return 0

    q = a.ask
    if not q:
        print("用法：--ask \"补一下昨天的指数\"")
        return 2

    ranked = sorted(((score(q, keys), why, nums) for keys, nums, why in INTENTS), key=lambda x: -x[0])
    best = [r for r in ranked if r[0] > 0]
    if not best:
        print("没听懂。可先 --list 看全部意图，或直接说「操作中心 编号」。")
        return 1

    print("你说的：%s\n" % q)
    for s, why, nums in best[:2]:
        print("建议：%s" % why)
        for n in nums[:4]:
            info = menu.get(n)
            if info:
                print("   %s. %s   [%s / %s]" % (n, info[0][:56], info[1], info[2]))
            else:
                print("   %s（未在菜单表中）" % n)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
