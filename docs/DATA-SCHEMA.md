# DATA-SCHEMA.md — `data/` 数据层说明

> 49 个 JSON（截至 2026-09-13）。**每个数字引用前先看 `CALIBER.md` 与 `data/calibers.md`。**
> 「生成器」列是要重跑时该跑的脚本（工作目录见 `操作中心.bat` / skill `wangxi-ops`）。

## 一、声学实测（核心资产）

| 文件 | 用途 | 关键字段 | 生成器 |
|---|---|---|---|
| `archive_vocal_albums.json` | **72 首录音室曲目全量实测**（主口径） | `summary{lowest,highest,span_median_octaves,stability_cents_median,vibrato_*}`；`songs[]{album,title,low,low_hz,high,high_hz,span_octaves,stability_cents,intonation_cents,vibrato_hz,vibrato_cents,hnr_db,register_share}` | 音域分析`批量专辑音域.py` |
| `archive_vocal.json` | **跨素材精测层**（规则派生：极值集/对照集/特例集） | `count`；`selection.rule`；`songs[]{name,stable_note,stable_hz,stable_status,stable_verified,reach_note,reach_hz,reach_status,dynamic_range_db,contexts,selection_reasons,manual_review}`；`conclusion`；`b1_reproduction`；`studio_vs_live`；`authority`；`low_history` | 基线`generate_vocal.py` |
| `archive_dynamic_range.json` | **低音区动态范围**（按音级聚合 P5/P95） | `classes[]{note,n,songs,median_dbfs,dynamic_range_db{pp_dbfs,mf_dbfs,range_db,sample_ids,status}}` | 音域分析`低音区动态范围.py` |
| `archive_stage.json` | **他人主导舞台**（综艺/晚会/商演/饭拍） | `source{analyzed,excluded}`；`summary`；`by_category`；`items[]` | 音域分析`对比情境分析.py` |
| `archive_stage_tour.json` | **王晰主导巡演现场层** | `layer`；`policy`；逐条素材与复核状态 | 轨迹`生成巡演现场报告.py` |
| `archive_context_compare.json` | 专辑层 vs 舞台层 **11 项指标**对照 | `metrics[]{key,label,self_median,other_median,delta,p,r,n_self,n_other}`；`sensitivity_solo_only` | 音域分析`对比情境分析.py` |
| `archive_crosscheck.json` | 同曲「舞台版 vs QQ官方版」配对对照 | `n_pairs`；`pairs[]` | 音域分析`双重校验舞台vsQQ.py` |
| `archive_lowc_verify.json` | 低音读数复核判定 | `rows[]`（YIN_OK / 次谐波错误等） | 音域分析`低音复核_LowC.py` |
| `album_verify_status.json` | 专辑层逐曲复核状态（✅/🟡/⚪） | `songs`；`albums` | 音域分析侧 |
| `vocal_measurements.json` | **声学统一长表**（一首歌×一个版本一行） | `layers`；逐行 `layer/tour/city/date/source_ref/metrics{low_note,low_hz,high_*,span,stability,vibrato,density,hnr}/verify/provenance` | `build_vocal_longtable.py` |
| `verify_ledger.json` | **复核总台账**（A3终裁+LowC复核+专辑状态三源合一） | `counts{双引擎一致,已取证,待复核,次谐波错误,未复核}` | `build_vocal_longtable.py` |

## 二、作品与演出

| 文件 | 用途 | 关键字段 | 生成器 |
|---|---|---|---|
| `albums.json` | 专辑元数据 + **QQ音乐核验发行日期** | `albums[]{name,release,release_date,release_source,songs[]}` | `verify_album_dates.py` |
| `songs_meta.json` | 歌曲元数据（最大单文件） | `song_count`；`songs[]` | `build_songs_meta.py` |
| `song_archive.json` / `song_index_lite.json` | 歌曲档案 / 轻量索引 | `count`；`songs[]` | `build_songs_page.py` 等 |
| `credits_full.json` | 词曲编制署名（QQ音乐歌词接口） | `统计`；`songs[]` | 采集侧 |
| `playable_songs.json` | 可试听曲目（含 VIP 标记） | `total`；`playable` | 采集侧 |
| `setlists.json` | 歌单（全站 64 场） | `show_count`；`setlists[]` | `build_setlists.py` |
| `live_repos.json` | 现场 repo 汇总（最大文件之一） | `repos[]`（歌单+反馈+来源） | `build_show_repo.py` 等 |
| `tour_weibo_posts.json` | 巡演相关微博（含与场次匹配） | `matched_to_shows`；`tour_prep_unmatched` | 采集侧 |
| `cities.json` | 城市与场次计数 | `city_count`；`show_count`；`cities[]` | `generate_cities_json.py` |
| `city_guides.json` | 22 城观演指南 | 按城市键 | `generate_city_guides.py` |
| `analytic` → `timeline.json` | 生涯时间轴 | `[]{date,type,title,source,stage}`（41 条） | 人工 + `build_kb_graph.py` |
| `event_lifecycle.json` | 活动生命周期（官宣/开票/开演窗口） | `events[].milestones[]` | `track_event_lifecycle.py` |

## 三、指数与基线

| 文件 | 用途 | 关键字段 | 生成器 |
|---|---|---|---|
| `dashboard/dashboard_data.json` | **唯一数据出口**（大屏） | `total_songs`；当月榜单；效应 | `QQ音乐大屏生成器_GEO优化版_源码.py` |
| `archive_baseline.json` | 统一口径基线（年度值） | `口径`；`源`；`区间`；`annual` | `compute_baseline_v1.py` |
| `archive_digest.json` | 年度档案卡摘要（20 张） | `口径`；`data_through`；卡片 | `generate_year_cards.py` |
| `archive_propositions.json` | 命题卡 | `count`；`cards[]` | `generate_propositions.py` |
| `netease_catalog.json` / `netease_only.json` | 网易云目录 / 独有曲目 | `songs[]` / `count` | 采集侧 |
| `pending_*.json` | 待处理候选（事件/发行/网易云/网页） | `candidates` / `releases` / `results` | 多源 |

## 四、知识库与可引用资产

| 文件 | 用途 | 关键字段 | 生成器 |
|---|---|---|---|
| `kb/facts.json` | **原子事实 1151 条**，每条带 `source_url`+`source_type` | `[]{id,subject,property,value,valid_from,valid_to,source,source_url,source_type,confidence}` | `build_kb_graph.py` |
| `kb/entities.json` / `kb/relations.json` / `kb/manifest.json` | 实体 1419 / 关系 1945 / 清单 | — | `build_kb_graph.py` |
| `kb/semantic/*` | 语义向量索引（4709 文档） | `docs.json`/`vectors.bin`/`graph.json`/`manifest.json` | `tools/build_kb_vectors.py` |
| `qa_bank.json` | 问答库 315 条 | `items[]{id,question,aliases,category,keywords,answer,sources,verified,confidence}` | `build_kb_graph.py` + 人工 |
| `calibers.json` | **口径登记表（35 项）** | `count`；`calibers[]{id,label,value,scope,source,note}` | `build_calibers.py` |
| `literature.json` | 文献索引 46 条 / 6 板块 | `sections[]{title,desc,items[]}` | 人工维护 |
| `authority.json` | 权威点评 + 已发表来源著录 | `items[]{kind,who,text/journal,publisher,indexing,tier_note,method_status,handling}` | 人工维护 |
| `elevator_definition.json` | 电梯定义句（单一事实源） | `full`/`short`/`html`/`facts` | `elevator_definition.py` |
| `site_search_index.json` | 全站检索索引（776 条） | `[]{...}` | 采集/构建侧 |
| `quotes.json` | 金句：现场 Talk（带时间戳）+ `golden_quotes`（跨来源，带证据级别） | `quotes[]`；`golden_quotes[]` | `transcript_pipeline.py` + `build_golden_quotes.py` |
| `essay_quotes.json` / `fan_essays.json` | 歌迷赏析（仅元数据与摘录，不转载全文） | `items[]` | `build_fan_essays.py` |
| `social_links.json` / `notifications.json` | 社交链接 / 站内通知 | — | 运维侧 |

## 五、对比框架与自动化（2026-09-13 新增）

| 文件 | 用途 | 关键字段 |
|---|---|---|
| `comparison_schema.json` | 横向对比**控制变量 + 8 维度记录要求** | `controls[]`；`dimensions[]{key,label,unit,must}`；`singers[]` |
| `comparison/wangxi.json` | 王晰（基准，本站实测值） | `dimensions{key:{value,n,songs,source,confidence,status}}` |
| `comparison/zhaopeng.json` | 赵鹏（**未测·已登记，不填估计值**） | 同上，`status=pending` |
| `analysis_queue.json` | 自动化管线队列（新增分析对象的唯一入口） | `items[]{id,url,singer,title,year,kind,age_band,status}` |

## 六、技能卡片与其它

| 文件 | 用途 |
|---|---|
| `skill_cards.json` | 每日唱功卡片（历史留存） |
| `tavern_audio.json` | 深夜小酒馆逐字稿索引 |
| `facts_registry.json` | 事实登记表 |
| `playable_songs.json` / `fan_essays.json` | 可试听 / 赏析元数据 |

## 七、字段纪律（新增数据时必须遵守）

1. **不写死数字**：能派生的就派生；派生不了的写进 `build_calibers.py` 登记。
2. **带来源**：每条事实/读数至少要有 `source`；对外事实补 `source_url` + `source_type`。
3. **带口径**：声学读数必须有稳定音/触达音/低音带读数的归属（见 `CALIBER.md`）。
4. **不带本地路径**：公开 JSON 不得含 `E:\` / `D:\` 绝对路径。
5. **不改既有字段语义**：要改名就同时改所有读取方（生成器、审计、页面）。
