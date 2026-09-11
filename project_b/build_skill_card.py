# -*- coding: utf-8 -*-
"""每日「唱功卡片」生成器 —— 从已实测数据池按日期确定性轮转，每天不同、全部本地留存。

纪律：
  · 只从已落盘的实测数据派生（音域/现场/舞台/巡演×专辑），无数据支撑的维度不硬写；
  · 卡片文案不含指数数值（指数太低，不用来论证唱功）；
  · 遗留禁用词（华语最低/唯一/第一/声学指纹/生物指纹/机械级音准）一律不出现在文案里；
  · 轮转确定性：同一天多次运行结果完全一致（按日期序数取模），不依赖随机数。

输入（站点 data/）：
  archive_vocal_albums.json  72 曲录音室全量
  archive_vocal.json         10 曲精测 + B1 复现 + 录音室/现场对照 + 权威背书
  archive_stage.json         他人主导舞台 32 素材
  archive_stage_tour.json    王晰主导巡演现场（本日新增层）
  data/albums.json           专辑发行（年月）

输出：
  D:\\wx409.github.io\\data\\skill_cards.json            站点数据（today + 历史，append-only）
  E:\\wx\\论文素材_王晰作传\\传记素材\\唱功卡片\\<日期>.md   本地传记素材归档（含社交短文案）

用法：
  python -X utf8 project_b/build_skill_card.py            # 生成/补齐今天
  python -X utf8 project_b/build_skill_card.py --date 2026-09-01   # 回填历史某天
  python -X utf8 project_b/build_skill_card.py --rebuild-history --days 14  # 回填最近 N 天
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT_JSON = DATA / "skill_cards.json"
BIO = Path(r"E:\wx\论文素材_王晰作传\传记素材\唱功卡片")

MEDIAN_HUMAN_LOW = 82.4          # 一般男低音下限 E2（对照用，非结论）
BANNED = ("华语最低", "唯一", "第一", "声学指纹", "生物指纹", "机械级音准", "旧口径", "已作废")


def load(rel, default=None):
    try:
        return json.loads((ROOT / rel).read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def clean(text: str) -> str:
    for b in BANNED:
        text = text.replace(b, "")
    return text


def fmt(v, nd=1):
    return "—" if v is None else f"{v:.{nd}f}"


def hz_note(note, hz):
    return f"{note}（{fmt(hz, 1)} Hz）"


def build_pool() -> list[dict]:
    """构造卡片池：每条 {key, topic, title, lines[], source, caliber, social[]}"""
    pool: list[dict] = []
    alb = load("data/archive_vocal_albums.json")
    albs = load("data/albums.json")
    voc = load("data/archive_vocal.json")
    stg = load("data/archive_stage.json")
    tour = load("data/archive_stage_tour.json")

    # ① 录音室专辑：逐曲最低稳定音（72 曲 → 每天换一首）
    for s in (alb.get("songs") or []):
        if not s.get("low_hz"):
            continue
        gap = s["low_hz"] - MEDIAN_HUMAN_LOW
        rel = "低" if gap < 0 else "高"
        pool.append({
            "key": f"album:{s.get('album')}|{s.get('title')}",
            "topic": "录音室低音",
            "title": f"《{s.get('title')}》的最低稳定音 {s.get('low')}",
            "lines": [
                f"音高 **{hz_note(s.get('low'), s.get('low_hz'))}**，比一般男低音下限 E2（82.4 Hz）{rel} {fmt(abs(gap),1)} Hz。",
                f"该曲音域跨度 **{fmt(s.get('span_octaves'),2)} 个八度**，音符内稳定性中位 **{fmt(s.get('stability_cents'),1)} 音分**"
                + (f"，颤音 **{fmt(s.get('vibrato_hz'),2)} Hz / {fmt(s.get('vibrato_cents'),0)} 音分**" if s.get("vibrato_hz") else "") + "。",
                f"出处：录音室专辑《{s.get('album')}》（{fmt_album_year(albs, s.get('album'))}），QQ音乐 320k 音源，人声分离 + 逐帧 F0 实测。",
            ],
            "source": f"data/archive_vocal_albums.json#{s.get('album')}/{s.get('title')}",
            "caliber": "最低稳定音：音符本身 ≥0.2s、HNR ≥5dB、强度 ≥中位−25dB；单帧/瞬时读数不作依据。",
            "social": [
                f"《{s.get('title')}》——最低稳定音 {s.get('low')}，比男低音的常规下限还低 {fmt(abs(gap),1)} Hz。",
                "低音不是音量的比拼，是控制力的比拼：长音稳不稳，听一秒就知道。",
            ],
        })

    # ② 十曲精测：颤音 / 稳定性特征
    for s in (voc.get("songs") or []):
        if not s.get("stable_hz"):
            continue
        lines = [f"稳定音 **{hz_note(s.get('stable_note'), s.get('stable_hz'))}**"
                 + (f"，该音持续 {fmt(s.get('stable_dur_s'),2)} s、HNR {fmt(s.get('stable_hnr_db'),1)} dB。" if s.get("stable_dur_s") else "。")]
        if s.get("vibrato_rate_hz_median"):
            lines.append(f"颤音速率 **{fmt(s.get('vibrato_rate_hz_median'),2)} Hz**、幅度 **{fmt(s.get('vibrato_extent_cents_median'),0)} 音分**"
                         "（专业常见区间 4.5–6.5 Hz / 50–100 音分）。")
        if s.get("stability_cents_median") is not None:
            lines.append(f"音符内稳定性中位 **{fmt(s.get('stability_cents_median'),1)} 音分**（越小越稳）。")
        lines.append(f"出处：{s.get('source') or '录音室实测'}，逐帧 F0 落盘可复核。")
        pool.append({
            "key": f"vocal:{s.get('name')}",
            "topic": "控制力",
            "title": f"《{s.get('name')}》：一个音的稳定性",
            "lines": lines,
            "source": "data/archive_vocal.json",
            "caliber": "十曲精测口径；颤音与稳定性为逐音符统计中位。",
            "social": [
                f"一个音能站住多久、抖多少，比唱多高更能说明问题——《{s.get('name')}》的答案在数据里。",
                "稳，是低音歌手最贵的天赋。",
            ],
        })

    # ③ 巡演现场（能力层）
    for r in (tour.get("rows") or []):
        if not r.get("low_hz"):
            continue
        pool.append({
            "key": f"tour:{r.get('tag')}",
            "topic": "巡演现场",
            "title": f"{r.get('tour')}{r.get('city')}现场《{r.get('song')}》最低稳定音 {r.get('low_note')}",
            "lines": [
                f"现场实测最低稳定音 **{hz_note(r.get('low_note'), r.get('low_hz'))}**（{r.get('date')}）。",
                f"复核状态 **{r.get('a3_final_note')}**"
                + (f"（YIN {fmt(r.get('a3_yin_hz'),1)} Hz ↔ CREPE {fmt(r.get('a3_crepe_hz'),1)} Hz）" if r.get("a3_crepe_hz") else "") + "。",
                f"同场跨度 **{fmt(r.get('span_octaves'),2)} 个八度**，稳定性中位 {fmt(r.get('stability_cents'),1)} 音分，"
                f"颤音 {fmt(r.get('vibrato_hz'),2)} Hz。出处：B站 {r.get('bv')}（{r.get('source_verdict') or '来源见台账'}）。",
            ],
            "source": "data/archive_stage_tour.json",
            "caliber": "他本人主导的巡演现场；最低稳定音口径，待复核读数只列不判。",
            "social": [
                f"{r.get('city')}现场，{r.get('song')}唱到 {r.get('low_note')}——现场的调，是他自己定的。",
                "现场和录音室的差别，不在能不能，而在敢不敢。",
            ],
        })

    # ④ 他人主导舞台（对照层）
    for x in (stg.get("items") or []):
        if not x.get("low_hz"):
            continue
        # 舞台条目只有 B站标题，没有独立曲名字段 → 从《…》里取曲名，取不到就按时长/分类描述
        _m = re.search(r"《([^》]{1,24})》", str(x.get("title") or ""))
        _label = clean(_m.group(1)) if _m else ""
        _名 = f"《{_label}》" if _label else f"（{x.get('cat')}素材）"
        pool.append({
            "key": f"stage:{x.get('bvid')}",
            "topic": "舞台对照",
            "title": f"他人主导舞台{_名}的音域读数",
            "lines": [
                f"分类：{x.get('cat')}；最低稳定音 **{hz_note(x.get('low'), x.get('low_hz'))}**，最高 {hz_note(x.get('high'), x.get('high_hz'))}。",
                f"跨度 **{fmt(x.get('span'),2)} 个八度**，稳定性 {fmt(x.get('stability'),1)} 音分，密度 {fmt(x.get('density'),2)}/s。",
                "这一层由节目组选曲、电视混音与伴唱叠加共同决定，只作互证，不作现场能力上限。",
            ],
            "source": "data/archive_stage.json",
            "caliber": "他人主导舞台统一口径；最高音含和声层风险，需听辨。",
            "social": [
                f"同一副嗓子，在不同的舞台上会呈现完全不同的声学画像——{x.get('cat')}{_名}就是一例。",
                "舞台是别人的调，专辑是自己的调。",
            ],
        })

    # ⑤ B1 复现
    for b in (voc.get("b1_reproduction") or []):
        pool.append({
            "key": f"b1:{b.get('version')}",
            "topic": "B1 复现",
            "title": f"{b.get('version')}：B1 级低音的实测读数",
            "lines": [
                f"实测 **{hz_note(b.get('note'), b.get('hz'))}**，出现位置 {fmt(b.get('time_s'),1)} s。",
                f"来源 {b.get('source')}，可信度 **{b.get('trust')}**。{b.get('note_text') or ''}",
            ],
            "source": "data/archive_vocal.json#b1_reproduction",
            "caliber": "同一测量管线；可信度分级见站点音域实测页。",
            "social": [
                f"B1，{b.get('note')}——低音歌手的分水岭，他在{b.get('version')}里唱出来了。",
                "低音的尽头不是更低，是更稳。",
            ],
        })

    # ⑥ 巡演 × 专辑：每巡唱的是什么
    for a in (tour.get("album_tour_sync") or []):
        if a.get("shows") is None:
            continue
        sm = "（同月发行·口径待核）" if a.get("album_same_month") else ""
        pool.append({
            "key": f"toursync:{a.get('tour')}",
            "topic": "巡演结构",
            "title": f"{a.get('tour')}「{a.get('theme')}」：巡演与专辑的关系",
            "lines": [
                f"该巡前最近发行专辑《{a.get('album')}》（{a.get('album_ym')}）{sm}，其曲目进歌单 **{a.get('album_songs_in_setlist')}/{a.get('album_songs_total')}（{a.get('coverage_pct')}%）**。",
                f"同时，该巡曲目中 **{a.get('earlier_tour_songs')} 首（{a.get('earlier_tour_share_pct')}%）**来自更早巡次。",
                f"场次 {a.get('shows')} 场（{a.get('date_range', ['', ''])[0]}~{a.get('date_range', ['', ''])[1]}），口径源：全站 64 场歌单单一事实源。",
            ],
            "source": "data/archive_stage_tour.json#album_tour_sync + data/setlists.json",
            "caliber": "专辑覆盖率为精确曲名匹配；专辑发行日期为年月精度，同月条目已标注待核。",
            "social": [
                f"{a.get('tour')}「{a.get('theme')}」巡演：{a.get('coverage_pct')}% 唱的是新专辑，{a.get('earlier_tour_share_pct')}% 是回望旧巡。",
                "巡演不是复读机，是每一轮的自我修订。",
            ],
        })

    # ⑦ 跨情境稳定的颤音（全站结论级）
    sv = voc.get("studio_vs_live") or {}
    if sv:
        pool.append({
            "key": "trait:studio_vs_live",
            "topic": "跨情境一致",
            "title": f"《{sv.get('song')}》录音室与现场的同音级复现",
            "lines": [
                f"录音室 **{fmt(sv.get('studio_hz'),1)} Hz** ↔ 现场 **{fmt(sv.get('live_hz'),1)} Hz**（{sv.get('live_note')}）。",
                sv.get("note") or "",
            ],
            "source": "data/archive_vocal.json#studio_vs_live",
            "caliber": "同音级对照；现场素材为非官方公开音源。",
            "social": [
                f"录音室和现场，{sv.get('studio_hz')} Hz 对 {sv.get('live_hz')} Hz——这不是巧合，是肌肉记忆。",
            ],
        })
    del stg, alb
    pool = [c for c in pool if all(clean(x).strip() for x in c["lines"])]
    # 按主题轮转交错：连续几天不会都是同一类（保证"每天有惊喜"且顺序确定）
    by_topic: dict[str, list[dict]] = {}
    for c in pool:
        by_topic.setdefault(c["topic"], []).append(c)
    interleaved, i = [], 0
    while True:
        added = False
        for t, items in by_topic.items():
            if i < len(items):
                interleaved.append(items[i])
                added = True
        if not added:
            break
        i += 1
    return interleaved


def fmt_album_year(alb, name):
    for a in (alb.get("albums") or []):
        if a.get("name") == name:
            return a.get("release") or "—"
    return "—"


def render_md(card: dict, day: str) -> str:
    lines = [f"# 唱功卡片 · {day}", "", f"**{card['title']}**", "",
             f"> 主题：{card['topic']} ｜ 卡片编号 {card['index']}/{card['pool_size']}", ""]
    lines += card["lines"] + ["", f"**口径**：{card['caliber']}", f"**数据底账**：`{card['source']}`", "",
                             "## 社交短文案（可直接发）", ""]
    lines += [f"- {clean(s)}" for s in card["social"]]
    lines += ["", "---", f"生成：{card['generated_at']}｜脚本：`project_b/build_skill_card.py`", ""]
    return "\n".join(lines)


def card_for(day: date, pool: list[dict]) -> dict:
    idx = day.toordinal() % len(pool)
    c = dict(pool[idx])
    c["title"] = clean(c["title"])
    c["key"] = clean(c["key"])
    c["lines"] = [clean(x) for x in c.get("lines") or []]
    c["social"] = [clean(x) for x in c.get("social") or []]
    c["index"] = idx + 1
    c["pool_size"] = len(pool)
    c["date"] = day.isoformat()
    c["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--rebuild-history", action="store_true")
    ap.add_argument("--days", type=int, default=14)
    args = ap.parse_args()

    pool = build_pool()
    if not pool:
        print("[FAIL] 卡片池为空：实测数据缺失")
        return 1

    store = load("data/skill_cards.json", {}) or {}
    cards = {c["date"]: c for c in (store.get("cards") or []) if c.get("date")}
    # 兼容 today 单独字段
    if store.get("today", {}).get("date"):
        cards.setdefault(store["today"]["date"], store["today"])

    targets = []
    if args.rebuild_history:
        for i in range(args.days):
            targets.append(date.today() - timedelta(days=i))
    else:
        targets.append(date.fromisoformat(args.date) if args.date else date.today())

    for d in targets:
        c = card_for(d, pool)
        cards[d.isoformat()] = c
        BIO.mkdir(parents=True, exist_ok=True)
        (BIO / f"{d.isoformat()}.md").write_text(render_md(c, d.isoformat()), encoding="utf-8")

    ordered = sorted(cards.values(), key=lambda x: x["date"])
    today_card = cards.get(date.today().isoformat()) or ordered[-1]
    OUT_JSON.write_text(json.dumps({
        "schema": 1,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pool_size": len(pool),
        "policy": {
            "rotation": "按日期序数取模（确定性：同一天任意次运行结果一致）",
            "source": "只取已落盘实测数据；无数据支撑的维度不写",
            "index_policy": "卡片不使用音乐指数数值",
            "archive": "全部卡片留存本地传记素材目录，站点仅展示今日与近期",
        },
        "today": today_card,
        "recent": ordered[-30:][::-1],
        "cards": ordered,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] 卡片池 {len(pool)} 张｜今日 #{today_card['index']}｜{today_card['title']}")
    print(f"[OK] {OUT_JSON}")
    print(f"[OK] 本地归档 {BIO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
