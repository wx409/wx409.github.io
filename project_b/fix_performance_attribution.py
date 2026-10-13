# -*- coding: utf-8 -*-
"""归属修正迁移：长表备注 + show_setlists 补 performer（可复跑、幂等）。

依据（唯一来源，可复核）：
  · 10-09：`原始材料\\沉响与长歌_20261009_歌单与现场链接.md` 第 10–30 行的 19 段表（自带「演唱」列）
  · 10-10：`data\\show_setlists\\2026-10-10_北京.json` 已有 `segment_list[].by`
  · 覆盖表：`data\\performance_attribution.json`（只加归属、不删数据）

做什么（就地改，先备份）：
  ① 备份 `E:\\wx\\index_records\\王晰演出活动.xlsx` → 同目录 `王晰演出活动.备份20261013_归属修正.xlsx`
  ② 行 204「备注」追加归属说明（保留原备注；自解释：傲日独唱 9 曲 + 王晰独唱 13 + 双人 7 + 2 待核）
  ③ `data/show_setlists/2026-10-09_北京.json` 补 `segment_list`（含 `by`），**保留原 `songs` 平铺字段**
  ④ `data/show_setlists/2026-10-10_北京.json` 的 `songs` 保留，`segment_list` 逐段补 `performer`（= 原 `by`，字段名两场统一）

用法：python -X utf8 project_b\\fix_performance_attribution.py [--apply]   （默认只试算）
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(__file__).resolve().parent.parent
XLSX = Path(r"E:\wx\index_records\王晰演出活动.xlsx")
BACKUP = XLSX.with_name("王晰演出活动.备份20261013_归属修正.xlsx")
SRC_MD = Path(r"E:\wx\论文素材_王晰作传\原始材料\沉响与长歌_20261009_歌单与现场链接.md")
SL9 = SITE / "data" / "show_setlists" / "2026-10-09_北京.json"
SL10 = SITE / "data" / "show_setlists" / "2026-10-10_北京.json"
ATTR = SITE / "data" / "performance_attribution.json"
ROW = 204  # 长表「序号」=204 的那一行


def _split_medley(song: str) -> list[str]:
    """串烧/点歌段拆曲名：英文串烧按「A / B / C」切（保留多词英文曲名），
    点歌段按「曲（演唱者）」逐首取曲名，带「结束曲/返场曲：」前缀的去掉前缀。"""
    body = song
    for pre in ("民族串烧：", "英文串烧：", "点歌环节：", "结束曲：", "返场曲："):
        if body.startswith(pre):
            body = body[len(pre):]
    body = body.split("（", 1)[0] if body.startswith("点歌环节") else body
    # 点歌段：逐「曲（演唱者）」提取
    parts = re.findall(r"([^/（）()]+?)\s*[（(]([^）)]*)[）)]", body)
    if parts and any(len(p[1]) <= 8 for p in parts):
        return [p[0].strip(" 、，,") for p in parts if len(p[0].strip(" 、，,")) >= 2]
    # 串烧：按 / 或 、切；英文曲名保留整段
    out = []
    for x in re.split(r"\s*/\s*|、", body):
        x = x.strip(" 、，,。.")
        if len(x) >= 2:
            out.append(x)
    return out


def parse_md_segments() -> list[dict]:
    """从 10-09 源文档的 19 段表解析 (no, song, by, songs[])。"""
    text = SRC_MD.read_text(encoding="utf-8")
    segs = []
    for ln in text.splitlines():
        m = re.match(r"\|\s*(\d+)\s*\|\s*(.+?)\s*\|\s*(双人|王晰|傲日)\s*\|", ln)
        if not m:
            continue
        no, song, by = int(m.group(1)), m.group(2).strip(), m.group(3)
        if "串烧" in song or "点歌" in song or "结束曲" in song or "返场" in song:
            songs = _split_medley(song)
        else:
            songs = [b.strip() for b in re.split(r"[＋+]", song) if b.strip()]
        seg = {"no": no, "song": song, "by": by, "songs": songs}
        if "点歌" in song:
            sb = {}
            for k, v in re.findall(r"([^/（）()]+?)\s*[（(]([^）)]*)[）)]", song):
                k = k.strip(" 、，,:：")
                if k.startswith("点歌环节"):
                    k = k.split("：")[-1].strip()
                if k:
                    sb[k] = v.strip()
            seg["songs_by"] = sb
        segs.append(seg)
    return segs


def attr_show(date: str) -> dict:
    doc = json.loads(ATTR.read_text(encoding="utf-8"))
    return next((s for s in doc["shows"] if s["key"] == date), {})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    segs = parse_md_segments()
    print("10-09 源文档解析：%d 段" % len(segs))
    for s in segs:
        print("   %2d %-34s by=%-4s %s" % (s["no"], s["song"][:34], s["by"], s["songs"]))

    attr9, attr10 = attr_show("2026-10-09"), attr_show("2026-10-10")
    d9 = json.loads(SL9.read_text(encoding="utf-8"))
    d10 = json.loads(SL10.read_text(encoding="utf-8"))

    # ② 备注追加（幂等：已有标记则跳过）
    from openpyxl import load_workbook
    wb = load_workbook(XLSX)
    ws = wb.active
    hdr = [c.value for c in ws[1]]
    note_col = hdr.index("备注") + 1
    seq_col = hdr.index("序号") + 1
    target = None
    for r in range(2, ws.max_row + 1):
        if ws.cell(r, seq_col).value == ROW:
            target = r
            break
    if target is None:
        print("[X] 长表找不到序号 %d 的行" % ROW)
        return 1
    old_note = str(ws.cell(target, note_col).value or "")
    MARK = "【归属修正 20261013】"
    if MARK in old_note:
        print("[=] 长表备注已含归属说明，跳过追加")
    else:
        excl = attr9.get("exclude_for_subject", [])
        pend = [p["song"] for p in attr9.get("pending", [])]
        keep = attr9.get("keep", {})
        add = (MARK + "本行为**双人演唱会全场曲目**（王晰 × 傲日其愣），"
               "「演唱曲目」列按全场登记，**含傲日其愣独唱**：%s；"
               "其余为**双人合唱 %d 首**（%s）与**王晰独唱 %d 首**（%s）；"
               "待核（疑傲日独唱，用户未确认，暂不计入剔除清单）：%s。"
               "细分见 data\\show_setlists\\2026-10-09_北京.json 的 segment_list 与 "
               "data\\performance_attribution.json。" % (
                   "、".join(excl), len(keep.get("双人合唱", [])), "、".join(keep.get("双人合唱", [])),
                   len(keep.get("王晰独唱", [])), "、".join(keep.get("王晰独唱", [])),
                   "、".join(pend) if pend else "无"))
        new_note = (old_note + "；" + add) if old_note else add
        print("\n[备注] 旧长度 %d → 新长度 %d" % (len(old_note), len(new_note)))
        print("[备注] 追加片段：", add[:400])
        if a.apply:
            ws.cell(target, note_col).value = new_note

    # ③ 10-09：补 segment_list（保留 songs）
    if not d9.get("segment_list"):
        d9["segment_list"] = [{"no": s["no"], "song": s["song"], "by": s["by"],
                               "songs": s["songs"], **({"songs_by": s["songs_by"]}
                                                       if s.get("songs_by") else {})}
                              for s in segs]
        d9["segment_list_source"] = ("原始材料\\沉响与长歌_20261009_歌单与现场链接.md 第10–30行 19 段表"
                                     "（自带「演唱」列）；与 10-10 segment_list 字段名统一（by）")
        d9["songs_note"] = ("`songs` 为**平铺全场曲目**（保留原字段，下游可能仍在读）；"
                            "逐曲归属看 `segment_list[].by` 与 data\\performance_attribution.json")
    if "performer" not in json.dumps(d9)[:200]:
        d9["attribution"] = {"exclude_for_subject": attr9.get("exclude_for_subject", []),
                             "pending": attr9.get("pending", []),
                             "keep": attr9.get("keep", {}),
                             "config": "data/performance_attribution.json"}

    # ④ 10-10：segment_list 逐段补 performer
    for s in d10.get("segment_list", []):
        s.setdefault("performer", s.get("by"))
    d10["attribution"] = {"added_compared_to_first_show": d10.get("delta_vs_first_show", {})
                          .get("added_compared_to_first_show", []),
                          "config": "data/performance_attribution.json"}

    if a.apply:
        if not BACKUP.exists():
            shutil.copy2(XLSX, BACKUP)
            print("[备份]", BACKUP)
        else:
            print("[备份] 已存在：", BACKUP)
        wb.save(XLSX)
        SL9.write_text(json.dumps(d9, ensure_ascii=False, indent=1), encoding="utf-8")
        SL10.write_text(json.dumps(d10, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[写入] xlsx / 2026-10-09_北京.json / 2026-10-10_北京.json")
    else:
        print("\n（试算，未写盘；加 --apply 落地）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
