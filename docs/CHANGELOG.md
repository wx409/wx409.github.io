# CHANGELOG.md — 重大变更

## 2026-09-15（续）回望专辑复核 + CREPE 反向误报发现

- **回望《无人岛上》最低稳定音 = D2 75.4Hz**（复核通过）。
  依据：重新人声分离 + 分离人声轨谐波列显示 1f0(75.4Hz) 为最强峰（-0.0dB）、2f0 亦在。
  此前站点值 D#2 77.9Hz 来自 09-09 的旧分析目录（`专辑音频_分析`）。
- **修一处陈旧**：`archive_vocal_albums.json` 自 2026-09-09 起未同步，
  09-10/09-11 的测量更新（如月光 C6 1067.5Hz）一直没推上来。
  已在生成器层重新派生，并同步说明书/预设字面量。
- **⚠️ 方法论：CREPE 交叉校验存在「反向误报」**（此前只记录了前向误报）。
  判据 `CREPE/YIN > 1.5 → YIN 次谐波错误` 本次给出比值 3.00 判定 YIN 错，
  但谐波列证明 **CREPE 自己锁到了 3 次谐波**、YIN 是对的。
  已在 `CREPE交叉校验.py` 写明：该判定必须经谐波列复核后才可采信。
- **聚合值同步**：最高 1065.0→**1067.5Hz**｜跨度中位 2.30→**2.27**｜
  颤音 5.17→**5.12Hz**｜密度 1.85→**1.88/s**；最低 B1 61.5Hz 不变。
  分享图（声学身份证）已重生成并通过指纹校验；voice.html 已重生成。

## 2026-09-15（续）6 个孤儿脚本全部接入流水线

反向检查暴露的 6 个 BACKLOG 脚本已全部接入，`ORPHAN_BACKLOG` 清空：

| 脚本 | 去处 | 理由 |
|---|---|---|
| `audit_stage_exclusions.py` | **部署链**（跟 audit_ops_coverage 之后） | 守卫类：防生成器把已排除素材/错误曲名回吞上线 |
| `build_album_verify.py` | **部署链**（跟 build_vocal_longtable 之后） | 生成站点数据 `data/album_verify_status.json` |
| `audit_audio_bitrate.py` | 菜单 **152** | 逐文件算真实码率，核对「QQ音乐320k」这类元数据声明 |
| `append_tavern_quotes.py` | 菜单 **154** | 小酒馆金句并首页 |
| `build_tavern_summary.py` | 菜单 **155** | ⚠️ 调 DeepSeek API 有成本 → 必须人工触发，不进部署链 |
| `rebuild_tavern_ep_summary.py` | 菜单 **156** | 摘要版 ep 页重建 |

新增 **U 组「审计与内容补齐」**（151–156），操作中心 150 → **156**。

**顺带修一个静默失效**：`append_tavern_quotes.py` 的插入锚点是 `<h2>历史巡演回顾` ——
瘦身 2.0 后首页由 `build_compact.py` 生成，**该板块已不存在**，脚本每次都打印
「[!] 未找到插入锚点」然后静默返回（不报错、也不生效）。
→ 改**自适应锚点**：`历史巡演回顾` → `<!-- FOOTER_NAV_START -->` → `<footer>` 依次回退，
并打印实际使用的锚点。
另注：其上游 `tavern/tavern_summaries.json` 当前为空（0 条），故插 0 条属正常，
需先跑菜单 155 生成摘要。

**验证**：`audit_bat` / `audit_ops_coverage`（待接入 0 · 未登记 0）/ `audit_pipeline`
（registry 168 条 = 菜单 156 · 分派 155 · 部署 54 · 计划任务 7）/ `audit_caliber` 全绿。

## 2026-09-15（续）audit_ops_coverage 新增反向检查

**起因**：2026-09-14/15 新增 15 个声音素材脚本，**一个都没进菜单**，而
`audit_ops_coverage` / `audit_pipeline` 全绿 —— 因为它们只校验"**已登记项**"的一致性，
**查不出"脚本在盘上却没入口"**。

**新增 C 类反向检查**（`python project_b/audit_ops_coverage.py [--strict]`）：
- 扫描 `project_b/` · `tools/` · 根目录下所有带 `if __name__ == "__main__"` 的**可运行脚本**
- 判据：属于「菜单 ∪ 部署链 ∪ 计划任务 ∪ 被其他脚本/bat 引用」即视为可达
- 三档输出：
  - `ORPHAN_ALLOWLIST` 永久豁免（一次性修复 / 被 import 的库 / 已被生成器取代的迁移脚本）
  - `ORPHAN_BACKLOG` 已知应接入但未接入（显式登记便于排期）
  - **未登记** —— 既不在上面两档也没入口（真正要警觉的）
- **默认只报警不阻断**（`audit_ops_coverage` 在每日部署链里，硬失败会卡住发布）；
  `--strict` 时出现"未登记"即退出码 1。菜单新增 **150** 号（可交互选择严格模式）。

**验证**：造探针脚本 `project_b/_zzz_orphan_probe.py` →
默认模式报「未登记 1」且 exit 0；`--strict` 报同一项且 **exit 1**；删除后回到「未登记 0」。

**踩坑**：判断文件是否在 `.git` 内时写成 `'.git' in str(绝对路径)` ——
本仓库根目录名 `wx409.github.io` **本身含 `.git` 子串**，导致**每个文件都被跳过**、
扫描数恒为 0。已改为对**相对路径**逐段比较（`_under_git()`）。

**同时发现的 13 个孤儿脚本**（首次跑反向检查即暴露）：
- 已修/已豁免 7：`build_debate`/`build_comparison`（产物已上线）、`build_legacy_notes`
  （页面生成器已原生包含 NOTE 块）、`dsh_llm`（库）、`data_pipeline`（遗留原型）、
  `fix_songs_meta`、`tools/fix_activity_table_corrections`（一次性修复）
- 待接入 6（已登记 BACKLOG）：`append_tavern_quotes` / `audit_audio_bitrate` /
  `audit_stage_exclusions` / `build_album_verify` / `build_tavern_summary` /
  `rebuild_tavern_ep_summary`

**项数同步**：操作中心 149 → **150**（AGENTS.md / wangxi-ops SKILL / 维护者预设）

## 2026-09-15 运维梗阻修复（deploy 中止 / 假告警 / 漏批不自愈）

- **deploy_all 连续两天中止**（站点停止更新）：`update_index_table.py` 因首页改版后
  无「最新演出动态」锚点而抛错，作为关键步骤中止整条流水线。
  同类还有 `inject_vocal_summary.py`。→ 两脚本改为**识别改版后优雅跳过（exit 0）**，
  内容仍在 live.html / vocal.html。同时记下一个既有缺陷：注入步骤排在页面重建之前，
  即使不报错也会被冲掉。
- **「指数长表滞后 2 天」连续三天为假告警**：`auto_update.py` 里看门狗(00:03)
  排在长表刷新(00:04:46)之前 → 看到的永远是刷新前状态。→ 调换顺序。
- **漏批只告警不自愈**：守护进程为 LogonTrigger，早间登录晚于 8:05/8:15/8:25
  即稳定漏 3 批。→ 新增 `CATCHUP_MIN_MISSING=3`，存活但漏批≥3 时立刻补跑；
  补跑成功记入 state 避免重复（原 `state["done"]` 只写不读，已补读取）。
- 立即补跑：`run_batch_now --mode full` → 383/383，长表 → 2026-09-14（滞后 0 天），
  2026 年度值 685.6 → **690.5**。
- 同步维护者预设（口径项数 21→53 两处；年度值/中位）。自测更新为 25/25。
- 验收 `acceptance_check`：**✅ 27｜⚠️ 5｜❌ 0**（此前 ❌ 2）。

## 2026-09-14（声音素材全链路·收官）

### 攻下两个此前判定"必须人工协助"的平台（都是我从 JS 包里挖出接口）
| 平台 | 破法 | 成果 |
|---|---|---|
| **QQ音乐「城市漫行」** | `c.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg?albummid=…`（专辑元数据）+ `musicu.fcg` 的 `vkey.GetVkeyServer`（直链，免登录） | **26/26 全下**（7 城 25 周；2021-01-29 发行） |
| **荔枝FM「低音时间」** | 从 Next.js JS chunk 挖出 `vodapi/user/<uid>` 调用模板 | **59/59 全下**（2016-03-14 ~ 2017-10-20） |

### 荔枝实况修正（早先假设有误）
- 期数 **63 → 59**（平台 `voiceCount=59`；标题期号到第六十三期 → **4 期已下架**）
- 起始 **2016-09 → 2016-03-14**；共 243.4 分钟；播放 297.6 万 / 粉丝 2.86 万

### 最终规模
- 媒体 **157 个文件 / 约 1.16 GB**（全部本地留存，不入 git）
- 转写 **157 条 / 171,098 字 / 926.1 分钟（15.4 小时）**
- 跨 **11 个系列（18 个 series key）**，覆盖 2016–2026
- 知识库：实体 **1598**｜事实 **1686**｜关系 **2220**｜语义 docs **5399**
- 语料同步 `wx_textmine_corpus/声音素材/` 157 txt（幂等）

### 站内呈现
- `research.html` 新增「四、声音素材语料」区块（派生自 JSON，含逐系列表 + 分析结论）
- `llms.txt` 新增该行；区块编号已校准（原误置于「四 口径登记表」之前）

### 文本分析结论（更新版）
- 情感：正 1502 / 负 135 → **偏暖**
- 人称：我 2245 / 你 1453 / 我们 707 → **单人对话式**
- 主题（按字数）：时间与年华 > 家与亲情 > 夜与睡 > 音乐与歌唱 > 爱情 > 诗与远方
- 时间线：**2016–2017（荔枝）与 2021（城市漫行）是音频内容双峰**（128.6 / 410.1 分钟）

### 仍未取得（如实登记，不伪造）
- 「我们的好梦时刻」第 11 期（2020-04-14，白落梅《不败于岁月，不输于山河》）：
  确证存在（新浪转载页可读全文），但喜马拉雅搜索/播放接口均需登录态，**无公开 track id**
- 三体《黑暗森林》第四季第16集：付费专辑，专辑曲目接口返回 0 首，**无直链**

## 2026-09-14（声音素材·文本分析）

- 新增 `data/voice_analysis.json`：高频词 / 主题分布 / 情感倾向 / 人称 / 系列对比 / 金句候选。
  生成器 `project_b/analyze_voice_corpus.py`（jieba 分词 + 规则筛选）。
- **修了一处 ASR 系统性错字**：faster-whisper 把「王晰」听成「**王熙**」共 **63 次**、
  「晰哥」→「西哥」1 次（低音人声 + 背景乐下的生僻人名是典型弱点）。
  - 治标：`project_b/fix_asr_names.py` 定向替换 40 个文件 / 64 处（只改确证错字，不做模糊匹配）
  - 治本：`transcribe_media.py` 加 `initial_prompt` 热词
- **口径关键（写进产物）**：这批素材里 **25/32 条金句是「他朗读的文本」**（文学/歌词），
  **不等于「他说的原话」**；只有节目口播/自我介绍类（7 条）才含本人原话。
  该字段以 `语料性质` 明确写入 `voice_analysis.json`，避免日后误引。
- 口径登记表 48 → **51 项**（`voice_corpus_items` 72 / `voice_corpus_chars` 51488 /
  `voice_corpus_minutes` 305.8）。

### 文本分析初步结论（可写进传记的三条）
1. **他选择读什么**：主题按字数排序为 时间与年华 > 家与亲情 > 夜与睡 > 爱情 > 诗与远方 > 音乐与歌唱。
2. **他面向谁说**：人称「我」1140 次 / 「你」616 次 / 「我们」225 次 —— 单人对话式，而非宣讲式。
3. **夜间电台的情绪基调**：情感词命中 正 640 / 负 79 → **偏暖**（不是伤感台）。

## 2026-09-14（第三批·电台元数据建档）

- 新增 **`data/radio_archive.json`**（schema `radio_archive v1`）：**只著录元数据、不下载音频**。
  series 7 / 已著录单集 **68** / singles **9** / unverified **11**。
- **核验到的关键事实**：
  - 「音乐图书馆」实为 **8 个 P**（bilibili `BV1nt411D7FQ`，经 public view API 核验）
  - 网易云 DJ 电台（`music.163.com/djradio?id=792978415`）**JSON-LD 可直读，30 集全量**
    （2019-03-23~05-12）；其第 7–14 集与「音乐图书馆」8 分 P 一一对应 → 内容旁证
  - 微博头条文章已抓全文：原文只提节目名、**不列期数** → 不能作为「7 集」的证据
  - 快手「晰望你听见」B 站饭制合集 20 段（2022-07-10 上传）
- **硬阻塞（纯 HTTP 无解）**：荔枝FM（403 + Next.js 客户端渲染，页面内不含列表接口）、
  微博（Sina Visitor System）、喜马拉雅 sound 页（JS 渲染）、QQ音乐专辑页（302）；
  另经本项目复测：荔枝 `_next` 站点接口由 JS 签名保护，纯 HTTP 拿不到。
- **纪律取舍**：微博 post id 日期解码**本机验证失败**（两种算法都无法复现已知日期）
  → ELLE 8 条日期留 `null`，**不推算**；官方期数 63/25/7 一律未当既成事实，全部进 `unverified`。
- 口径登记表 45 → **48 项**（`radio_episodes_archived` 68 / `radio_singles_archived` 9 /
  `radio_unverified_items` 11）。

## 2026-09-14（第三批·百家号补齐）

- **补上百家号 2026-08~09 缺口**：619 → **625 条**（最新至 2026-09-10）。
  净新增 6 条（2 条 2026-08/09 + 4 条 2023 年视频类旧漏）。
- **采集方式（重要）**：百家号主页是 Baidu 签名保护接口，直连端点全部返回安全页，
  **无公开 JSON API** → 必须走浏览器 console 脚本。已固化为：
  - 采集增量2.js（按真实 DOM 结构 div.feed-item 抓取；不再依赖 <a href>；
    自动滚到底；xecCommand 兜底复制）
  - 探测页面结构2.js（DOM 诊断，页面改版时先跑它）
  - 归并增量.py（去重双判据 nid + 正文指纹；补年份；保持既有降序）
  - sync_baijiahao_corpus.py（同步进 wx_textmine_corpus\百家号\，幂等）
  - cleanup_baijiahao_dup.py（清理误生成重复文件）
- **踩坑记录**：sync_baijiahao_corpus.py 首版判重只认 _001 后缀、未认既有 _000
  → 整库重复生成 584 个文件（已清理并修脚本）。
- 口径登记表 44 → **45 项**（新增 aijiahao_articles 625）。

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
