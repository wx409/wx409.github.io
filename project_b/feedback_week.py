# -*- coding: utf-8 -*-
"""演出反馈一周工作流（一键串联，第一性原理：收集→匿名展示→全文归档→分析→进KB→发布）

设计：
  ①收集   多通道增量（B站自动；微博/小红书平台风控，默认提示手动，可 --full-collect 强跑）
  ②匿名展示  build_show_repo（≤60字+平台标签+外链，不公开昵称 → live 页 audience-repo）
  ③全文归档  build_sample_comments（评论全文/图片/原始JSON → E:\\wx 私有，本地分析语料）
  ④评论分析  analyze_audience_comments（情感/评价维度/歌曲提及，论文友好）
  ⑤进知识库  build_kb_graph（含评论维度）+ build_kb_vectors（语义索引）
  ⑥发布     git commit + push + IndexNow

用法：
  python project_b/feedback_week.py --date 2026-08-23 --city 广州            # 全流程(发布)
  python project_b/feedback_week.py --date 2026-08-23 --city 广州 --no-push  # 只跑本地不发布
  python project_b/feedback_week.py --date 2026-08-23 --city 广州 --no-collect # 跳过收集(数据已有)
日志：logs/feedback_week_<日期>.log
"""
import argparse, datetime, io, subprocess, sys
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
PY = sys.executable
LOGS = ROOT / "logs"


def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    LOGS.mkdir(exist_ok=True)
    with open(LOGS / ("feedback_week_%s.log" % datetime.date.today().strftime("%Y%m%d")),
              "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(desc, args, cwd=None):
    log("-- %s --" % desc)
    r = subprocess.run([PY, "-X", "utf8"] + args, cwd=cwd or ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        log("[warn] %s 退出码 %d：%s" % (desc, r.returncode, (r.stdout or "")[-200:].strip()))
    else:
        tail = [l for l in (r.stdout or "").splitlines() if l.strip()][-2:]
        for l in tail:
            log("   " + l.strip())
    return r.returncode


def find_page(city):
    hits = sorted(ROOT.glob("live/*%s*2026.html" % city)) + sorted(ROOT.glob("live/*%s*.html" % city))
    for h in hits:
        if "setlists" not in h.name:
            return "live/%s" % h.name
    return ""


def main():
    if sys.stdout and getattr(sys.stdout, "buffer", None):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--city", required=True)
    ap.add_argument("--no-collect", action="store_true", help="跳过收集（数据已有）")
    ap.add_argument("--full-collect", action="store_true", help="全通道收集（含微博/小红书，风控风险）")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()

    log("=== 演出反馈一周工作流：%s %s站 ===" % (a.date, a.city))

    # ① 收集
    if not a.no_collect:
        bili = [str(ROOT / "project_b" / "collect_show_feedback.py"),
                "--date", a.date, "--city", a.city, "--bili-only", "--bili-pages", "3", "--bili-order", "pubdate"]
        run("B站增量收集(3页,最新)", bili)
        if a.full_collect:
            run("微博/小红书全通道收集", [str(ROOT / "project_b" / "collect_show_feedback.py"),
                                        "--date", a.date, "--city", a.city, "--skip-bili"])
        else:
            log("微博/小红书：平台风控高，默认跳过自动抓取（可用操作中心 5 或 --full-collect 手动补）")

    # ② 匿名入库
    page = find_page(a.city)
    if page:
        run("匿名短评入库 live 页", [str(ROOT / "project_b" / "build_show_repo.py"),
                                    "--date", a.date, "--city", a.city, "--page", page, "--no-push"])
    else:
        log("[warn] 未匹配到 %s 的 live 页，跳过匿名入库（可在操作中心 6 手动指定）" % a.city)

    # ③ 全文归档
    run("评论全文/图片/原始JSON归档", [str(ROOT / "tools" / "build_sample_comments.py"),
                                    "--date", a.date.replace("-", ""), "--city", a.city])

    # ④ 评论分析
    run("评论多层面分析(论文友好)", [str(ROOT / "project_b" / "analyze_audience_comments.py"),
                                   "--date", a.date, "--city", a.city])

    # ⑤ 知识库（含评论维度）+ 语义索引
    run("知识库三层重建(含评论维度)", [str(ROOT / "project_b" / "build_kb_graph.py")])
    run("语义索引重建", [str(ROOT / "tools" / "build_kb_vectors.py")])
    run("问答库静态页 qa.html", [str(ROOT / "tools" / "build_qa_page.py")])

    # ⑥ 发布
    if not a.no_push:
        subprocess.run(["git", "-C", str(ROOT), "add", "live/", "data/kb", "data/qa_bank.json",
                        "qa.html", "sitemap.xml", "llms.txt"])
        subprocess.run(["git", "-C", str(ROOT), "commit", "-m",
                        "演出反馈一周工作流(%s %s站): 匿名入库+全文归档+评论分析+KB评论维度" % (a.date, a.city)])
        r = subprocess.run(["git", "-C", str(ROOT), "push", "origin", "main"])
        log("git push 退出码 %d" % r.returncode)
        run("IndexNow 通知", [str(ROOT / "project_b" / "deploy_all.py"), "--notify-only"])
    else:
        log("--no-push 模式，未提交发布。")

    log("=== 完成。产物：live页反馈 / E:\\wx 全文归档 / temp\\audience_analysis / data/kb 评论维度 ===")


if __name__ == "__main__":
    main()
