# 口径登记表（单一事实源 · 数字字典）

> 生成时间：2026-09-10 09:01　｜　生成脚本：`project_b/build_calibers.py`（幂等，部署时自动重跑）
>
> **纪律**：任何页面/论文/宣传材料引用数字，必须同时给出本表 id 与范围。
> 不同范围的数字**不是矛盾**，混用才是错误。场次数必须成对出现（全站 = 巡演 + 签唱会）。

| id | 名称 | 数值 | 范围 | 来源 |
|---|---|---|---|---|
| `tracked_songs` | 追踪曲目池 | **383** | 主动追踪并采集指数的曲目清单（池内） | `dashboard/dashboard_data.json` |
| `tracked_links` | 追踪链接数 | **383** | 同一首歌的多个平台链接（一首歌可有多条链接） | `dashboard/dashboard_data.json` |
| `entity_songs` | 关系图谱曲目 | **435** | 至少有一条关系（现场/小酒馆/专辑）的曲目 | `entity_index.json` |
| `songs_meta` | 歌曲元数据条目 | **586** | 含元信息（时长/专辑/发行等）的曲目 | `data/songs_meta.json` |
| `song_archive` | 歌曲档案条目 | **748** | 档案库收录的全部曲目条目（含未追踪/无指数） | `data/song_archive.json` |
| `credits_songs` | 署名/演职信息曲目 | **325** | 有公开演职/署名记录的曲目 | `data/credits_full.json` |
| `playable_songs` | 可试听曲目 | **117** | 站内提供试听入口的曲目 | `data/playable_songs.json` |
| `netease_songs` | 网易云曲库曲目 | **122** | 网易云音乐侧可核验曲目 | `data/netease_catalog.json` |
| `shows_all` | 全站场次 | **64** | 六轮巡演 + 签唱会等非巡演演出 | `data/cities.json（长表派生）` |
| `shows_setlists` | 有歌单记录的场次 | **64** | 长表中至少有 1 条曲目记录的场次 | `data/setlists.json` |
| `cities` | 巡演城市数 | **22** | 去重城市 | `data/cities.json` |
| `live_songs` | 有现场记录的曲目 | **302** | 至少在一个场次歌单中出现过的曲目 | `entity_index.json` |
| `kb_facts` | 知识库事实条数 | **1150** | 结构化事实 | `data/kb/manifest.json` |
| `kb_entities` | 知识库实体数 | **1416** | 人/歌/专辑/演出/城市等实体 | `data/kb/manifest.json` |
| `kb_relations` | 知识库关系数 | **1942** | 实体间关系 | `data/kb/manifest.json` |
| `semantic_docs` | 语义索引文档数 | **4702** | 可语义检索的文档块 | `data/kb/semantic/manifest.json` |
| `qa_pairs` | 问答对数量 | **315** | 可引用问答（GEO 资产） | `data/qa_bank.json` |
| `shows_tour` | 六轮巡演场次 | **59** | 一巡~六巡的巡演场次（不含签唱会） | `巡演歌单长表（单一事实源）` |
| `setlist_rows` | 歌单曲目记录行 | **1249** | 长表曲目行（含串烧拆分行前的原始记录） | `巡演歌单长表` |
| `setlist_songs_unique` | 歌单唯一曲目（数据层归一名） | **289** | 长表去重后的曲目名 | `巡演歌单长表` |
| `index_days` | 指数数据覆盖天数 | **1282** | 站点图表所用指数长表的实际覆盖天数 | `E:\wx\wx_textmine_out\music_index_long.csv` |

## 常见误用

- ❌ 把 `song_archive`(748) 当作'追踪曲目'——追踪曲目是 `tracked_songs`(383)。
- ❌ 把 `tracked_links`(383) 与 `tracked_songs` 混为一谈——前者是链接单位。
- ❌ 用'60 场'或'65 场'描述巡演——正确是 `shows_tour`(59) 或 `shows_all`(64)。
- ❌ 跨平台比曲目数（QQ 池 vs 网易云）——平台口径不同，不可相加或相减。
