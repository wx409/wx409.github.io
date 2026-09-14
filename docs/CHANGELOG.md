# CHANGELOG.md — 重大变更

## 2026-09-14（续）— 第三批数据采集：微博三源结构纠正 + 少城时代入语料

### 事实源结构纠正（重要）
- **「本人微博」是按时期分三个来源**，不是一个账号：微博书（2014-07→2023-10，871 条）／
  百家号（2019-10→2026-07，619 条，另一账号）／本人微博（半年可见，**实测已抓完 33 条**）。
- 工作室线两条：少城时代（2016-08→2021-03）与王晰工作室（2019-08→现在，2206 条）。
- 两处数据坑已登记：微博书_帖子.json 的 date 是**月桶**（不可做年代统计）；
  wx_textmine_corpus\本人微博\ 目录名≠本人账号语料（871 微博书 + 30 账号）。
- 「本人微博缺 1903 条」的说法**作废**：增量抓取实测「无下一页游标、新增 0」，
  API 的 	otal 1936 是账号计数器而非可抓条数。

### 少城时代（UID 1629398873）入语料
- 用账号内搜索 searchProfile 替代全量时间线（154 页/64 分钟 → 13 请求/35 秒）；
  实测时间线 2022-09→2026-08 的 60 页**命中 0%**，证明全量无价值。
- 产出：shaocheng_posts.json（1563 全量并集，含其他艺人，**不可当王晰语料**）、
  shaocheng_posts_wangxi.json（**172 条**王晰相关：84 原创 + 73 转发）、
  E:\wx\wx_textmine_corpus\少城时代\（172 txt，与工作室微博同命名约定）。
- **单字「晰」是唯一净增量（14 条）**：微博在昵称插空格（晰 哥中秋快乐），
  「王晰」「晰哥」两个旧词都匹配不到。
- **交叉核验结论**：少城 157 条与微博书同文**仅 2 条** —— 少城发自家原创宣传、
  不转发他的个人原话；「转发不可见」指少城自己的 73 条转发。

### 执行与阻塞
- ✅ wx_textmine/01_ingest.py 加 shaocheng_weibo 源规则（排在「微博」之前）。
- ✅ project_b/fix_weibo_dates.py：修 weibo_all_posts.json 18 条畸形日期。
- ⚠️ 工作室增量两次均「新增 0」→ 2206 vs API 2225 差额系更早的隐藏/删除帖。
- ⛔ **百家号 8~9 月补采受阻**：主页为 Baidu 签名保护接口，无公开 JSON API。
  已备浏览器脚本 采集增量.js + 归并工具 归并增量.py，待人工跑一次。

### 口径登记表 38 → 44 项
- 新增：weibo_all_posts 1722／weibo_book_posts 770／weibo_personal_visible 33／
  weibo_studio_archived 2206／shaocheng_wangxi_posts 172／shaocheng_union_posts 1563。


> 只记**结构性变更**（站点架构、口径、数据层、生成器、纪律）。
> 逐日运维细节见 `temp/运维备忘_20260907.md`；数字变更见 `data/calibers.md`。

## 2026-09-14 — qa.html 方案 A（全做）+ jazz.html 补厚

### 修了一个一直没被发现的数据 bug（巡次截断）
- **根因**：长表里除六轮巡演外还有 5 场「签唱会」（巡次值形如 `《歌颂》签唱会`、
  `《B面图景》签唱会`…），`build_setlists.py` 用 `tour_raw[:2]` 兜底，
  把它们截成了 `《歌`/`《B`/`《X`/`《不`。脏巡次一路传到 cities / 知识库 / 问答库，
  生成了「`《歌王晰巡演有哪些场次？`」这类**乱码问题**（4 条）。
- **修复**：改为显式归一 —— 六轮巡演 → 一巡…六巡；含「签唱会」→ **签唱会**；其余 → 其他。
- **连带收益**：全站场次口径第一次在数据里自洽：一巡 17 + 二巡 11 + 三巡 12 + 四巡 9 +
  五巡 8 + 六巡 2 = **59**，+ 签唱会 5 = **64**。

### qa.html：问答形态与索引形态分开（方案 A 全做）
- **取消 289 条「某歌在哪些演出唱过」问答**（`build_kb_graph.expand_qa`）；
  原数据一条不丢，改由新增的 `data/songs_shows_index.json` + `songs-shows.html` 承载
  （**289 首 × 64 场 = 1249 条「歌×场」记录**，生成器 `project_b/build_songs_shows.py`）。
  理由：场次列表天然是**表**，套「问+答」不增加信息，只增加模板风险（其中 78 条答案 <20 字）。
- **6 条常识性短答迁为结构化事实**：新增 `data/qa_factoids.json`（出生/奖项/三次机构归属/专辑集），
  由 `build_kb_graph` 注入 `facts.json`（**1151 → 1157 条**）并从问答集中移除。
- **人工条目答案去 markdown 星号**（`王晰**未开过个人演唱会**` 在 HTML 里原样显示星号）。
- **补 FAQPage JSON-LD**：此前 `qa.html` 的 JSON-LD **缺 `@type: FAQPage`**
  （与 llms.txt 的声明不符）——现已修正，16 条问答全部进 FAQPage。
- `qa.html`：**151KB → 24.8KB**，16 条**有出处、有论证**的问答（每条附数据源链接）。
- 生成器 `tools/build_qa_page.py` 重写：带 NAV/FOOTER 标记（`build_nav` 可幂等接管）+ 来源链接。

### jazz.html：补厚（独立页保留，不并入 research）
- 由 8.7KB → **18.1KB**；`project_b/build_jazz_page.py`（新生成器，数据全派生）。
- **曲目表扩到 12 首**（按演唱场次排序）：Your Man 19 / Besame Mucho 13 / Close to You 13 /
  像雾像雨又像风 13 / 月半弯 13 / City of Stars 12 / Autumn Leaves 6 / Yesterday Once More 2 /
  情网 2 / 女人花 1 / 晚风 1 / 水中花 1。
- 新增「**跨巡演延续性**」：这条线从 2019 一巡延续到 2026 六巡。
- 新增「**声学实测（低音区爵士）**」：《晚风》F2 85.6Hz / 跨度 1.77 / 颤音 5.38Hz。
- 新增「**试听与第三方语境**」4 条（现场录像 / 改编讨论 / 器材试听 / 发烧圈帖），逐条标性质与用途。
- 新增 **Dataset + FAQPage**（原只有 BreadcrumbList）。
- ⚠️ **口径澄清**：《晚风》（爵士改编，1 场，《Low C的诱惑》F2 85.6Hz）与
  《晚风暖暖》（王晰原唱，17 场，《重游往昔》C2 65.3Hz）是**两首不同的作品**，
  后者不并入爵士线（此前检索用子串匹配，把两首混在一起过）。

### 口径登记表 38 项（+3）
- 新增 `songs_shows_rows`(1249) / `songs_shows_songs`(289) / `jazz_repertoire_songs`(12)；
  `qa_pairs` 315 → **16**（只计实质问答）；`kb_facts` 1151 → **1157**。

### 验证
- `audit_nav`（孤儿 0/漂移 0/死锚点 0）、`audit_jsonld`、`audit_caliber`、`audit_pipeline`、
  `check_index_integrity` 全绿；第一批 49/49、第二批 60/60。
- sitemap **38 条**（含 songs-shows.html、jazz.html）；IndexNow 同步新增两页。


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
- 口径登记：28 → **38 项**（补 7.1/7.5 新计数）；`data/calibers.md` 定位为可重建产物，单一事实源 = 脚本。
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
