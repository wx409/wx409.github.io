"""一条链接 → 全流程：下视频/取文 → 转写 → 切分说话人 → 切句入池 → 重建页面

用法：
  python -X utf8 project_b/ingest_link.py --weibo "https://m.weibo.cn/detail/xxxx" --source "节目名 日期"
  python -X utf8 project_b/ingest_link.py --text-file "某访谈.txt" --source "媒体 2025"
  python -X utf8 project_b/ingest_link.py --weibo ... --no-build     # 只入池，不重建页面
"""
import argparse
import os
import re
import subprocess
import sys

PROJ = r"D:\wx409.github.io\project_b"
PY = sys.executable


def run(script, *args):
    cmd = [PY, "-X", "utf8", os.path.join(PROJ, script)] + list(args)
    print("  →", os.path.basename(script), " ".join(a[:24] for a in args))
    return subprocess.call(cmd)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weibo")
    ap.add_argument("--text-file")
    ap.add_argument("--source", required=True, help="出处（节目名/媒体 + 日期）")
    ap.add_argument("--quality", default="mid", choices=["high", "mid", "low"])
    ap.add_argument("--no-build", action="store_true")
    ap.add_argument("--skip-split", action="store_true")
    a = ap.parse_args()

    md_path = ""

    # 1) 视频链接：转写
    if a.weibo:
        rc = run("transcribe.py", "--weibo", a.weibo)
        if rc != 0:
            print("转写失败，请先修 cookie 或检查链接")
            return rc

    # 2) 找文本源：优先显式文件，其次最新转写
    if a.text_file:
        md_path = a.text_file
    else:
        txt_dir = r"E:\wx\私有\王晰全文库\采访目录\全文"
        cands = [os.path.join(txt_dir, f) for f in os.listdir(txt_dir)
                 if f.endswith("_转写_turbo.txt")]
        if not cands:
            print("找不到转写文件")
            return 2
        latest = max(cands, key=os.path.getmtime)
        print("使用最新转写：", os.path.basename(latest))
        if not a.skip_split:
            run("split_speakers2.py", latest)
            guess = latest.replace("_转写_turbo.txt", "_转写_turbo_王晰.md")
            md_path = guess if os.path.exists(guess) else latest
        else:
            md_path = latest

    # 3) 切句入池
    rc = run("add_phrases_from_file.py", "--file", md_path,
             "--source", a.source, "--type", "interview", "--quality", a.quality)
    if rc != 0:
        return rc

    # 4) 重建
    if not a.no_build:
        run("build_phrases_page.py")
        run("build_nav.py")

    print("\n完成。建议接着跑：")
    print("  python -X utf8 project_b\\curate_interview_pool3.py   # 重挑骰面")
    print("  python -X utf8 project_b\\audit_jsonld.py && audit_nav.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
