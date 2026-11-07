# -*- coding: utf-8 -*-
"""把两份事实包渲染成 markdown 报告（避免文档里的数字随数据漂移）。

输入：analysis/out/vocal_claims.json、analysis/out/did_stats.json、analysis/out/curve.json
输出：analysis/CLAIMS.md（自动生成，勿手改）
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
DEST = HERE / "CLAIMS.md"

METRIC_CN = {
    "low_hz": ("最低稳定音", "Hz", "{:.2f}", "越低越好；中位比单曲极值更能代表常规音区"),
    "high_hz": ("最高音", "Hz", "{:.2f}", ""),
    "span_octaves": ("音域跨度", "八度", "{:.2f}", "一首作品内最高到最低的距离"),
    "intonation_cents": ("音准偏差", "音分", "{:.2f}", "越小越准；人耳可辨阈约 10–25 音分"),
    "stability_cents": ("音高稳定度", "音分", "{:.2f}", "同曲内逐帧抖动，越小越稳"),
    "vibrato_hz": ("颤音频率", "Hz", "{:.2f}", "男低音常见 4–6 Hz"),
    "vibrato_cents": ("颤音幅度", "音分", "{:.2f}", ""),
    "hnr_db": ("谐噪比 HNR", "dB", "{:.2f}", "越高气息越干净（受分离与混音影响）"),
    "duration_s": ("有效时长", "秒", "{:.1f}", ""),
    "density_per_s": ("音符密度", "个/秒", "{:.2f}", ""),
}


def table(metrics):
    rows = ["| 维度 | 中位 | 95% CI | n | 怎么读 |", "|---|---|---|---|---|"]
    for key, (cn, unit, fmt, hint) in METRIC_CN.items():
        m = metrics.get(key)
        if not m:
            continue
        rows.append(f"| {cn} | {fmt.format(m['median'])} {unit} | "
                    f"{fmt.format(m['ci_lo'])}–{fmt.format(m['ci_hi'])} | {m['n']} | {hint} |")
    return "\n".join(rows)


def main():
    v = json.loads((OUT / "vocal_claims.json").read_text(encoding="utf-8"))
    curve = json.loads((OUT / "curve.json").read_text(encoding="utf-8"))
    sens = json.loads((OUT / "sensitivity.json").read_text(encoding="utf-8"))

    s = v["studio"]
    st = v["live"]["stability"]
    det4 = [x for x in st["detail"] if x["sessions"] >= 4]
    stable = [x for x in det4 if x["sd_semitone"] < 1]
    c = {x["rel"]: x for x in curve["curve"]}

    L = []
    L.append("# 自动生成的事实清单")
    L.append("")
    L.append(f"> 生成时间 {v['meta']['generated_at']}；数据根源 `{v['meta']['source']['file']}`"
             f"（{v['meta']['source']['rows']} 行 / {v['meta']['source']['songs']} 曲，"
             f"sha256 `{v['meta']['source']['sha256'][:12]}…`）。")
    L.append("> **本文件由 `analysis/render_claims.py` 生成，勿手改。** 页面与大屏结论都读同一份 JSON。")
    L.append("")
    L.append("## 一、演出效应（同场 DiD，事件级 bootstrap）")
    L.append("")
    L.append("| 相对日 | 效应 | 95% CI | 场次 |")
    L.append("|---|---|---|---|")
    for rel in (0, 1, 2, 3, 7, 14):
        if rel in c:
            x = c[rel]
            L.append(f"| T+{rel} | {x['effect_pct']:+.1f}% | {x['ci_lo_pct']:+.1f} – {x['ci_hi_pct']:+.1f}% | {x['n_events']} |")
    L.append("")
    L.append(f"- 首周均值 **{curve['week1_pct']:+.1f}%**；区间在 0 以上的相对日 "
             f"{sum(1 for x in curve['curve'] if x['ci_lo_pct'] > 0)} / {len(curve['curve'])}。")
    L.append("- 口径敏感性：")
    for cell in sens["cells"]:
        L.append(f"  - {cell['label']}：{cell['did_pct']:+.1f}%（{cell['ci_lo_pct']:+.1f} ~ {cell['ci_hi_pct']:+.1f}），"
                 f"为正场次 {cell['share_positive']:.0%}，n={cell['n_events']}")
    L.append("")
    L.append("## 二、唱功六维（录音室层）")
    L.append("")
    L.append(table(s["metrics"]))
    L.append("")
    L.append(f"- 样本：{s['n']} 首；B1±50 音分（{s['b1']['window_hz'][0]}–{s['b1']['window_hz'][1]} Hz）"
             f"**{s['b1']['count']} 首**（{s['b1']['share']:.0%}）；低于 C2 **{s['below_c2']['count']} 首**；"
             f"音域 ≥2 八度占 {s['span_share_ge2']:.0%}。")
    L.append("")
    L.append("## 三、现场稳定性（清洗后）")
    L.append("")
    q = v["live"]["qc"]
    L.append(f"- 现场记录 {q['total']} 行 → 单曲单场 {q['per_song_session']} 行 / {q['sessions']} 场"
             f"（剔除缺曲名 {q['unnamed']}、整场合计 {q['aggregate']}）。")
    L.append(f"- 可比 {st['n_songs']} 首（≥{st['min_sessions']} 场）：跨场波动中位 "
             f"{st['sd_semitone']['median']:.2f} 半音，p75 {st['sd_semitone']['p75']:.2f}。")
    icc = st["icc"]
    L.append(f"- ICC(1) = {icc['icc']:.2f}（95% CI {icc['ci_lo']:.2f}–{icc['ci_hi']:.2f}，n={icc['n_songs']} 首）："
             f"曲目间差异只占约 {icc['icc']:.0%} 的方差，其余来自场次与音源。")
    L.append(f"- ≥4 场且波动 <1 半音的曲目 **{len(stable)} 首**：" +
             ("、".join(f"{x['song']}（{x['sessions']} 场，{x['sd_semitone']:.2f}）" for x in stable) or "无"))
    L.append("")
    L.append("## 四、口径与限制")
    L.append("")
    L.append("- 指数为平台相对值；日期存在断档；场次间隔 <7 天时窗口重叠。")
    L.append("- 现场与录音室走不同测量管线，**不做差值结论**；低音一律读作「音名 ±50 音分」。")
    L.append("- 双引擎在 ±50 音分内一致帧约七成，`engine_disagreement.json` 自标 `publishable: false`。")

    DEST.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"写出 {DEST.name}（{len(L)} 行）")


if __name__ == "__main__":
    main()
