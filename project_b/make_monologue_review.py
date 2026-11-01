"""生成「小酒馆独白 · 待标记」清单（每条后面留一个「答：」空位）

用法：python -X utf8 project_b/make_monologue_review.py [--limit 120]
填空规则（你只写答案，不删原文）：
  答：好      → 升为 high（进骰池）
  答：删      → 从词句库删除
  答：改 XXX  → 用 XXX 替换原文（精度问题就改）
  留空        → 保持 mid，不动
"""
import argparse
import json

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
OUT = r"D:\wx409.github.io\docs\小酒馆独白_待标记.md"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=150)
    a = ap.parse_args()

    bank = json.load(open(BANK, encoding="utf-8"))
    pool = [i for i in bank["items"]
            if i["type"] == "talk" and "深夜小酒馆" in (i.get("source") or "")
            and i.get("quality") == "mid"]

    # 先按「观点词密度 + 长度」排序，先看最像金句的
    POS = ["其实", "不要", "一定要", "记住", "所以", "但是", "我们", "人生", "生活",
           "时间", "父母", "爱", "希望", "选择", "理解", "坚持"]
    pool.sort(key=lambda x: (-sum(1 for k in POS if k in x["text"]), -len(x["text"])))
    picked = pool[:a.limit]

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("# 小酒馆独白 · 待标记（%d 条 / 共 %d 条）\n\n" % (len(picked), len(pool)))
        f.write("每条下面写 `答：好` / `答：删` / `答：改 正确文本`；不写=保持不动。\n\n")
        f.write("---\n\n")
        for it in picked:
            f.write("**%s**  \n<sub>%s</sub>  \n答：\n\n" % (it["text"], it["source"]))

    print("已生成:", OUT)
    print("清单 %d 条（库内独白共 %d 条，均为 mid）" % (len(picked), len(pool)))
    print("\n示例如下：")
    for it in picked[:5]:
        print("  •", it["text"][:56])


if __name__ == "__main__":
    main()
