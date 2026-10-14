# -*- coding: utf-8 -*-
"""抓 B站**指定收藏夹**全量清单（复用 `音域分析\\抓取B站收藏夹.py` 的取数与分类逻辑，
只把写死的 fav_id 参数化；不另造轮子）。

用法：
  python -X utf8 project_b\\fetch_bili_favlist.py --fid 4116829058
  python -X utf8 project_b\\fetch_bili_favlist.py --fid 4116829058 --out "E:\\...\\传播监测\\B站收藏夹_4116829058.json"

字段：bvid / title / duration_s / up / ctime / 分类 / 关键词 / url（＋本脚本补的 目标曲目命中）
纪律：只取元数据、不下载音视频；清单落本地（音视频不入 git、不上页面）。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

COOKIE_FILE = Path(r"E:\wx\index_records\bilibili_cookies.txt")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
SPACE = "1327234958"

# 复用既有分类规则（与 抓取B站收藏夹.py 同表；顺序即优先级）
RULES = [
    # 顺序即优先级。⚠️ 2026-10-14 修：原来「纯享/翻唱集/AI」一律判「排除-他人分析」——
    # 但标题写「纯享」的也可能是**本人演唱的纯享剪辑**（如 FineLIVE翻浪四季歌会｜王晰《晚风》纯享版），
    # 从标题无法判定「他人翻唱」→ 降级为「待核（需人耳/直拍确认演唱者）」，不擅自排除。
    ("原曲/他人翻唱", ["他人翻唱", "翻唱集", "原唱版", "AI翻唱", "AI 王晰"]),
    ("待核-需人耳", ["纯享", "音高测量", "3D环绕", "混剪"]),
    ("棚版混音", ["混音工程版", "混音师版本", "棚版"]),
    ("饭拍直拍", ["直拍", "饭拍", "站姐", "Hi-res", "4K60"]),
    ("晚会", ["跨年", "春晚", "晚会", "国庆", "中秋", "元宵", "春节", "元旦", "庆典"]),
    ("综艺", ["经典咏流传", "情歌大会", "声入人心", "我是歌手", "歌手", "追光吧", "我们的歌",
              "天赐的声音", "蒙面", "星光大道", "开门大吉", "天天向上", "快乐大本营",
              "我是唱作人", "时光音乐会", "节目", "综艺", r"第\d+期", "唱作人", "舞台"]),
    ("盛典商演", ["盛典", "颁奖", "发布会", "音乐节", "之夜", "演唱会", "歌会", "红毯", "开幕"]),
]

# 目标曲目（用户问题：够不够用作音源）
TARGETS = {
    "Smoke Gets in Your Eyes": ["smoke gets in your eyes", "smoke", "烟雾", "你的眼睛"],
    "Moon River": ["moon river", "月亮河"],
    "一生中最爱": ["一生中最爱"],
    "沉响相关": ["沉响", "长歌", "天桥", "20261009", "20261010", "我要你", "梦一场", "敕勒",
                 "乌兰巴托", "四岁的海骝马", "最美", "在水一方", "我会找到你", "小毛驴",
                 "Yes or No", "忘不了", "心恋", "酒歌", "美酒加咖啡", "岩缝", "岩峰", "亲密爱人", "哭砂"],
}


def classify(title: str):
    for cat, kws in RULES:
        hit = [k for k in kws if re.search(k, title, re.I)]
        if hit:
            return cat, hit
    return "其他", []


def get(url: str, cookie: str):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": f"https://space.bilibili.com/{SPACE}/", "Cookie": cookie})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fid", required=True, help="收藏夹 media_id（favlist?fid=…）")
    ap.add_argument("--out", default="", help="输出 JSON 路径（默认落传播监测目录）")
    a = ap.parse_args()
    out = Path(a.out) if a.out else Path(r"E:\wx\论文素材_王晰作传\传播监测") / f"B站收藏夹_{a.fid}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    cookie = COOKIE_FILE.read_text(encoding="utf-8", errors="replace").strip() if COOKIE_FILE.exists() else ""

    items, page, fav_title, fav_owner = [], 1, "", ""
    while True:
        url = (f"https://api.bilibili.com/x/v3/fav/resource/list?media_id={a.fid}"
               f"&pn={page}&ps=20&platform=web&order=mtime&type=0&tid=0")
        try:
            j = get(url, cookie)
        except Exception as e:
            print("[X] 请求失败：", repr(e)[:160])
            return 1
        if j.get("code") != 0:
            print("[X] API 错误：", j.get("code"), j.get("message"))
            return 1
        d = j.get("data") or {}
        info = d.get("info") or {}
        fav_title = fav_title or (info.get("title") or "")
        fav_owner = fav_owner or ((info.get("upper") or {}).get("name") or "")
        medias = d.get("medias") or []
        if not medias:
            break
        for m in medias:
            title = m.get("title") or ""
            cat, kw = classify(title)
            hit = [t for t, ws in TARGETS.items() if any(w.lower() in title.lower() for w in ws)]
            items.append({
                "bvid": m.get("bvid"), "title": title,
                "duration_s": m.get("duration"),
                "up": (m.get("upper") or {}).get("name"),
                "ctime": (datetime.fromtimestamp(m.get("ctime", 0)).strftime("%Y-%m-%d")
                          if m.get("ctime") else ""),
                "pubtime": (datetime.fromtimestamp(m.get("pubtime", 0)).strftime("%Y-%m-%d")
                            if m.get("pubtime") else ""),
                "分类": cat, "关键词": kw, "目标曲目": hit,
                "url": f"https://www.bilibili.com/video/{m.get('bvid')}",
            })
        if not d.get("has_more"):
            break
        page += 1
        time.sleep(0.6)

    doc = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
           "fav_id": a.fid, "fav_title": fav_title, "fav_owner": fav_owner,
           "count": len(items),
           "分类统计": dict(Counter(x["分类"] for x in items)),
           "目标曲目命中": {t: [x["bvid"] for x in items if t in x["目标曲目"]] for t in TARGETS},
           "items": items,
           "note": "只取元数据、不下载音视频；音视频不入 git、不上页面。"}
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] 收藏夹「{fav_title}」(owner {fav_owner}) 共 {len(items)} 条 → {out}")
    for k, v in Counter(x["分类"] for x in items).most_common():
        print(f"   {k}: {v}")
    print("   目标曲目命中：")
    for t, bvs in doc["目标曲目命中"].items():
        if bvs:
            print(f"   {t}: {len(bvs)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
