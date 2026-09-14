# CHANGELOG.md — 重大变更

> 只记**结构性变更**（站点架构、口径、数据层、生成器、纪律）。
> 逐日运维细节见 `temp/运维备忘_20260907.md`；数字变更见 `data/calibers.md`。

## 2026-09-13（晚）— 展示策略更正 + 第一批修补

### 更正：完整档案页「不展示」≠「不收录」
- `build_nav.py`：`LEGACY_NOINDEX`（强制 noindex）→ **`ARCHIVE_PAGES` + `ROBOTS_INDEX`（强制 index, follow）**。
- `deploy_all.py`：IndexNow 恢复推送完整档案页（39 条 URL，实推 39/39 成功）。
- `build_compact.py`：sitemap 恢复全量对外页（**36 条**，排除私密/实验区）。
- 外部大屏生成器源码（`E:\wx\QQ音乐大屏生成器_GEO优化版_源码.py`）robots 回滚为 `index, follow`。
- 顶部主导航仍只放精简版 7 页；**底部全站索引恢复全量**（5 组），完整档案页有直连入口。
- noindex 仅剩：`archive-index.html`（私密索引）、`kb-semantic.html`、`debate/`、`search.html`。

### 第一批修补（对应「网站修补」层）
- [1-1] sitemap.xml：7 条 → **36 条**（对外页全量）。
- [1-2] `archive-index.html`：151KB 整页快照 → **11KB 纯链接索引**（目标 <15KB，达标）。
  正文只此一份、在原页；本页只有链接与一句说明。
- [1-3] 新增 **`docs/链接登记.md`**：全部链接留本地，含用途与「收录/推送」状态。
- [1-4] llms.txt 一致性修正：声明改为「8 个公开页」；`stage.html` 移入「完整档案」区；
  `qa.html` 标注「待正式扶正」；新增「刻意不收录」区。
- [1-5] 精简版正文「旧页，完整存档」→「**完整档案**」（5 处）。
- 新增 `docs/计划外页面清单_20260913.md`（8 个边界页逐个报告，**只报告未处理**）。
- 新增 `docs/qa抽查_20260913.md`：抽查 20 条 → 96.8% 为机械派生、26% 答案 <20 字、仅 3.2% 带出处
  → **结论：暂不扶正为第 8 个公开页**。

### 第二批：项目上下文文件
- 新增 `AGENTS.md`（每次会话先读，<150 行）+ `docs/PROJECT.md`、`docs/DATA-SCHEMA.md`、
  `docs/CALIBER.md`、`docs/CHANGELOG.md`（本文件）。

### 验证
- 第一批验证 49/49、第二批验证 60/60；`audit_nav`（孤儿 0/漂移 0/死锚点 0）、`audit_jsonld`、
  `audit_caliber`、`audit_pipeline` 全绿；线上 25/25 完整档案页 200 + 可收录；IndexNow 39/39。

## 2026-09-13 — 网站瘦身 2.0 + 声学整合与扩展（两批）

### 第一批（主线上线）
- 新建**精简版 7 页**作对外主入口：`index` `works` `live` `vocal` `history` `research` `community`
  （由 `project_b/build_compact.py` 单一生成器派生，所有数字来自 `data/*.json`）。
- `index.html` 由完整版改为精简版；完整版首页快照迁至 `archive-index.html`。
- 注入器改指 `archive-index.html`：`build_home` / `inject_vocal_summary` / `inject_index_facts` /
  `update_index_table`。
- 修 `inject_vocal_summary.py` 长期缺陷：读错字段 `lowest_note`（应为 `stable_note`）→ B1 曲名恒为空。
- 备份：分支 `full-archive` + 标签 `v1.0-full-20260913` + 本地克隆 `E:\wx\backups\wx409-full-backup-20260913`。

### 第二批（声学扩展）
- **6.2 归档提示**：voice/stage/skill 的 4 处重复数据块加「最新版本见 vocal/live」提示，**表格全部保留**。
- **6.3 三级读数制度**：`TIER-CALIBER` 标记块落 voice/stage/skill/vocal **四页**（生成器内置）。
- **7.1 低音区动态范围**：新工具 `音域分析/低音区动态范围.py` + `data/archive_dynamic_range.json`；
  B1 11.4dB / C2 21.3 / C#2 15.7 / D2 16.4 / D#2 18.9 / E2 19.0（P5–P95）；A1 类排除。
- **7.2 横向对比框架**：`data/comparison_schema.json` + `comparison/wangxi.json` + `comparison/zhaopeng.json`（未测不填）。
- **7.3 专家辩论模块**：`debate/`（noindex 实验区，《向着太阳》最低音之争）。
- **7.4《乐器》入档**：`data/authority.json` → research/academic/voice 权威区（不写"核心刊物"）。
- **7.5 自动化管线**：`tools/{fetch,analyze,queue_run}.py` + `README.md` + `.github/workflows/analysis.yml`
  + `data/analysis_queue.json`；测量链自检跑通。
- 金句档案：`quotes.json` 增 `golden_quotes`（带证据级别，"待核实"单列）。
- 口径登记：28 → **35 项**（补 7.1/7.5 新计数）；`data/calibers.md` 定位为可重建产物，单一事实源 = 脚本。
- 修 `build_skill_page.py`：七维表 stability/vibrato 读逐曲字段恒为空（→ 改从 72 曲 summary 派生），
  并把 `sorted(x)[len(x)//2]` 换成 `statistics.median`。

## 2026-09-11 — 声学长表统一 + 页面整理
- 新增 `data/vocal_measurements.json`（146 行，一首歌×一个版本）+ `data/verify_ledger.json`（257 条复核判定）。
- 跨素材精测层改为**规则派生**（A 极值集 ∪ B 对照集 ∪ C 特例集），不再手挑「十曲」。
- `kb-semantic.html` 加 `noindex, follow` 并移出 sitemap（URL 仍可用保书签兼容）。
- 任务登记表单一事实源：`project_b/pipeline_registry.json`（派生 + 四向比对 `audit_pipeline.py`）。

## 2026-09-09 — 站内外一致性 + 音高测量可信度
- 新增 `project_b/research_ld.py` / `inject_vocal_summary.py` / `inject_index_facts.py` /
  `update_sitemap_lastmod.py` / `audit_live.py`。
- 《向着太阳》最低稳定音修正为 **G2 97.8Hz**（原 D#2 78.1Hz 系 YIN 次谐波错误）。
- 确立「过程稿不上线」纪律（`audit_jsonld` + `audit_live` 黑名单把关）。
- `voice.html` 升级为 Dataset + ResearchProject + FAQPage 结构化数据。

## 2026-09-08 — 音域权威化 + 命题卡体系
- 确立「极低音实测必须人声分离」（混音版 A1 为伴奏 bass 污染）。
- 音域白皮书 v1：四层证据 + 分档对外措辞（稳妥/进阶/禁用）；**不主张排名式结论**。
- 命题卡体系 v1：矛盾驱动 + 五段式（现象→证据→机制→反证→落点）。
- 矛盾扫描器 `基线口径/矛盾扫描器.py`。

## 2026-09-07 — 文本挖掘切本地 + 数字档案定调
- wx_textmine 全线切本地模型（qwen2.5:7b），解决云端内容审核拒绝大段微博文本的问题。
- 挖掘报告改按**百度百科核校**（履历事实以百科为准）。
- 「数字档案」四层档案卡设计定调（履历/语料/数据/关联）；`原始材料总索引_v1.md` 定为唯一入口。
- 操作中心.bat 重构（A–F 六组，编号连续）。
