"""整理《深夜小酒馆》节目独白 → 可引用的「他说过的话」

原则（准确优先）：
  · 只从单人口播稿里取，绝不拼接两段不同的话
  · 以「提问 → 回答」为天然边界切块，避免断在半句
  · 名字/节目名统一：王希|王熙|西风 → 王晰；日暮金|日木斤 → 日木斤
  · 剔除：做酒步骤、节目套话（欢迎收听/下期见/打烊）、纯语气
  · 输出：data/tavern_monologue.json + 待抽看清单 docs/小酒馆独白_待抽看.md

用法：python -X utf8 project_b/curate_tavern_monologue.py [--import]
"""
import argparse
import glob
import json
import os
import re
from collections import Counter

SRC = r"E:\wx\私有\王晰全文库\采访目录\小酒馆字幕"
BANK = r"D:\wx409.github.io\data\phrase_bank.json"
OUT_JSON = r"D:\wx409.github.io\data\tavern_monologue.json"
OUT_MD = r"D:\wx409.github.io\docs\小酒馆独白_待抽看.md"

NAME_FIX = [("王希", "王晰"), ("王熙", "王晰"), ("西风", "晰风"),
            ("日暮金", "日木斤"), ("日木斤深夜小酒馆", "日木斤深夜小酒馆"),
            ("小酒馆的王晰", "日木斤深夜小酒馆的王晰")]

RECIPE = re.compile(r"倒入|加入|毫升|搅拌|摇匀|切|杯底|柠檬|冰块|气泡水|糖|酒精度|调酒|特调")
ROUTINE = re.compile(r"留言|告诉我|打开窗|打开门|我们的小酒馆|你有点醉了|欢迎收听|下期|打烊|期待下次|我们下次|收听|订阅|公众号|晚安|好梦|先聊到|今天就到|想喝点什么|来先喝|喝杯|这杯酒|小酌|干杯|杯子里")
ASK = re.compile(r"留言问|问如何|有人问|有位|问怎样|的问题|来信问|问道")


def clean(text):
    for a, b in NAME_FIX:
        text = text.replace(a, b)
    return text


def episode_of(fname):
    m = re.match(r"第(\d+)期", fname)
    return int(m.group(1)) if m else 0


def blocks(body):
    """按「提问」切块：每个问题之后的整段回答 = 一个块"""
    body = re.sub(r"\s*\n\s*", "\n", body)
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    text = "\n".join(lines)
    # 找提问位置
    idx = [m.start() for m in ASK.finditer(text)]
    if not idx:
        return [text]
    out = []
    for i, s in enumerate(idx):
        e = idx[i + 1] if i + 1 < len(idx) else len(text)
        out.append(text[s:e])
    return out


def sentences(block):
    """块内再切：以连接词为边界，但每段保持完整语义起点"""
    block = re.sub(r"\n", "", block)
    parts = re.split(r"(?=(?:所以|但是|还有|就像|其实|首先|其次|最后|如果|因为|不要|一定要|记住))", block)
    return [p.strip() for p in parts if p.strip()]


def _push(s, ep, title, items, dropped):
    s = re.sub(r"\s+", "", s).strip("，、。；：\"“”")
    for _ in range(5):
        if s and s[-1] in "的了我你他她它都就要而是把被在和与或但所以为个呢吧啊":
            s = s[:-1]
        else:
            break
    s = s.strip("，、。；：")
    if len(s) < 14:
        dropped["太短"] += 1
        return
    if len(s) > 120:
        dropped["太长"] += 1
        return
    if RECIPE.search(s):
        dropped["做酒步骤"] += 1
        return
    if ROUTINE.search(s):
        dropped["节目套话"] += 1
        return
    if not re.search(r"[\u4e00-\u9fff]", s):
        dropped["无中文"] += 1
        return
    if re.fullmatch(r"[啊哦嗯吧呢啦呀对好的那这]+", s):
        dropped["纯语气"] += 1
        return
    items.append({"text": s, "ep": ep, "file": title,
                  "source": ("深夜小酒馆 第%d期（节目独白）" % ep) if ep else "深夜小酒馆（节目独白）"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--import", dest="do_import", action="store_true")
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(SRC, "*.txt")))
    items, dropped = [], Counter()

    for p in files:
        raw = open(p, encoding="utf-8", errors="ignore").read()
        body = raw.split("\n\n", 1)[-1]
        body = clean(body)
        ep = episode_of(os.path.basename(p))
        title = os.path.basename(p).rsplit(".", 1)[0]

        MARK = ("其实", "但是", "但", "所以", "还有", "就像", "如果", "因为", "不要",
                "我们", "你", "这", "那", "后来", "于是", "当", "很多", "有时候", "记得")
        CLOSE = "吧呢了啊呀哦吗嘛"

        for blk in blocks(body):
            lines = [l.strip() for l in blk.split("\n") if l.strip()]
            buf = ""
            for i, ln in enumerate(lines):
                buf += ln
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                long_enough = len(buf) >= 45
                ends_soft = buf and buf[-1] in CLOSE
                next_new = nxt.startswith(MARK)
                if (long_enough and (next_new or ends_soft)) or len(buf) >= 100:
                    _push(buf, ep, title, items, dropped)
                    buf = ""
            if buf:
                _push(buf, ep, title, items, dropped)

    # 去重（同一句可能跨期重复）
    seen, uniq = set(), []
    for it in items:
        k = re.sub(r"\s", "", it["text"])[:16]
        if k in seen:
            dropped["重复"] += 1
            continue
        seen.add(k)
        uniq.append(it)

    print("文件 %d｜候选 %d｜去重后 %d" % (len(files), len(items), len(uniq)))
    print("丢弃原因:", dict(dropped))

    json.dump({"count": len(uniq), "items": uniq},
              open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 抽看清单：按时长与「观点词」优先
    OPINION = ["其实", "不要", "一定要", "记住", "所以", "但是", "我们", "人生", "生活", "时间", "父母", "爱"]
    scored = sorted(uniq, key=lambda x: (-sum(1 for k in OPINION if k in x["text"]), -len(x["text"])))
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("# 小酒馆独白 · 待抽看（共 %d 条，列前 80）\n\n" % len(uniq))
        f.write("> 全部来自单人口播稿，按「提问—回答」整块切分，未拼接不同段落。\n\n")
        for it in scored[:80]:
            f.write("- %s  \n  <sub>%s</sub>\n" % (it["text"], it["source"]))
    print("已写:", OUT_JSON, "|", OUT_MD)
    for it in scored[:6]:
        print("  •", it["text"][:60], "|", it["source"][:22])

    if a.do_import:
        bank = json.load(open(BANK, encoding="utf-8"))
        exist = {re.sub(r"\s", "", i["text"]) for i in bank["items"]}
        added = 0
        for it in uniq:
            if it["text"] in exist:
                continue
            exist.add(it["text"])
            bank["items"].append({
                "text": it["text"], "type": "talk", "source": it["source"],
                "curated": False, "rights": "free", "mood": "talk",
                "verified": False, "quality": "mid",
            })
            added += 1
        bank["count"] = len(bank["items"])
        bank["by_type"] = dict(Counter(i["type"] for i in bank["items"]))
        bank["quality_stats"] = dict(Counter(i.get("quality", "high") for i in bank["items"]))
        json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("入池 %d 条（quality=mid）｜词句库 %d" % (added, bank["count"]))


if __name__ == "__main__":
    main()
