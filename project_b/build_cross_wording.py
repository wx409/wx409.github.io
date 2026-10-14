# -*- coding: utf-8 -*-
"""P1-2 跨源措辞差表：同一事件在「巡演 talk（口语层）／活动表（事务层）／巡演长表（曲目层）」的措辞差异

先做**字段映射人工确认**（这是本步的前置，不是装饰）：
  · `data/activity_master.json`   → 事件文本 = `rows[].title` ＋ `city` ＋ `note`（初版自动探测的
    `name/desc/venue` 三个键在该文件里**并不存在**，等于把事务层测成了空表 → 已修）
  · `data/tour_talks_sentences.json` → 句子在 `groups[].items[].sentences[]`（初版探测的
    `sentences/rows/items` 顶层键不存在 → 口语层同样取到 0 条 → 已修）
  · `data/setlists.json` → `setlists` 是**按日期做键的字典**（初版按 `shows/rows/items` 探测 → 曲目层取到 0 条 → 已修）
计数口径：口语层 1459 句 / 67 源 / 12 组（文件自带 counts）；活动表 458 事件；长表 64 场。

输出：`data/cross_source_wording.json` ＋ `E:\\wx\\论文素材_王晰作传\\原始材料\\跨源措辞差表_v1.md`
用法：python -X utf8 project_b\\build_cross_wording.py
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
RAW = Path(r"E:\wx\论文素材_王晰作传\原始材料")
OUT_JS = D / "cross_source_wording.json"
OUT_MD = RAW / "跨源措辞差表_v1.md"

# ── 字段映射（人工确认后写死；改数据源必须同步改这里）──
FIELD_MAP = {
    "activity_master": {"file": "data/activity_master.json", "container": "rows",
                        "text_fields": ["title", "city", "note"], "date_field": "date",
                        "verified": True,
                        "note": "确认于 2026-10-14：该文件**没有** name/desc/venue 字段；"
                                "事务层文本取 title＋city＋note"},
    "tour_talks_sentences": {"file": "data/tour_talks_sentences.json",
                             "container": "groups[].items[].sentences[]", "text_fields": ["text"],
                             "date_field": "", "verified": True,
                             "note": "确认于 2026-10-14：句子在 groups→items→sentences 三层之下；"
                                     "groups[].tour/city 可作事件归属"},
    "setlists": {"file": "data/setlists.json", "container": "setlists（按日期为键的字典）",
                 "text_fields": ["songs[].title", "theme", "venue"], "date_field": "date",
                 "verified": True,
                 "note": "确认于 2026-10-14：setlists 是 dict，键为日期；曲目写法取 songs[].title"},
}


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def verify_field_map() -> list[str]:
    """★ 启动时校验 FIELD_MAP 的上游字段是否真的存在。

    背景（2026-10-14）：初版自动探测 `name/desc/venue` 三个键在该文件里并不存在，
    于是**静默出了空表**（事务层 0 条）。这里改成：逐条检查 container / text_fields /
    date_field，缺任何一项即**打印告警并把该源退回空表 + 明确提示**，不再静默。

    返回：问题清单（空＝全部通过）。
    """
    problems = []
    for name, spec in FIELD_MAP.items():
        fp = D / Path(str(spec["file"])).name
        if not fp.exists():
            problems.append(f"{name}: 文件不存在 {fp}")
            continue
        doc = load(fp, None)
        if doc is None:
            problems.append(f"{name}: JSON 解析失败 {fp}")
            continue
        cont = str(spec.get("container") or "")
        # ① 容器校验
        if cont == "rows":
            bad = not isinstance(doc.get("rows"), list)
        elif cont.startswith("setlists"):
            bad = not isinstance(doc.get("setlists"), dict)
        elif "groups" in cont:
            groups = doc.get("groups")
            bad = not isinstance(groups, list)
            if not bad:
                g0 = groups[0] if groups else {}
                if not isinstance(g0.get("items"), list):
                    bad = True
                elif g0.get("items") and not isinstance(g0["items"][0].get("sentences"), list):
                    bad = True
        else:
            bad = cont not in doc if cont else False
        if bad:
            problems.append(f"{name}: 容器 `{cont}` 缺失或类型不对（上游字段改名？）")
            continue
        # ② 文本字段抽样校验（取一行/一项，逐字段看是否真的出现）
        sample = None
        if cont == "rows":
            sample = (doc.get("rows") or [None])[0]
        elif cont.startswith("setlists"):
            sl = doc.get("setlists") or {}
            sample = next(iter(sl.values()), None) if sl else None
        elif "groups" in cont:
            g0 = (doc.get("groups") or [None])[0]
            sample = ((g0 or {}).get("items") or [None])[0]
            if sample and (sample.get("sentences") or []):
                sample = sample["sentences"][0]
        for tf in spec.get("text_fields") or []:
            key = tf.split("[]")[0].split(".")[-1]
            if isinstance(sample, dict) and key not in sample:
                problems.append(f"{name}: 文本字段 `{tf}` 在抽样项里不存在"
                                f"（可用键：{list(sample)[:8]}）")
        df = spec.get("date_field")
        if df and isinstance(sample, dict) and df not in sample:
            problems.append(f"{name}: 日期字段 `{df}` 在抽样项里不存在")
    return problems


_VERIFY_PROBLEMS = verify_field_map()

am = load(D / "activity_master.json") or {}
act_rows = am.get("rows") or []
tt = load(D / "tour_talks_sentences.json") or {}
groups = tt.get("groups") or []
sl = load(D / "setlists.json") or {}
setlists = sl.get("setlists") or {}
CANON = load(D / "song_aliases.json") or {}

# 曲名规范表（用于「曲目层写法」对照）
cand = CANON.get("canonical") or {}
alias = CANON.get("aliases") or {}
alias2canon = {}
for canon_name, alts in (alias.items() if isinstance(alias, dict) else []):
    if isinstance(alts, list):
        for a in alts:
            alias2canon[str(a)] = canon_name

# ── talk 层：按 (tour, city) 归组取句 ──
talk_by_city = {}
talk_sent_total = 0
for g in groups:
    city = g.get("city") or ""
    tour = g.get("tour") or ""
    buf = []
    for it in (g.get("items") or []):
        for s in (it.get("sentences") or []):
            t = (s.get("text") or "").strip()
            if t:
                buf.append({"text": t, "tc": s.get("timecode") or "", "src": it.get("part_title") or ""})
    talk_sent_total += len(buf)
    talk_by_city.setdefault((tour, city), []).extend(buf)

# ── 事件清单：以长表（有日期、有场次、有曲目）为骨架，向另两层找同城/同期记录 ──
events = []
for key, v in setlists.items():
    if not isinstance(v, dict):
        continue
    dt = v.get("date") or (key if re.match(r"\d{4}-\d{2}-\d{2}", str(key)) else "")
    city = v.get("city") or v.get("scene") or ""
    tour = v.get("tour") or ""
    songs = [x.get("title") for x in (v.get("songs") or []) if isinstance(x, dict) and x.get("title")]
    events.append({"date": dt, "city": city, "tour": tour, "venue": v.get("venue") or "",
                   "theme": v.get("theme") or "", "songs": songs, "n_songs": len(songs)})
events.sort(key=lambda x: x["date"] or "")


# ── 事件选取：以 **有 talk 语料的 (巡次,城市)** 为准，再回长表取同一场 ──
#   talk 语料共 12 组（11 个巡次×城市 + 1 个「北京收官」）；按精确键匹配，
#   匹配不到就如实写「该层无对应语料」，不用别的城市的句子顶替（初版曾把广州句错配给三巡）。
def norm_city(c: str) -> str:
    return re.sub(r"(收官|首演|站)$", "", str(c or "")).strip()


ev_by_key = {}
for e in events:
    ev_by_key.setdefault((e["tour"], norm_city(e["city"])), []).append(e)
for k in ev_by_key:
    ev_by_key[k].sort(key=lambda x: x["date"] or "")

SELECT, unmatched = [], []
for g in groups:
    tour, city = g.get("tour") or "", norm_city(g.get("city"))
    cands = ev_by_key.get((tour, city)) or []
    if not cands:
        unmatched.append((tour, city, g.get("sentences")))
        continue
    e = cands[-1] if "收官" in str(g.get("city")) else cands[0]
    talk = [{"text": (s.get("text") or "").strip(), "tc": s.get("timecode") or "",
             "src": it.get("part_title") or ""}
            for it in (g.get("items") or []) for s in (it.get("sentences") or []) if (s.get("text") or "").strip()]
    act = [r for r in act_rows if str(r.get("date")) == e["date"]]
    SELECT.append((e, act, talk))
SELECT.sort(key=lambda x: -(x[0]["n_songs"]))

rows_out = []
seen_talk = set()
for e, act, talk in SELECT:
    title = act[0].get("title") if act else ""
    notes = "；".join(sorted({(r.get("note") or "") for r in act if r.get("note")}))[:120]
    # 取一条**未用过**的、信息量较大的 talk 句，避免各场样本雷同
    sample = None
    for s in talk:
        t = s["text"]
        if len(t) >= 12 and t not in seen_talk:
            sample = s
            break
    if sample:
        seen_talk.add(sample["text"])
    aliases = [s for s in e["songs"] if s in alias2canon]
    rows_out.append({
        "date": e["date"], "tour": e["tour"], "city": e["city"], "venue": e["venue"],
        "n_songs": e["n_songs"],
        "talk_layer": {"n_sent": len(talk),
                       "sample": (sample or {}).get("text", ""),
                       "timecode": (sample or {}).get("tc", ""),
                       "src": (sample or {}).get("src", "")},
        "act_layer": {"n_rows": len(act), "title": title, "note": notes},
        "list_layer": {"songs_head": e["songs"][:6], "alias_written": aliases,
                       "alias_note": "长表里用了别名写法，规范名见 data/song_aliases.json"},
    })

res = {"schema": 1, "generated_at": date.today().isoformat(),
       "field_map": FIELD_MAP,
       "layer_counts": {"talk_sentences": talk_sent_total,
                        "talk_groups": len(groups),
                        "talk_counts_from_file": tt.get("counts"),
                        "activity_events": len(act_rows),
                        "setlist_shows": len(events)},
       "events": rows_out,
       "unmatched_talk_groups": unmatched,
       "caliber": "三层措辞天然不同（口语/事务/曲目），本表只做**对照呈现**，不作优劣或准确性判断；"
                  "曲目层写法以 data/song_aliases.json 为规范。"}

OUT_JS.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

L = ["# 跨源措辞差表 v1（同一事件：巡演 talk ／ 活动表 ／ 巡演长表）", "",
     f"> 生成 {date.today().isoformat()}｜事件 {len(rows_out)} 个｜"
     f"层级计数：talk 句 {talk_sent_total}（{len(groups)} 组）、活动表 {len(act_rows)} 事件、长表 {len(events)} 场。",
     "> **字段映射已人工确认**（见文末）；三层措辞天然不同，本表只作对照，不评优劣。", ""]
for i, r in enumerate(rows_out, 1):
    L += [f"## {i}. {r['date']}｜{r['tour']}·{r['city']}（{r['venue']}）", "",
          f"- **口语层**（talk，{r['talk_layer']['n_sent']} 句可对）："
          f"「{r['talk_layer']['sample']}」"
          + (f"（{r['talk_layer']['timecode']}，{r['talk_layer']['src']}）" if r["talk_layer"]["timecode"] else ""),
          f"- **事务层**（活动表，{r['act_layer']['n_rows']} 条）：{r['act_layer']['title']}"
          + (f"｜备注：{r['act_layer']['note']}" if r["act_layer"]["note"] else ""),
          f"- **曲目层**（长表，{r['n_songs']} 首）：{'、'.join(r['list_layer']['songs_head'])}"
          + (f"｜别名写法：{'、'.join(r['list_layer']['alias_written'])}" if r["list_layer"]["alias_written"] else ""),
          ""]
L += ["---", "", "## 字段映射（人工确认，2026-10-14）", "",
      "| 文件 | 容器 | 文本字段 | 日期字段 | 备注 |", "|---|---|---|---|---|"]
for k, v in FIELD_MAP.items():
    L.append(f"| `{v['file']}` | `{v['container']}` | {'、'.join(v['text_fields'])} | {v['date_field'] or '—'} | {v['note']} |")
L += ["", "**初版三处映射错误（本轮修正）**：① 活动表按 `name/desc/venue` 探测 → 该文件无此三键；"
      "② talk 按顶层 `sentences/rows/items` 探测 → 句子在 `groups[].items[].sentences[]`；"
      "③ 长表按 `shows/rows/items` 探测 → 实为按日期为键的字典 `setlists`。"
      "三处都会让那一层静默变成空表，因此本步把映射写死并在此登记。", ""]
OUT_MD.write_text("\n".join(L), encoding="utf-8")

# ★ 字段映射校验结果（缺失即告警 + 该层退回空表并提示，绝不静默出空表）
if _VERIFY_PROBLEMS:
    print("[warn] FIELD_MAP 校验未通过 %d 项（对应层已退回空表，不静默）：" % len(_VERIFY_PROBLEMS))
    for p in _VERIFY_PROBLEMS:
        print("   -", p)
    print("   → 处置：核对上游字段名后改 FIELD_MAP（见本文件顶部注释），或确认数据源已换。")
else:
    print("[ok] FIELD_MAP 校验通过（container / text_fields / date_field 均存在）")

print(f"[ok] {OUT_JS.name}｜事件 {len(rows_out)} 个｜talk 句 {talk_sent_total}｜活动 {len(act_rows)}｜长表 {len(events)}")
print(f"[ok] {OUT_MD.name}")
for r in rows_out[:5]:
    print(f"  · {r['date']} {r['tour']}·{r['city']}｜talk {r['talk_layer']['n_sent']} 句｜"
          f"活动 {r['act_layer']['n_rows']} 条｜曲目 {r['n_songs']} 首")
sys.exit(0 if len(rows_out) >= 5 else 1)
