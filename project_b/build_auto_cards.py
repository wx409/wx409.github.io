# -*- coding: utf-8 -*-
"""定期上线的**自动卡**：每周发现卡 + 演出后自燃卡（复用卡片厂模板与 caliber-lock）。

设计原则（防"硬凑"）：
  · **未达条件就不出卡**，并打印原因；不生成空卡、不占位。
  · 两张卡都用**稳定 id**（weekly_findings / selfignite_latest）→ 每周/每次触发是覆盖而非堆积，
    历史版本由 git 保留；share.html 与 sitemap 通过现有卡片厂自动收录。
  · `review_status` 决定上站层级：auto → 落 `share-<id>.html`（模板自带 noindex,follow）且不进主导航。

数据源（全部可选，缺则降级）：
  data/asset_streams.json                本周增量（streams[].new_7d）
  data/propagation_digest.json           传播监测摘要（优先）
  temp/propagation_digest_light.json     轻量巡逻摘要（次选）
  data/propagation_watch.json            阈值（thresholds）
  E:\\wx\\...\\传播监测\\每日巡逻_*.json / 定向窗_*.json   兜底

用法：
  python -X utf8 project_b\\build_auto_cards.py             # 两张都跑（各自判条件）
  python -X utf8 project_b\\build_auto_cards.py --weekly
  python -X utf8 project_b\\build_auto_cards.py --selfignite --dry
"""
from __future__ import annotations
import argparse
import glob
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
SITE = Path(__file__).resolve().parent.parent
D = SITE / "data"
SH = D / "share"
CARDS = SH / "cards"
RENDER = SH / "rendered"
ARCH = Path(r"E:\wx\论文素材_王晰作传\传播监测")
TODAY = date.today()
EXPERIENTIAL = "经验性认知（非官方）"

sys.path.insert(0, str(SITE / "project_b"))
from build_topic_cards import render_card, plat_templates  # noqa: E402


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def newest(pattern: str):
    fs = sorted(glob.glob(str(pattern)))
    return Path(fs[-1]) if fs else None


def emit(card: dict, dry: bool) -> None:
    card = {**card, "generated_at": TODAY.isoformat()}
    if not dry:
        CARDS.mkdir(parents=True, exist_ok=True)
        RENDER.mkdir(parents=True, exist_ok=True)
        (CARDS / f"card_{card['id']}.json").write_text(
            json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
        (RENDER / f"card_{card['id']}.html").write_text(render_card(card), encoding="utf-8")
    print(f"[出卡] {card['id']}｜{card['title']}｜主数字 {len(card['main_numbers'])}"
          f"｜caliber-lock {len(card['caliber_lock'])}" + ("（dry-run 未写盘）" if dry else ""))


# ───────────────────────── ① 每周发现卡 ─────────────────────────
def build_weekly(dry: bool) -> bool:
    streams = (load(D / "asset_streams.json", {}) or {}).get("streams") or []
    inc = []
    for s in streams:
        n = s.get("new_7d")
        if isinstance(n, int) and n > 0:
            inc.append((s.get("stream"), n, s.get("source"), s.get("latest")))
    inc.sort(key=lambda x: -x[1])
    total = sum(x[1] for x in inc)

    digest = load(D / "propagation_digest.json") or load(SITE / "temp" / "propagation_digest_light.json", {}) or {}
    prop_note = ""
    if digest:
        r2 = digest.get("rule2") or {}
        prop_note = (f"传播监测（{digest.get('generated_at', '—')[:16]}）：帖中位 "
                     f"{((r2.get('posts') or {}).get('median'))}、评论中位 "
                     f"{((r2.get('comments') or {}).get('median'))}；"
                     f"突增判定 {'命中' if ((r2.get('posts') or {}).get('triggered')) else '未命中'}")

    if total <= 0 and not prop_note:
        print("[不出卡] 本周增量 0 且无传播监测材料 → 不生成「本周发现」卡（不硬凑）")
        return False

    iso = TODAY.isocalendar()
    week = f"{iso[0]}-W{iso[1]:02d}"
    span = f"{(TODAY - timedelta(days=7)).isoformat()} ~ {TODAY.isoformat()}"
    main = [{"value": total, "unit": "条", "label": "本周新增记录合计（各素材流 new_7d 求和）",
             "caliber": "weekly_increment", "source": "data/asset_streams.json"}]
    for name, n, src, latest in inc[:3]:
        main.append({"value": n, "unit": "条", "label": f"{name}（最新 {latest or '—'}）",
                     "caliber": "weekly_increment", "source": src or "data/asset_streams.json"})
    reading = [
        f"统计窗：{span}（ISO 周 {week}）；口径 = 各素材流 `new_7d` 之和，逐流列出以便复核。",
        "有增量才出卡：本周合计为 0 时本卡不生成（避免「每周一张空卡」）。",
    ]
    if inc:
        reading.append("增量构成：" + "；".join(f"{a} {b} 条" for a, b, _s, _l in inc) + "。")
    if prop_note:
        reading.append(prop_note + f"（平台机制表述为{EXPERIENTIAL}）")
    card = dict(
        id="weekly_findings", no=8, title="本周发现", subtitle=f"素材增量速报（{span}）",
        pillar="事实（数据流派生）", review_status="auto", page_layer="share-<id>.html（noindex,follow，不进主导航）",
        main_numbers=main, view_reading=reading,
        view_card=[f"{total} 条", week] + [f"{a} {b}" for a, b, _s, _l in inc[:2]],
        caliber_lock=[{"label": "口径", "value": "new_7d（各流自报）",
                       "why": "不同素材流的计量单位不同（条/天/个），**不跨流相加解读为「总产出」**，只作增量提示"}],
        gate={"pass_status": ["数据流派生"], "note": "非声学卡，不适用稳定音门槛"},
        platform=plat_templates("本周发现", f"素材增量 {total} 条", f"统计窗 {span}（ISO 周 {week}）",
                                "想看逐流明细？看站内素材积攒看板"),
        footnote=(f"口径：各素材流 new_7d 之和；数据源 data/asset_streams.json"
                  f"（+ 传播监测摘要）；生成 {TODAY.isoformat()}｜未达增量不出卡"),
    )
    emit(card, dry)
    return True


# ───────────────────────── ② 演出后自燃卡 ─────────────────────────
def build_selfignite(dry: bool) -> bool:
    cfg = load(D / "propagation_watch.json", {}) or {}
    th = cfg.get("thresholds") or {}
    src = (load(D / "propagation_digest.json") if (D / "propagation_digest.json").exists()
           else load(SITE / "temp" / "propagation_digest_light.json"))
    src_path = "data/propagation_digest.json" if (D / "propagation_digest.json").exists() \
        else "temp/propagation_digest_light.json"
    if not src:
        p = newest(ARCH / "每日巡逻_*.json")
        if p:
            src, src_path = load(p, {}) or {}, str(p)
    if not src:
        print("[不出卡] 找不到传播监测产物（digest / 每日巡逻）→ 跳过自燃卡")
        return False

    r2 = src.get("rule2") or {}
    wp = src.get("window_probe") or {}
    posts_t = bool((r2.get("posts") or {}).get("triggered"))
    comm_t = bool((r2.get("comments") or {}).get("triggered"))
    cluster_n = int(wp.get("max_per_30min_sliding") or 0)
    need = int(th.get("cluster_n_in_hours", 5))
    cluster_ok = cluster_n >= need
    hit = posts_t or comm_t or cluster_ok
    if not hit:
        print(f"[不出卡] 自燃阈值未命中（帖突增 {posts_t}／评论突增 {comm_t}／"
              f"30 分钟滑动峰值 {cluster_n} < {need}）→ 不生成自燃卡")
        return False

    d = newest(ARCH / "定向窗_*.json")
    wins = load(d, {}) if d else {}
    sp = load(SH / "woyaoni_spread.json", {}) or {}
    peak = (sp.get("first_peak") or {})
    main = [
        {"value": (r2.get("posts") or {}).get("median"), "unit": "赞", "label": "帖点赞中位（判定基数）",
         "caliber": "propagation_spike", "source": src_path},
        {"value": (r2.get("posts") or {}).get("threshold"), "unit": "赞",
         "label": "突增阈值（中位×%s）" % th.get("hot_ratio_vs_median", 3.0),
         "caliber": "propagation_spike", "source": src_path},
        {"value": cluster_n, "unit": "条", "label": f"30 分钟滑动峰值（簇状门槛 {need}）",
         "caliber": "propagation_cluster", "source": src_path},
    ]
    if peak.get("likes"):
        main.append({"value": peak["likes"], "unit": "赞",
                     "label": f"最高单条（{peak.get('datetime', '—')}）",
                     "caliber": "propagation_spike", "source": "data/share/woyaoni_spread.json"})
    reading = [
        f"触发源：{src_path}（{str(src.get('generated_at', '—'))[:16]}）；"
        f"阈值取自 data/propagation_watch.json#thresholds。",
        f"命中项：帖突增 {'是' if posts_t else '否'}、评论突增 {'是' if comm_t else '否'}、"
        f"簇状（30 分钟滑动峰值 {cluster_n} ≥ {need}）{'是' if cluster_ok else '否'}。",
    ]
    if wins:
        reading.append(f"定向窗 {wins.get('window', '—')}：窗内 {wins.get('n_in_window')} 条"
                       f"（帖 {wins.get('n_post')} / 评论 {wins.get('n_comment')}）；"
                       f"窗内突增 {len(wins.get('spikes_in_window') or [])} 条。")
    if sp.get("notes"):
        reading.append(f"同场次样本：{sp['notes']} 条笔记 / {sp['likes_total']} 赞 / "
                       f"{sp['comments_grabbed']} 条评论；{sp['pct_same_day_or_next']}% 集中在演出当日或次晚。")
    card = dict(
        id="selfignite_latest", no=9, title="自燃信号", subtitle="演出后传播突增/簇状触发（阈值命中才出卡）",
        pillar="事实（阈值触发）", review_status="auto", page_status="auto",
        page_layer="share-<id>.html（noindex,follow，不进主导航）",
        main_numbers=main, view_reading=reading,
        view_card=[f"帖中位 {(r2.get('posts') or {}).get('median')} 赞",
                   f"阈值 {(r2.get('posts') or {}).get('threshold')} 赞",
                   f"滑动峰值 {cluster_n} 条"],
        caliber_lock=[
            {"label": "平台侧", "value": "无曝光/推荐/榜单数据",
             "why": f"平台机制一律 {EXPERIENTIAL}；禁用三类平台侧夸张断言（见 data/share/battlemap.json）"},
            {"label": "样本", "value": "本机可检索到的公开 UGC",
             "why": "样本无法证实平台侧热度；「未命中」也不等于「没有热点」"},
        ],
        gate={"pass_status": ["阈值触发（规则判定）"],
              "note": f"阈值：簇状 6 小时内 ≥{need} 条 / 单条突增 ≥中位×{th.get('hot_ratio_vs_median', 3.0)}"},
        platform=plat_templates("自燃信号", "阈值命中的传播突增",
                                f"帖点赞中位 {(r2.get('posts') or {}).get('median')}、阈值 "
                                f"{(r2.get('posts') or {}).get('threshold')}", "想看判定细节？看站内传播监测口径"),
        footnote=(f"口径：规则判定（data/propagation_watch.json#thresholds）；触发源 {src_path}；"
                  f"生成 {TODAY.isoformat()}｜阈值未命中不出卡"),
    )
    emit(card, dry)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weekly", action="store_true")
    ap.add_argument("--selfignite", action="store_true")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    do_w = a.weekly or not (a.weekly or a.selfignite)
    do_s = a.selfignite or not (a.weekly or a.selfignite)
    ok = 0
    if do_w:
        ok += 1 if build_weekly(a.dry) else 0
    if do_s:
        ok += 1 if build_selfignite(a.dry) else 0
    print(f"[done] 出卡 {ok} 张（未达条件的不出卡；出卡后请跑 build_share_page.py 生成页面）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
