# -*- coding: utf-8 -*-
"""生成「今早自启核查 + 两首点歌处理」报告（只写事实，不含推断）并落数据层。"""
import json
from datetime import datetime
from pathlib import Path

SITE = Path(r"D:\wx409.github.io")
ARCH = Path(r"E:\wx\论文素材_王晰作传\传播监测")
OUT = ARCH / "自启核查与两首点歌_20261015.md"

# ── 读取实测数据 ──
def load(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


sm = load(SITE / "data" / "song_evidence_master.json", {})
rows = {r["song"]: r for r in (sm.get("rows") or [])}
np_row, ys_row = rows.get("南屏晚钟", {}), rows.get("一生中最爱", {})
sec = (load(SITE / "data" / "archive_stage_tour.json", {}) or {}).get("by_song") or []
sec = {x.get("song"): x for x in sec if isinstance(x, dict)} if isinstance(sec, list) else {}

L = ["# 今早自启核查 + 10-10 两首点歌处理（2026-10-15）", "",
     "> 结论先行：**今早的自启抓取没有跑**（机器自 2026-10-08 09:21 起未重启、启动项只在登录/开机触发）；"
     "并且**微博 cookie 现为「失效」（明确 login=false）**，因此**无法补抓工作室新帖**。",
     "> 两首点歌的**已有本地素材**（10-13 抓取归档）已完成三指标实测与双源/跨场对照，见下。", "",
     "## 一、今早自启核查（证据）", "",
     "| 证据项 | 实测 | 判定 |", "|---|---|---|",
     f"| `temp/auto_fetch_social.log` 最后写入 | {datetime.fromtimestamp((SITE / 'temp' / 'auto_fetch_social.log').stat().st_mtime):%Y-%m-%d %H:%M}（8322 字节） | "
     "**今日无任何「=== 开机自启抓取」记录** |",
     "| 日志中最近两次完整执行 | 2026-10-12 10:53/10:54、2026-10-14 15:14–15:25（后者为验收手跑） | 无 10-15 记录 |",
     "| 开机时间 | `Win32_OperatingSystem.LastBootUpTime` = **2026-10-08 09:21:57** | **今日未开机/未重启 → 启动项不会被触发** |",
     "| 启动项 | `…\\Startup\\wx409_social_boot.cmd` 存在（75B，`start /min cmd /c auto_fetch_social.bat`） | 存在但**本日无触发机会** |",
     "| `weibo_archive/index.json` | total **39**，generated_at **2026-10-13 09:50:50** | 10-13 之后再未更新 |",
     "| `weibo_archive_studio/index.json` | total **2218**，generated_at **2026-10-13 09:56:51** | 同上 |",
     "| `media/` 今日新增 | 本人 **0** 个 / 工作室 **0** 个 | 无新增 |",
     "| 微博 cookie 四态（现查） | **失效（login=false，明确未登录）** | **即使今天触发也会因 cookie 失效而停在第 1 步** |", "",
     "**结论（只述事实）**：**没跑**。原因两条：① 机器今日未重启（启动项自 10-08 起未获触发）；"
     "② 微博 cookie 已明确失效。**不必怀疑脚本**——10-13 同类执行留下了完整记录（本人 39 条 / 工作室 2218 条）。", "",
     "## 二、工作室新帖与两首点歌定位", "",
     "- **今日/昨日新增 mp4：0 个**（`media/` 今日新增 0）→ 你所说的「工作室刚发」那一条**不在本地**。",
     "- 本地最近的**工作室点歌帖**：微博 id **5353266315265746**（`created_at` 2026-10-12 18:40:11，"
     "抓取日 2026-10-13 09:50），正文「点歌环节📹《哭砂》《亲密爱人》」，媒体 "
     "`…_video1.mp4`（5.2MB）/`…_video2.mp4`（11.8MB）**已归档**。",
     "- 因此：**《南屏晚钟》《一生中最爱》的那条新帖未取到**（cookie 失效）；"
     "两曲的**既有**本地/远端素材见第三节。", "",
     "## 三、两首点歌的三指标实测与档位判断", "",
     "门槛（既定纪律）：升格需 **Δ噪声底 ≤ −3 dB** 或 **ΔHNR ≥ +3 dB**；无依据维持触达/样本级。", "",
     "### 3.1《南屏晚钟》——双源（同曲双源旁证）", "",
     "| 源 | 噪声底 (dBFS) | HNR 中位 (dB) | 动态范围 P95−P5 (dB) | 时长 |", "|---|---|---|---|---|",
     "| A｜`点歌段_BV1DtpQ6sE8c` | **−34.88** | **1.83** | 6.48 | 203.1s |",
     "| B｜`点歌段_BV1GTpn6BEFm` | **−32.24** | **3.08** | 5.28 | 191.5s |",
     "| **Δ（B−A）** | **+2.64 dB（未达 −3dB 门槛）** | **+1.25 dB（未达 +3dB 门槛）** | −1.20 | −11.6s |", "",
     "- **档位判断**：**两源均未升格** → 维持**触达/样本级**（现登记最低稳定音口径："
     f"{np_row.get('low_note_live') or np_row.get('low_note') or '—'} "
     f"{np_row.get('low_hz_live') or np_row.get('low_hz') or '—'}Hz）。",
     "- **双源旁证一致性**：两源同曲、同场（10-10 点歌段）、**互不矛盾**；差异仅体现在噪声底（B 高 2.6dB）与 "
     "HNR（B 高 1.3dB），**量级小、不构成来源优劣结论**（不评优劣）。",
     "- **不确定性**：两源均为第三方/中控台混合来源，切片与噪声条件不同；**极值音归属未定**。", "",
     "### 3.2《一生中最爱》——跨场对照", "",
     f"- 三巡舟山 2026-05-23（`BV13MVK6uEa9`，二次制作·待听辨）：**低稳定音 "
     f"{ys_row.get('low_note_live') or '—'} {ys_row.get('low_hz_live') or '—'}Hz**"
     f"（现场层 `low_stable` 口径；由分离实测得到）。",
     "- 本次**中控台直出（工作室）那条未取到** → 无法做同场双源；**跨场对照**只能比量级："
     "三巡舟山为**个人巡演场（王晰主导）**，10-10 为**双人演唱会（东演）**，"
     "**口径与窗口均不同**（整曲 vs 点歌段；手机实录 vs 中控台），**不作优劣判断**。",
     "- **待取到新帖后**才能做「同场双源」与三指标升格判断。", "",
     "## 四、行动建议（不擅自执行）", "",
     "1. 更新微博 cookie（F12 → Network → Copy request headers → 粘进 `E:\\wx\\index_records\\wb.txt` → "
     "跑 `tools\\sync_weibo_cookie.py`）→ 再跑 `auto_fetch_social.py` 即可取到新帖。",
     "2. 取到后即可对两曲做**同场双源**（南屏晚钟｜一生中最爱）与三指标升格判断；"
     "《南屏晚钟》届时可能出现「工作室直出 vs 现场两源」的第三源。", ""]
OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
print("[OK]", OUT)
