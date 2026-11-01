"""每日：重算口径基线 → 同步站点 → 提交推送（补齐「指数进大屏但档案层滞后」的缺口）

调用链：
  E:\\wx\\论文素材_王晰作传\\基线口径\\compute_baseline_v1.py   （内部会同步 data/archive_baseline.json）
  project_b\\build_calibers.py                                （登记口径数字）
  git add data/ dashboard/ → commit → push

用法：python -X utf8 project_b/publish_baseline_daily.py [--no-push]
"""
import argparse
import os
import subprocess
import sys
import time

ROOT = r"D:\wx409.github.io"
BASELINE = r"E:\wx\论文素材_王晰作传\基线口径\compute_baseline_v1.py"
PY = sys.executable


def run(args, cwd=None):
    print("→", " ".join(os.path.basename(a) if a.endswith(".py") else a for a in args)[:96])
    return subprocess.call(args, cwd=cwd or ROOT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()

    rc = run([PY, "-X", "utf8", BASELINE])
    print("基线重算退出码", rc)
    if rc != 0:
        print("！基线重算失败，放弃发布")
        return 1

    run([PY, "-X", "utf8", os.path.join(ROOT, "project_b", "build_calibers.py")])

    # 只提交数据与派生页，避免误带临时文件
    subprocess.call(["git", "add", "data", "dashboard"], cwd=ROOT)
    diff = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", errors="ignore")
    changed = [x for x in (diff.stdout or "").splitlines() if x.strip()]
    if not changed:
        print("无变化，跳过提交")
        return 0
    print("将提交 %d 个文件" % len(changed))
    msg = "口径基线自动更新 (%s)" % time.strftime("%m-%d %H:%M")
    subprocess.call(["git", "commit", "-m", msg], cwd=ROOT)
    if not a.no_push:
        rc2 = subprocess.call(["git", "push", "origin", "main"], cwd=ROOT)
        print("推送退出码", rc2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
