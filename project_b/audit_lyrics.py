"""歌词全量体检：逐条过规则，生成「可疑清单」

检查项（每条给出命中原因）：
  A 无中文 ／ B 字母数字占比过高 ／ C 长度越界（<8 或 >34）
  D 同一字连续重复 3 次 ／ E 署名/制作名单特征 ／ F 标题特征（含王晰/Elvis/歌名-歌手）
  G 无中文虚词（的/了/在/是/我/你/不/就/都/也/还/和/与/把/被/给/很/太/才/又）
  H 纯标点/符号 ／ I 与歌名完全相同 ／ J 疑似演出/节目串词（欢迎/下期/小酒馆…）

输出：docs/歌词可疑清单.md（分级：删 / 复核 / 留观察）
"""
import json
import re
from collections import Counter

BANK = r"D:\wx409.github.io\data\phrase_bank.json"
OUT = r"D:\wx409.github.io\docs\歌词可疑清单.md"

CJK = re.compile(r"[\u4e00-\u9fff]")
FUNC = set("的了在是我你他不就都也还和与把被给很太才又这那有要会能来说去来着过们")
CREDIT = re.compile(r"作词|作曲|编曲|制作人|监制|吉他|贝斯|鼓|键盘|和声|录音|混音|母带|统筹|出品|发行|"
                    r"Lyricist|Composer|Arranger|Producer|Guitar|Bass|Mixing|Mastering|"
                    r"弦乐|马头琴|长笛|小提琴|大提琴|口琴|古筝|二胡|手风琴|Program|Rap|Doublebass|"
                    r"制作公司|项目经理|监唱|配唱|录音师|助理|"
                    r"^[\u4e00-\u9fffA-Za-z]{1,8}[:：]|[A-Za-z]{3,}\s*[:：]")

TITLE = re.compile(r"王晰|Elvis|^(.*)[-—–]\1?.*$")
SHOW = re.compile(r"欢迎|下期|小酒馆|订阅|公众号|晚安|好梦|打烊|收听")


def lyric_name(it):
    m = re.search(r"歌词《(.+)》", it.get("source") or "")
    return m.group(1).strip() if m else ""


def check(t, lname):
    """返回 (级别, 原因列表)。级别：drop / review / watch / ok"""
    reasons, drop = [], False
    s = t.strip()
    if not CJK.search(s):
        reasons.append("A 无中文"); drop = True
    if len(s) < 6:
        reasons.append("C 过短(%d)" % len(s)); drop = True
    elif len(s) < 8:
        reasons.append("C 偏短(%d)" % len(s))
    if len(s) > 34:
        reasons.append("C 过长(%d)" % len(s))
    if re.search(r"([\u4e00-\u9fff])\1\1", s):
        uniq = len(set(s))
        if uniq <= 3 and len(s) <= 8:
            reasons.append("D 重复字串"); drop = True
        else:
            reasons.append("D 重复字（歌词手法，非错）")
    if CREDIT.search(s):
        reasons.append("E 署名/名单"); drop = True
    if re.search(r"王晰|Elvis", s):
        reasons.append("F 含歌手名"); drop = True
    if lname and (s == lname or s.replace("《", "").replace("》", "") == lname):
        reasons.append("I 与歌名相同（可能标题行）")
    if not any(ch in FUNC for ch in s):
        reasons.append("G 无虚词（可能是碎片）")
    if re.fullmatch(r"[\W_]+", s):
        reasons.append("H 纯符号"); drop = True
    if SHOW.search(s):
        reasons.append("J 节目串词"); drop = True
    ascii_n = len(re.findall(r"[A-Za-z0-9]", s))
    if ascii_n / max(len(s), 1) > 0.4:
        reasons.append("B 字母数字占比高")

    if drop:
        return "drop", reasons
    if any(r.startswith(("C 过长", "B ")) for r in reasons):
        return "review", reasons
    if reasons:
        return "watch", reasons
    return "ok", reasons


def main():
    bank = json.load(open(BANK, encoding="utf-8"))
    items = [i for i in bank["items"] if i["type"] == "lyrics"]
    print("歌词条数", len(items))

    buckets = {"drop": [], "review": [], "watch": []}
    ok = 0
    for it in items:
        lvl, rs = check(it["text"], lyric_name(it))
        if lvl == "ok":
            ok += 1
        else:
            buckets[lvl].append((it["text"], it["source"], rs))

    print("合格 %d｜应删 %d｜需复核 %d｜留观察 %d"
          % (ok, len(buckets["drop"]), len(buckets["review"]), len(buckets["watch"])))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("# 歌词可疑清单\n\n")
        f.write("共 %d 条歌词；合格 %d｜**应删 %d**｜需复核 %d｜留观察 %d\n\n"
                % (len(items), ok, len(buckets["drop"]), len(buckets["review"]), len(buckets["watch"])))
        f.write("规则：A 无中文 / B 字母数字过多 / C 长度越界 / D 重复字 / E 署名名单 / "
                "F 歌手名 / G 无虚词 / H 纯符号 / I 与歌名相同 / J 节目串词\n\n")

        for lvl, title in (("drop", "## 一、应删（明显非歌词）"),
                           ("review", "## 二、需复核（可能截断或混入）"),
                           ("watch", "## 三、留观察（轻疑）")):
            f.write("%s：%d 条\n\n" % (title, len(buckets[lvl])))
            for t, src, rs in buckets[lvl][:120]:
                f.write("- %s  \n  <sub>%s ｜ %s</sub>\n" % (t, src, "；".join(rs)))
            if len(buckets[lvl]) > 120:
                f.write("\n…（其余 %d 条省略）\n" % (len(buckets[lvl]) - 120))
            f.write("\n")

    print("→", OUT)
    print("\n应删样例：")
    for t, src, rs in buckets["drop"][:8]:
        print("  ", t[:48], "|", "；".join(rs)[:26])
    print("\n需复核样例：")
    for t, src, rs in buckets["review"][:8]:
        print("  ", t[:48], "|", "；".join(rs)[:26])


if __name__ == "__main__":
    main()
