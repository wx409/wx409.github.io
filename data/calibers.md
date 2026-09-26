# 口径登记表（单一事实源 · 数字字典）

> 生成时间：2026-09-27 00:12　｜　生成脚本：`project_b/build_calibers.py`（幂等，部署时自动重跑）
>
> **纪律**：任何页面/论文/宣传材料引用数字，必须同时给出本表 id 与范围。
> 不同范围的数字**不是矛盾**，混用才是错误。场次数必须成对出现（全站 = 巡演 + 签唱会）。

| id | 名称 | 数值 | 范围 | 来源 |
|---|---|---|---|---|
| `tracked_songs` | 追踪曲目池 | **383** | 主动追踪并采集指数的曲目清单（池内） | `dashboard/dashboard_data.json` |
| `tracked_links` | 追踪链接数 | **383** | 同一首歌的多个平台链接（一首歌可有多条链接） | `dashboard/dashboard_data.json` |
| `entity_songs` | 关系图谱曲目 | **438** | 至少有一条关系（现场/小酒馆/专辑）的曲目 | `entity_index.json` |
| `songs_meta` | 歌曲元数据条目 | **685** | 含元信息（时长/专辑/发行等）的曲目 | `data/songs_meta.json` |
| `song_archive` | 歌曲档案条目 | **748** | 档案库收录的全部曲目条目（含未追踪/无指数） | `data/song_archive.json` |
| `credits_songs` | 署名/演职信息曲目 | **325** | 有公开演职/署名记录的曲目 | `data/credits_full.json` |
| `stage_tet_intonation` | 现场音准偏差中位（TET，伪影） | **21.0** | 王晰主导巡演/签唱会现场素材（demucs 人声分离后 YIN 逐帧测音准偏差） | `data/archive_stage_tour.json` |
| `stage_claimable` | 现场层可主张素材 | **522** | 过复核门槛（人耳确认/谐波列通过/双引擎一致）的现场素材条数 | `data/archive_stage_tour.json → summary.n_claimable` |
| `vibrato_tier` | 颤音速率的分层归属 | **组内可纵比、跨组谨慎** | 修音敏感度分层中的单列一档（区别于高敏感层的稳定性/音准） | `音频备忘 §21 / acoustic-report「六条纪律」/ 宣传词条库 #8` |
| `playable_songs` | 可试听曲目 | **117** | 站内提供试听入口的曲目 | `data/playable_songs.json` |
| `netease_songs` | 网易云曲库曲目 | **125** | 网易云音乐侧可核验曲目 | `data/netease_catalog.json` |
| `shows_all` | 全站场次 | **64** | 六轮巡演 + 签唱会等非巡演演出 | `data/cities.json（长表派生）` |
| `shows_setlists` | 有歌单记录的场次 | **64** | 长表中至少有 1 条曲目记录的场次 | `data/setlists.json` |
| `cities` | 巡演城市数 | **22** | 去重城市 | `data/cities.json` |
| `live_songs` | 有现场记录的曲目 | **305** | 至少在一个场次歌单中出现过的曲目 | `entity_index.json` |
| `kb_facts` | 知识库事实条数 | **1704** | 结构化事实 | `data/kb/manifest.json` |
| `kb_entities` | 知识库实体数 | **1663** | 人/歌/专辑/演出/城市等实体 | `data/kb/manifest.json` |
| `kb_relations` | 知识库关系数 | **2312** | 实体间关系 | `data/kb/manifest.json` |
| `semantic_docs` | 语义索引文档数 | **5568** | 可语义检索的文档块 | `data/kb/semantic/manifest.json` |
| `qa_pairs` | 问答对数量 | **16** | 可引用问答（GEO 资产） | `data/qa_bank.json` |
| `shows_tour` | 六轮巡演场次 | **59** | 一巡~六巡的巡演场次（不含签唱会） | `巡演歌单长表（单一事实源）` |
| `setlist_rows` | 歌单曲目记录行 | **1254** | 长表曲目行（含串烧拆分行前的原始记录） | `巡演歌单长表` |
| `setlist_songs_unique` | 歌单唯一曲目（数据层归一名） | **293** | 长表去重后的曲目名 | `巡演歌单长表` |
| `index_days` | 指数数据覆盖天数 | **1300** | 站点图表所用指数长表的实际覆盖天数 | `E:\wx\wx_textmine_out\music_index_long.csv` |
| `stage_measured_versions` | 现场实测版本数 | **16** | B站音轨人声分离后实测的现场演唱版本（一巡/二巡/六巡的同一首歌多场次） | `音域分析\轨迹\让她降落_四版实测.json` |
| `stage_measured_shows` | 现场实测场次数 | **5** | 上述现场版本覆盖的实际演出场次（同场多源只算一场） | `音域分析\轨迹\让她降落_四版实测.json` |
| `stage_low_reviewed` | 巡演现场低音读数·谐波列复核通过条数 | **484** | archive_stage_tour.json 中复核状态为「谐波列复核通过」的素材条数 | `data\archive_stage_tour.json` |
| `stage_lowest_hz` | 巡演现场最低稳定音（现行） | **57.8** | 王晰主导巡演现场·过复核门槛的最低稳定音（Hz） | `data\archive_stage_tour.json` |
| `reach_多听有益` | 多听有益 念诵段触达音（G#1） | **51.9** | 录音室 MV / 念诵段 @80.0s：混音带限自相关 + 外部耳测；属触达级，**不并入稳定音口径** | `data\archive_vocal.json#songs[].reach_*` |
| `reach_live_多听有益` | 多听有益 现场念诵段低音事件（A1） | **56.5** | 四巡｜北京 2023-11-12（王晰本人号直拍 BV1Ab4y1g7Wj）｜@55.5s（2.0s）：本人现场人声在场（听辨认定）；属触达级，**不并入稳定音口径** | `data\archive_vocal.json#songs[].live_low_events` |
| `reach_live_多听有益` | 多听有益 现场念诵段低音事件（A1） | **54.3** | 四巡｜杭州 2024（BV1ArKxe7E8H）｜@57.8s（1.0s）：本人现场人声在场（听辨认定）；属触达级，**不并入稳定音口径** | `data\archive_vocal.json#songs[].live_low_events` |
| `dynamic_range_B1` | B1 低音区动态范围（P95−P5） | **11.4** | 已过复核门槛的音级 B1（）：pp -22.0 dBFS → mf -10.6 dBFS，n=8 次出现 / 5 曲 | `data\archive_dynamic_range.json#classes[]` |
| `dynamic_range_C2` | C2 低音区动态范围（P95−P5） | **21.3** | 已过复核门槛的音级 C2（）：pp -35.0 dBFS → mf -13.7 dBFS，n=38 次出现 / 16 曲 | `data\archive_dynamic_range.json#classes[]` |
| `dynamic_range_Cs2` | C#2 低音区动态范围（P95−P5） | **15.7** | 已过复核门槛的音级 C#2（）：pp -31.6 dBFS → mf -15.9 dBFS，n=35 次出现 / 16 曲 | `data\archive_dynamic_range.json#classes[]` |
| `dynamic_range_D2` | D2 低音区动态范围（P95−P5） | **16.4** | 已过复核门槛的音级 D2（）：pp -31.1 dBFS → mf -14.7 dBFS，n=106 次出现 / 43 曲 | `data\archive_dynamic_range.json#classes[]` |
| `dynamic_range_Ds2` | D#2 低音区动态范围（P95−P5） | **18.9** | 已过复核门槛的音级 D#2（）：pp -29.9 dBFS → mf -11.0 dBFS，n=75 次出现 / 32 曲 | `data\archive_dynamic_range.json#classes[]` |
| `dynamic_range_E2` | E2 低音区动态范围（P95−P5） | **19.0** | 已过复核门槛的音级 E2（）：pp -32.4 dBFS → mf -13.4 dBFS，n=123 次出现 / 44 曲 | `data\archive_dynamic_range.json#classes[]` |
| `analysis_queue_items` | 自动化分析管线队列条目数 | **2** | data/analysis_queue.json：新增分析对象（含横向对比候选歌手）的唯一入口 | `data\analysis_queue.json#items` |
| `songs_shows_rows` | 歌曲×场次索引记录数 | **1254** | 全站 64 场歌单展开：293 首歌曲 × 场次 | `data\songs_shows_index.json` |
| `songs_shows_songs` | 歌曲×场次索引·歌曲数 | **293** | 同表口径：出现在已收录歌单中的不同歌曲数 | `data\songs_shows_index.json` |
| `jazz_repertoire_songs` | 爵士/Bossa Nova 曲目线条目数 | **12** | 站内歌单中判定为爵士/Bossa Nova 的曲目数（依据：歌单备注 + 曲目风格归属） | `project_b\build_jazz_page.py` |
| `weibo_all_posts` | 四源统一微博帖数 | **1722** | 工作室微博 + 百家号 + 本人微博（统一表，本地档案不进 git） | `E:\wx\私有工具\weibo_merged\weibo_all_posts.json` |
| `weibo_personal_visible` | 本人微博当前可见帖数 | **33** | 王晰本人账号（1292815744）经 API 抓取到的全部可见帖 —— **实测确认已抓完**：末页无下一页游标、增量新增 0 条 | `E:\wx\私有工具\weibo_archive\index.json` |
| `weibo_studio_archived` | 工作室微博已归档帖数 | **2206** | 王晰工作室（7215995153）2019-08-08 ~ 2026-09-04 逐条归档 | `E:\wx\私有工具\weibo_archive_studio\index.json` |
| `weibo_book_posts` | 微博书 OCR 基准帖数 | **770** | 微博书（3 册）OCR 帖 —— 2014-2018 本人原话的主干来源 | `E:\wx\私有工具\weibo_merged\weibo_book_posts.json` |
| `shaocheng_wangxi_posts` | 少城时代官博·王晰相关帖数 | **172** | 少城时代（UID 1629398873）2016-08-12 ~ 2021-03-11 的王晰相关帖，含转发 | `E:\wx\私有工具\weibo_merged\shaocheng_posts_wangxi.json` |
| `shaocheng_union_posts` | 少城时代官博·23词搜索并集（含其他艺人） | **1563** | 同账号 23 个关键词并集（多艺人厂牌号：张靓颖/王铮亮/赵露思…） | `E:\wx\私有工具\weibo_merged\shaocheng_posts.json` |
| `baijiahao_articles` | 王晰百家号帖数 | **625** | 百家号（另一账号，非本人微博）：2019-10-28 12:55 ~ 2026-09-10 19:00 | `E:\wx\私有工具\weibo_baijiahao_archive\baijiahao_archive.json` |
| `radio_episodes_archived` | 电台节目已著录单集数 | **68** | 已逐集著录（标题/日期/时长/平台）的单集数，跨 7 个系列 | `data\radio_archive.json#series[].episodes` |
| `radio_singles_archived` | 电台/读诗单条已著录数 | **9** | 单集/读诗/读信类条目（含音乐图书馆专访、好梦时刻第11期等） | `data\radio_archive.json#singles` |
| `radio_unverified_items` | 电台档案·待核项数 | **11** | 无法核验、已单列的条目（含荔枝 63 集清单、ELLE 8 条微博、城市漫行 25 周等） | `data\radio_archive.json#unverified` |
| `voice_corpus_items` | 声音素材转写条目数 | **157** | 已下载并完成转写的音频/视频单集数，跨 18 个系列 | `data\voice_corpus.json#items` |
| `voice_corpus_chars` | 声音素材转写全文字数 | **171098** | 全部转写稿字符数（可检索语料规模） | `data\voice_corpus.json#items[].text` |
| `voice_corpus_minutes` | 声音素材总时长（分钟） | **926.1** | 已下载音频/视频的总时长 | `data\voice_corpus.json#counts` |
| `textmine_corpus` | 文本挖掘语料条数 | **5155** | wx_textmine 管线的 corpus.jsonl 条数，来自 6 个来源 | `E:\wx\wx_textmine_out\corpus.jsonl` |
| `textmine_events` | 文本挖掘抽取事件数 | **3590** | 从语料抽取的带日期事件（LLM 抽取，未经人工复核） | `E:\wx\wx_textmine_out\master_timeline.json` |
| `event_effects_edges` | 事件×歌曲 效应边数 | **32668** | 事件前后窗口的指数变化（baseline/post/effect_pct/spike_z/significant） | `E:\wx\wx_textmine_out\event_effects.json` |
| `media_library_files` | 声音素材库已下载媒体文件数 | **157** | 本地留存的音频/视频文件数（跨 20 个条目，18 个条目已下载） | `E:\wx\声音素材库\manifest\media_manifest.json` |
| `media_library_pending` | 声音素材库待采条目数 | **2** | 因平台限制未下载的条目（荔枝 63 集 / QQ音乐城市漫行 / 三体单曲 / 好梦时刻 等） | `E:\wx\声音素材库\manifest\media_manifest.json` |

## 常见误用

- ❌ 把 `song_archive`(748) 当作'追踪曲目'——追踪曲目是 `tracked_songs`(383)。
- ❌ 把 `tracked_links`(383) 与 `tracked_songs` 混为一谈——前者是链接单位。
- ❌ 用'60 场'或'65 场'描述巡演——正确是 `shows_tour`(59) 或 `shows_all`(64)。
- ❌ 跨平台比曲目数（QQ 池 vs 网易云）——平台口径不同，不可相加或相减。
