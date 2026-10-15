# -*- coding: utf-8 -*-
"""按用户提供**两晚权威歌单图**重建《沉响与长歌》10-09 / 10-10 的段与曲目结构。

依据等级＝用户提供官方/粉丝整理图（2026-10-14/15）。原则：**不删数据**——
旧结构整段留档到 `legacy_segment_list`（含旧 no/song/by/songs），另建 `image_segment_list` 为准。

两套口径**同时保留**：
  `segments_no` ＝ 图编号段数（串烧按 1 段、点歌 4 首各占 1 段）
  `songs_n`     ＝ 串烧展开后的曲目数
用法：python -X utf8 project_b\\apply_setlist_image_corrections.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
SL9 = D / "show_setlists" / "2026-10-09_北京.json"
SL10 = D / "show_setlists" / "2026-10-10_北京.json"
ATTR = D / "performance_attribution.json"
ALIAS = D / "song_aliases.json"

# ── 图源结构（逐条照录；串烧括号内为展开曲目）──────────────────────────────
IMG9 = [
    (1, "嘎达梅林", "双人", ["嘎达梅林"]),
    (2, "忘不了", "王晰", ["忘不了"]),
    (3, "Your Man", "王晰", ["Your Man"]),
    (4, "天上的风", "傲日", ["天上的风"], "图源补录：明确「傲日其愣」独唱；此前按「待核」未并入"),
    (5, "四岁的海骝马", "傲日", ["四岁的海骝马"]),
    (6, "敕勒歌+乌兰巴托的夜", "双人", ["敕勒歌", "乌兰巴托的夜"]),
    (7, "心恋", "双人", ["心恋"]),
    (8, "在水一方", "傲日", ["在水一方"]),
    (9, "最美", "傲日", ["最美"]),
    (10, "唱起草原的歌", "傲日", ["唱起草原的歌"]),
    (11, "小毛驴", "王晰", ["小毛驴"], "图上标「摇滚」"),
    (12, "Yes or No", "王晰", ["Yes or No"]),
    (13, "在路上", "王晰", ["在路上"]),
    (14, "我会找到你", "傲日", ["我会找到你"]),
    (15, "我要你", "王晰", ["我要你"], "图上标「沙锤」"),
    (16, "蒙语串烧", "傲日", ["送亲歌", "小草", "莫合茹"]),
    (17, "英文串烧", "王晰", ["Smoke Gets in Your Eyes", "Moon River", "Love Me Tender"]),
    (18, "亲密爱人", "王晰", ["亲密爱人"], "点歌 1/4"),
    (19, "梦一场", "傲日", ["梦一场"], "点歌 2/4"),
    (20, "哭砂", "王晰", ["哭砂"], "点歌 3/4；图上标「粉丝接唱」"),
    (21, "岩峰里盛开的花", "傲日", ["岩峰里盛开的花"],
     "点歌 4/4；演唱者＝傲日其愣（用户确认 2026-10-14）；旧写作《岩缝中开出的花》"),
    (22, "美酒加咖啡", "双人", ["美酒加咖啡"]),
    (23, "酒歌", "双人", ["酒歌"]),
]
IMG10 = [
    (1, "嘎达梅林", "双人", ["嘎达梅林"]),
    (2, "忘不了", "王晰", ["忘不了"]),
    (3, "Your Man", "王晰", ["Your Man"]),
    (4, "心爱的姑娘", "傲日", ["心爱的姑娘"],
     "图源补录；我们旧写作《晚安我心爱的姑娘》（同一首，已建别名）"),
    (5, "四岁的海骝马", "傲日", ["四岁的海骝马"]),
    (6, "敕勒歌+乌兰巴托的夜", "双人", ["敕勒歌", "乌兰巴托的夜"]),
    (7, "心恋", "双人", ["心恋"]),
    (8, "在水一方", "傲日", ["在水一方"]),
    (9, "最美", "傲日", ["最美"]),
    (10, "唱起草原的歌", "傲日", ["唱起草原的歌"]),
    (11, "小毛驴", "王晰", ["小毛驴"]),
    (12, "Yes or No", "王晰", ["Yes or No"]),
    (13, "在路上", "王晰", ["在路上"]),
    (14, "回家", "傲日", ["回家"], "**加唱**（图注）；我们此前仅见于待核清单"),
    (15, "我要你", "王晰", ["我要你"]),
    (16, "蒙语串烧", "傲日", ["送亲歌", "小草", "莫合茹"]),
    (17, "英文串烧", "王晰", ["Smoke Gets in Your Eyes", "Moon River", "Love Me Tender"]),
    (18, "南屏晚钟", "王晰", ["南屏晚钟"], "点歌 1/4"),
    (19, "Love Is Over", "双人", ["Love Is Over"], "点歌 2/4（合唱）"),
    (20, "一生中最爱", "王晰", ["一生中最爱"], "点歌 3/4"),
    (21, "我会找到你", "傲日", ["我会找到你"], "点歌 4/4"),
    (22, "美酒加咖啡", "双人", ["美酒加咖啡"]),
    (23, "酒歌", "双人", ["酒歌"], "返场"),
]

# 图注「加唱 生日歌 双人」——列在点歌 4 首之后，但**不占编号**（与点歌分栏）
ENCORE10 = [{"song": "生日歌", "by": "双人", "note": "**加唱**（与点歌分栏）"}]


def build(img, legacy_by_no):
    out = []
    for row in img:
        no, song, by, songs = row[0], row[1], row[2], row[3]
        extra = row[4] if len(row) > 4 else ""
        item = {"no": no, "song": song, "by": by, "songs": songs,
                "source": "用户提供权威歌单图（2026-10-14）"}
        if extra:
            item["note"] = extra
        # 旧结构里的补充说明（如 notes/songs_by）按曲名并入，不丢
        for lg in legacy_by_no:
            if lg.get("songs") and set(lg["songs"]) & set(songs):
                for k in ("songs_by", "singer", "evidence"):
                    if lg.get(k) and k not in item:
                        item[k] = lg[k]
                if lg.get("note") and "note" not in item:
                    item["note"] = lg["note"]
        out.append(item)
    return out


def main() -> int:
    d9 = json.loads(SL9.read_text(encoding="utf-8"))
    d10 = json.loads(SL10.read_text(encoding="utf-8"))

    for d, img, tag in ((d9, IMG9, "10-09"), (d10, IMG10, "10-10")):
        legacy = d.get("segment_list") or []
        # 旧结构整段留档（不删数据）
        d.setdefault("legacy_segment_list", legacy)
        d.setdefault("legacy_note",
                     "`legacy_segment_list` ＝ 图源更正前的旧结构（19 段口径，含串烧合并与点歌缺项），"
                     "**仅作留痕，不再作为事实源**。")
        d["image_segment_list"] = build(img, legacy)
        d["segment_list"] = d["image_segment_list"]           # 事实源切换到图源结构
        d["segments_no"] = len(img)
        d["songs_n"] = sum(len(x[3]) for x in img)
        d["segments"] = d["segments_no"]
        d["songs"] = sorted({s for x in img for s in x[3]})
        d["segment_count_note"] = (
            "**两套口径并存**：`segments_no`＝图编号段数（串烧按 1 段、点歌 4 首各占 1 段）；"
            "`songs_n`＝串烧展开后的曲目数。旧文所写「19 段 / 26 曲」系早期按 19 段歌单"
            "（串烧合并、点歌只列 3 首）计，**已作废**，以本文件两套字段为准（旧结构见 `legacy_segment_list`）。")
        d["source"] = (d.get("source") or "") + "＋**用户提供权威歌单图（2026-10-14，图编号 23 段口径）**"
        d["corrected_at"] = "2026-10-14"
        print(f"[OK] {tag}：段 {d['segments_no']}｜展开曲 {d['songs_n']}｜曲名集 {len(d['songs'])}")

    # 10-09 点歌/加唱结构
    d9["point_song_segment"] = {
        "segment_no": 18, "sung_count": 4,
        "sung_this_show": [
            {"song": "亲密爱人", "by": "王晰", "no": 18},
            {"song": "梦一场", "by": "傲日", "no": 19},
            {"song": "哭砂", "by": "王晰", "no": 20, "note": "粉丝接唱（图注）"},
            {"song": "岩峰里盛开的花", "by": "傲日其愣（用户确认 2026-10-14）", "no": 21,
             "alias_note": "旧写作《岩缝中开出的花》；以图源为准"},
        ],
        "candidate_pool": ["亲密爱人", "哭砂", "南屏晚钟", "一生中最爱", "梦一场",
                           "岩峰里盛开的花", "贝加尔湖畔", "赞歌"],
        "source": "用户提供 10-09 权威歌单图（点歌 4 首各占 No.18–21）",
    }
    # 10-10 点歌 + 加唱（分栏）
    d10["point_song_segment"] = {
        "segment_no": 18, "sung_count": 4,
        "sung_this_show": [
            {"song": "南屏晚钟", "by": "王晰", "no": 18},
            {"song": "Love Is Over", "by": "王晰 × 傲日其愣（合唱）", "no": 19},
            {"song": "一生中最爱", "by": "王晰", "no": 20},
            {"song": "我会找到你", "by": "傲日其愣", "no": 21},
        ],
        "encore_extra": [{"song": "生日歌", "by": "双人", "no": 22, "kind": "加唱（非点歌）"}],
        "source": "用户提供 10-10 权威歌单图（No.18–21 点歌 + 加唱生日歌）",
    }
    d10["has_encore_extra"] = ["生日歌"]
    d10.setdefault("notes", []).append(
        "★ 2026-10-14 图源更正：点歌段补至 **4 首**（南屏晚钟 / Love Is Over / 一生中最爱 / 我会找到你）；"
        "**加唱《生日歌》单列**（与点歌分栏）；补 No.4《心爱的姑娘》（＝旧写《晚安我心爱的姑娘》）。")
    d9.setdefault("notes", []).append(
        "★ 2026-10-14 图源更正：补 **No.4《天上的风》（傲日其愣独唱）**；点歌 4 首成立"
        "（No.18–21）；曲名以图为准（岩峰里盛开的花 / 唱起草原的歌）。")

    SL9.write_text(json.dumps(d9, ensure_ascii=False, indent=1), encoding="utf-8")
    SL10.write_text(json.dumps(d10, ensure_ascii=False, indent=1), encoding="utf-8")

    # performance_attribution：天上的风 正式并入剔除清单
    a = json.loads(ATTR.read_text(encoding="utf-8"))
    sh = a["shows"][0]
    sh["pending"] = [p for p in (sh.get("pending") or []) if p.get("song") != "天上的风"]
    if "天上的风" not in sh["exclude_for_subject"]:
        sh["exclude_for_subject"].append("天上的风")
    ee = sh.setdefault("exclude_evidence", {})
    bucket = ee.setdefault("用户确认（2026-10-14）", [])
    if "天上的风" not in bucket:
        bucket.append("天上的风")
    sh.setdefault("renames", {})["岩缝中开出的花"] = {"canonical": "岩峰里盛开的花",
                                                   "by": "图源 2026-10-14", "kept_old_as_alias": True}
    sh["renames"]["晚安我心爱的姑娘"] = {"canonical": "心爱的姑娘", "by": "图源 2026-10-14（10-10 No.4）"}
    ATTR.write_text(json.dumps(a, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[OK] exclude_for_subject=%d 条；pending 余 %d 条" % (
        len(sh["exclude_for_subject"]), len(sh.get("pending") or [])))

    # 别名表
    al = json.loads(ALIAS.read_text(encoding="utf-8"))
    A = al.setdefault("aliases", {})
    A.setdefault("岩峰里盛开的花", [])
    for old in ("岩缝中开出的花", "岩峰中开出的花"):
        if old not in A["岩峰里盛开的花"]:
            A["岩峰里盛开的花"].append(old)
    A.setdefault("心爱的姑娘", [])
    if "晚安我心爱的姑娘" not in A["心爱的姑娘"]:
        A["心爱的姑娘"].append("晚安我心爱的姑娘")
    al["generated_at"] = datetime.now().isoformat(timespec="seconds")
    ALIAS.write_text(json.dumps(al, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[OK] 别名：岩峰里盛开的花 ←[岩缝/岩峰中开出的花]；心爱的姑娘 ←[晚安我心爱的姑娘]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

