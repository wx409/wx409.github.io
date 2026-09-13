#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/queue.py —— 自动化分析管线第 3 步：读 data/analysis_queue.json，批量跑，回写结果。

队列即「新增分析对象」的唯一入口：往 data/analysis_queue.json 的 items 里加一条
{id, url, singer, title, year, kind（录音室/现场/综艺）, age_band, status:"pending"} 即可。

每步都写回 status，便于人工随时接手：
  pending → fetched（已下载到 tmp/）→ analyzed（已出结果 JSON）→ failed（附 reason）

合规：素材只落 tmp/（gitignore），**只发布方法与结果数据**，不入库、不二次分发、不嵌页面。

用法：
  python tools/queue.py                # 跑全部 pending
  python tools/queue.py --only zhaopeng-01
  python tools/queue.py --status       # 只看队列状态
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "data", "analysis_queue.json")
TMP = os.path.join(ROOT, "tmp")
RESULTS = os.path.join(ROOT, "tmp", "analysis")


def load():
    if os.path.exists(QUEUE):
        return json.load(io.open(QUEUE, encoding="utf-8"))
    return {"schema": "analysis_queue v1", "items": []}


def save(doc):
    io.open(QUEUE, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))


def run(cmd) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    print(("  " + (r.stdout or "").strip()[:600]).replace("\n", "\n  "))
    if r.returncode != 0:
        print("  [stderr]", (r.stderr or "").strip()[-500:])
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main() -> int:
    ap = argparse.ArgumentParser(description="分析队列批量执行")
    ap.add_argument("--only", default=None)
    ap.add_argument("--status", action="store_true")
    args = ap.parse_args()

    doc = load()
    items = doc.get("items", [])
    # 先做一次「有没有活」判断：CI 无待办时应秒退，不浪费环境安装时间
    runnable = [it for it in items if it.get("status") == "pending" and it.get("url")]
    if args.status or (not items):
        print("=" * 68)
        print("分析队列（%d 条，其中可跑 %d 条）" % (len(items), len(runnable)))
        print("=" * 68)
        for it in items:
            print("  %-16s %-10s %-8s url=%s" % (it.get("id"), it.get("singer"),
                                                 it.get("status"), "有" if it.get("url") else "无"))
        if runnable:
            print("\n提示：有 %d 条可跑，执行 python -X utf8 tools/queue_run.py 开始。" % len(runnable))
        return 0
    if not runnable and not args.only:
        print("[OK] 队列无待处理条目（pending 且已填 url）——退出码 2 表示'无活'，CI 可据此跳过")
        return 2

    todo = [it for it in items if it.get("status") == "pending"]
    if args.only:
        todo = [it for it in todo if it.get("id") == args.only]
    if not todo:
        print("[OK] 无待处理条目")
        return 0

    failed = 0
    for it in todo:
        iid = it.get("id")
        print("-" * 68)
        print("▶ %s（%s / %s / %s）" % (iid, it.get("singer"), it.get("title"), it.get("kind")))
        if not it.get("url"):
            # 未填 url 属「待人工选源」，不是失败：保持 pending，不污染失败计数
            print("  ⏸ 缺 url —— 保持 pending（待人工选定公开音源后填入）")
            it["reason"] = "待人工选定公开可访问音源后填入 url"
            save(doc)
            continue
        os.makedirs(TMP, exist_ok=True)
        rc, _ = run([sys.executable, os.path.join("tools", "fetch.py"), it["url"],
                     "--out", TMP, "--name", iid])
        if rc != 0:
            it["status"] = "failed"
            it["reason"] = "下载失败"
            failed += 1
            save(doc)
            continue
        audio = os.path.join(TMP, iid + ".wav")
        if not os.path.exists(audio):
            it["status"] = "failed"
            it["reason"] = "未找到下载的 wav"
            failed += 1
            save(doc)
            continue
        it["status"] = "fetched"
        save(doc)

        res_json = os.path.join(RESULTS, iid + ".json")
        rc, _ = run([sys.executable, os.path.join("tools", "analyze.py"), audio,
                     "--out", os.path.join(TMP, "work_" + iid), "--json", res_json])
        if rc != 0 or not os.path.exists(res_json):
            it["status"] = "failed"
            it["reason"] = "分析失败"
            failed += 1
            save(doc)
            continue
        res = json.load(io.open(res_json, encoding="utf-8"))
        it["status"] = "analyzed"
        it["result"] = res_json.replace("\\", "/")
        it["summary"] = {
            "lowest_stable_note": res["lowest_stable"]["note"],
            "lowest_stable_hz": res["lowest_stable"]["hz"],
            "span_octaves": res["span_octaves"],
            "caliber": "稳定音口径（时长 ≥0.15s、HNR ≥5dB、强度 ≥中位−25dB）",
        }
        save(doc)

    print("-" * 68)
    print("[OK] 处理 %d 条，失败 %d 条｜队列：%s" % (len(todo), failed, QUEUE))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
