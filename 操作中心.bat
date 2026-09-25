@echo off
title 王晰档案站 · 操作中心 (v3)
setlocal EnableExtensions
if "%op%"=="165" goto build_style_metrics
:menu
cls
echo ================================================================
echo   王晰 GEO 数字档案站 · 操作中心  (重构版 v2)
echo   说明: temp\运维SOP_新微博与评论处理.md
echo   备忘: temp\运维备忘_YYYYMMDD.md
echo ================================================================
echo.
echo.
echo  [A · 平台采集（本人/工作室/微博/小红书/B站）]
echo  ------------------------------------------------------------------------------
echo    1. 微博全量 - 王晰本人（文字+图片+视频）
echo    2. 微博全量 - 王晰工作室
echo    3. 微博抓取 - 仅文字图片
echo    4. 微博本地网页快照
echo    5. 同步 wb.txt Cookie
echo    6. 小红书全量 - 王晰主页
echo    7. 小红书按链接抓取 - 视频+图文
echo    8. 小红书按链接抓取 - 仅文字图片
echo    9. 小红书 summary 重建
echo    10. B站全量 - 王晰空间
echo    11. B站下载+摘要 - 视频+文字
echo    12. B站仅文字摘要
echo.
echo  [B · 演出反馈 / 评论 / 歌单]
echo  ------------------------------------------------------------------------------
echo    13. 观众反馈收集（微博+小红书+B站+Bing）
echo    14. 反馈入库 live 页
echo    15. 歌单候选（反馈反推歌名）
echo    16. 演出反馈一周工作流
echo    17. 追踪报告入库
echo    18. 微博手动正文入库
echo    19. 评论多层面分析（默认广州场）
echo    20. 小红书入库（按歌曲归类）
echo    21. 广州整理摘录重渲染
echo    22. 更新 live-reviews
echo    23. B站翻页补收
echo    24. 歌单重建（长表＞setlists.json+页）
echo    25. 场次标记已举办 + 大屏 rebuild
echo.
echo  [C · 转写与内容加工]
echo  ------------------------------------------------------------------------------
echo    26. 转写 txt 导入 + ASR 纠错
echo    27. 转写加工 - DeepSeek 后处理
echo    28. 转写预筛 + 待审清单
echo    29. 转写合并
echo.
echo  [D · 页面重建 / 地图 / 知识库]
echo  ------------------------------------------------------------------------------
echo    30. 地图 + 巡演目录重建
echo    31. 首页重建 + 动态更新
echo    32. 重建知识库图谱
echo    33. 重建语义索引 (bge-small-zh)
echo    34. 打开语义检索页
echo.
echo  [E · 档案 / 论文 / 研究]
echo  ------------------------------------------------------------------------------
echo    35. 打开论文素材索引
echo    36. 打开论文草稿目录
echo    37. 打开预测实验档案
echo    38. 预测最终验证 P001
echo.
echo  [F · 部署 / Git / 运维]
echo  ------------------------------------------------------------------------------
echo    39. 完整部署 deploy_all（全流水线+commit+IndexNow，末尾自动口径/导航/结构化数据/bat 把关）
echo    40. IndexNow 通知 only
echo    41. 全链路 auto_update
echo    42. git 手动 push
echo    43. git 状态查看
echo.
echo  ------------------------------------------------------------------------------
echo.
echo  [G · 档案一键生成（口径基线 + 全量年度卡）]
echo  ------------------------------------------------------------------------------
echo    44. 档案一键全量（口径基线 + 全部年度卡 + digest）
echo    45. 仅重算口径与效应基线（第一张表）
echo    46. 仅生成全部年度档案卡
echo    47. 重启大屏监测 daemon（改生成器/模板后必做，内存旧模板会覆盖新页面）
echo    48. 大屏 HTML 三查（发布前结构自检）
echo    49. 命题卡+宣传词条摘要（data/archive_propositions.json）
echo    50. 矛盾扫描（event_effects x 年度表 x 微博行为）
echo.
echo  [H · 音域实测（人声分离 + F0 + 白皮书）]
echo  ------------------------------------------------------------------------------
echo    51. 音域一键（B站下载→人声分离→落盘F0）
echo    52. 音域谱生成（10曲→data/archive_vocal.json）
echo    53. 生成分享图文（长图+图文版HTML）
echo    54. 更新 voice.html 音域数据（含 IndexNow）
echo    55. 更新 analysis-board 展板
echo    ---- I组 口径与导航把关 ----
echo    56. 口径审计（单一事实源一致性自检）
echo    57. 口径登记表（data/calibers.json+md）
echo    58. 导航统一（顶部导航+底部全站索引）
echo    59. 导航与内链审计（孤儿页检查）
echo    60. 一键全部把关（口径+登记表+导航+批处理）
echo    61. 生成 llms.txt（计数从 manifest 派生，禁手写）
echo    62. 事件效应口径修正（同窗合并+去重叠+FDR）
echo    63. 打开核实记录与文献综述
echo    ---- J组 指数数据源（原始库/重算/诊断） ----
echo    64. 重建指数长表（00_build_matrix.py，含千分位修复）
echo    65. 重建原始库长表（build_index_raw_long.py）
echo    66. 指数数据源诊断（覆盖率+年度多口径对照）
echo    67. 指数数据源完整性守卫（防回退，退出码1=异常）
echo    68. 生成学术研究页（data/literature.json 转 academic.html）
echo    ---- K组 专辑音域全量实测 ----
echo    69. 下载专辑音频（七专辑+回望，QQ音乐320k）
echo    70. 专辑音域实测（分离+F0+多维指标，约12分钟）
echo    71. 生成专辑音域报告（报告+站点数据+voice.html）
echo    72. 添加待测曲目（搜索歌名写入待测清单）
echo    73. 一键音域实测（69到71全流程）
echo    74. 清理分离人声缓存（释放约2.9GB）
echo    ---- L组 情境对比（他主导 vs 他人主导） ----
echo    75. 抓取B站收藏夹清单（王晰综艺现场live）
echo    76. 下载他人主导音频（综艺/晚会/商演/饭拍）
echo    77. 情境对比分析（报告+箱线图+站点数据）
echo    78. 生成他人主导详细报告（分类明细+长图）
echo    79. 生成舞台实测页 stage.html
echo    ---- M组 口径复核与双重校验 ----
echo    80. 复核十曲严格口径（新旧口径逐曲对照）
echo    81. 匹配QQ官方版本（舞台素材同曲对照）
echo    82. 双重校验（舞台版 vs QQ官方版）
echo    83. 重绘十曲图（按现行口径）
echo    ---- N组 一致性与 GEO 资产维护 ----
echo    84. sitemap lastmod 自动回填（按 git，禁手写）
echo    85. 电梯定义句刷新（首页/问答库/llms/Person）
echo    86. 首页音域摘要块刷新（从实测 JSON 派生）
echo    87. 结构化数据审计（JSON-LD 语法/类型/纪律）
echo    88. 分享图重新生成 + 版本指纹（长图一致性）
echo    ---- O组 线上核验（审计线上化） ----
echo    89. 线上核验（图片200+sha256对指纹+数字一致+黑名单）
echo    ---- P组 音高交叉校验（CREPE） ----
echo    90. CREPE 交叉校验（排查 YIN 次谐波错误）
echo    91. 打开《向着太阳》重测报告
echo    92. 低音复核（LowC 及以下曲目：YIN 次谐波排查）
echo    93. 打开低音复核报告（LowC）
echo    ---- Q组 运维加固（2026-09-10 停摆事故后） ----
echo    94. 漏批看门狗（应完成批次 vs 产出，停摆则拉起+补跑）
echo    95. 更新重启抑制 - 查看状态（只读）
echo    96. 更新重启抑制 - 应用（活动时间06:00-23:00 + 暂停更新35天）
echo    97. 导出 BitLocker 恢复密钥 → D:\Bitlocer.txt
echo    98. 守护进程任务改 S4U（重启免解锁，先实测）
echo    99. 指数长表日期偏移核查（三重证据）
echo    ---- R组 补录与自检（2026-09-10 停摆事故配套） ----
echo    100. 按日补录与验收（输入日期，预检+重建+验收+口径自查）
echo    101. 看门狗自测（24 项，不触碰真实状态）
echo    102. 日期偏移影子验证（复用旁路表，出对照报告）
echo    103. 自动登录（方案甲）状态查看
echo    104. 补录后全链路重建与验收（长表→基线→年度卡→部署→四查）
echo    105. 指数日期映射口径（查看/试算/应用/回滚）
echo    106. 缺失日备用数据源（守护进程准终值，可生成日档案回填）
echo    107. 指数长表+基线刷新（日档案更新后跑；已接入每日 auto_update）
echo    108. 事故验收总检（根因/自愈/口径/数据/站点/任务/产物 一次性体检）
echo    109. 立刻补跑一次采集（全量/极速）+ 自动刷新长表基线
echo    110. B站轨迹素材采集（同曲多版本，本地零 token）
echo    111. 导出轨迹素材清单（md 清单 + 待测链接 txt）
echo    112. 场次音域实测一键（B站音轨到 wav 到 分离测音 到 双标准报告）
echo    113. 低音读数复核与终裁（CREPE 多配置稳健性 到 谱列解释度 到 四轨归属）
echo    114. 事实预检（facts_registry：专辑年份/履历/赛事/换算 生成前强制过一遍）
echo   [S 组 声学自动化（已接入每日自动链路，此处仅手动触发）]
echo    115. 音域三页数据同步（输入有变化才跑生产脚本，幂等）
echo    116. 每日唱功卡片（生成/回填 + 本地传记素材归档 + 社交短文案）
echo    117. 每晚声学增量（新场次素材：下载 到 分离测音 到 回写现场层）
echo    119. 专辑发行日期核验（QQ音乐 publicTime 到 release_date 精确日期）
echo    120. 活动生命周期追踪（官宣/开票/开演的指数前后窗口，自动回填）
echo    121. 公众号文章留存 + 离线OCR（原文快照/图片/逐图文本 到 Markdown）
echo    122. 任务登记表重派生（菜单/部署/计划任务 三源合一 到 pipeline_registry.json）
echo    123. 任务一致性审计（登记表 vs 部署 vs 菜单 vs 计划任务，漂移 exit 1）
echo    124. raw_archive 保留策略（默认试算；--apply 才删）
echo    125. 声学长表与复核台账（vocal_measurements + verify_ledger 构建/校验/查询）
echo    126. 补搜巡演曲目池（按巡次缺口扩池，让五巡等覆盖慢慢补全）
echo    127. 歌迷赏析入站（本地转Markdown + 索引 + 学术研究页第七节）
echo    128. 录音室层重测（人工确认：全新分离重跑 72 曲 + 出报告；默认不自动跑）
echo    129. 网易云独有曲目取源 + 实测（网易云有、QQ 无的曲目）
echo    130. 低音复核工具组（伴奏静音窗口扫描 + 人声轨低频扫描 + 混音终检）
echo    131. 低音带轨迹（通用：--file/--t0/--t1/--lo/--hi，任意素材/窗口/频带）
echo    132. 歌迷赏析摘录入站（首页听众说 + 歌曲库赏析入口 + 巡演页；数据 data/essay_quotes.json）
echo    133. 社媒出图（低音实测 6 张，含页脚署名，幂等）
echo    ---- T组 声音素材库（下载/转写/语料/分析，媒体仅本地留存） ----
echo    134. 声音素材库总览（媒体清单 + 出处/URL 核验，幂等）
echo    135. 下载 B站/微博 媒体（yt-dlp，音频轨）
echo    136. 下载 喜马拉雅 读诗（公开直链接口）
echo    137. 采集 网易云 DJ 电台（31 期，可选下载）
echo    138. 采集 QQ音乐「城市漫行」（26 期，含音频直链）
echo    139. 采集 荔枝FM「低音时间」（59 期，含音频直链）
echo    140. 补齐 ELLE007 发布日期（微博 upload_date，不推算）
echo    141. 批量转写（faster-whisper large-v3 本地 GPU）
echo    142. 声音语料整合（到 data/voice_corpus.json）
echo    143. 语料同步进 textmine 语料库（按正文指纹判重，幂等）
echo    144. 语料文本分析（主题/情感/人称/金句）
echo    145. 声音 × 指数 × 声学 交叉分析（传记三主线）
echo    146. 并入知识库（voice_series/voice_episode + 事实关系）
echo    147. ASR 人名错字校正（王熙到王晰等，只改确证错字）
echo    148. 维护者预设审计（说明书与站点口径一致）
echo    149. 声音素材全链路一键（134到146 依次执行）
echo    150. 操作中心覆盖审计（含反向检查：可运行脚本无入口则报警；--strict 严格）
echo    ---- U组 审计与内容补齐（2026-09-15 接入原孤儿脚本） ----
echo    151. 舞台排除项回归审计（防已排除素材/错误曲名被生成器回吞上线）
echo    152. 存量音源码率审计（逐文件算真实码率，不信标称）
echo    153. 专辑层复核状态生成（A3 终裁到 data/album_verify_status.json）
echo    154. 小酒馆金句并入首页金句墙（锚点自适应，幂等）
echo    155. 小酒馆「有价值摘要」提取（?? 调 DeepSeek API，按量计费）
echo    156. 小酒馆摘要版 ep 页重建（全文页换摘要版，全文已备份本地）
echo    157. 低音谐波列复核（原始混音谐波列；1f0/3f0 缺失即判次谐波）
echo    158. 高音区倍频复核（对称闸门：抓 YIN 锁 2 次谐波"报高八度"）
echo    159. 听辨台账回填（人耳定案写回 data/listening_verdicts.json）
echo    160. 听辨定案后重建（跑覆盖 → 巡演报告 → stage.html → 导航）
echo    161. 汇总明细一致性审计（防未复核值被当结论）
echo    162. 听辨样本切制（待复核读数切 6~8 秒小段送人耳）
echo    163. 辩音总档生成（传记素材：前史+正本+裁决台账合并）
echo    164. 专辑层高音区复核（极值读数必须过人耳）
echo    165. 风格指标生成（打两份工 / 低音亮度，可复算）
echo    166. 整场纵向分析（拱形结构 / 音区不漂移，读已有 F0）
echo    167. talk 批量转写（whisper，选目录出 txt+segments）
echo    168. 数据仓库重建（站点 JSON → DuckDB 单文件，101 表）
echo    169. 原始素材无损压缩（WAV→FLAC，默认试算）
echo    170. 原始视频省空间（HEVC 重编码，默认试算）
echo    171. 整场按曲目切分（掌声 / 能量谷 / f0 断裂）
echo    172. 归因检验报告（四问 + 多重比较校正）
echo    173. 追踪池核查与扩容（歌单唱过 vs 源表追踪，可 --apply 写入）
echo    174. 曲目谱系（翻唱档案：293 首选曲行为结构化）
echo    175. 翻唱价值分析（选曲指纹 / 同曲多版本方差 / 音区适配 / 语言跨度 / 自有vs翻唱 DiD）
echo    176. 场次覆盖索引（有实测 vs 有素材 两口径 + 待采清单）
echo    177. 缺口场次补录（按 轨迹\场次下载清单_缺口补录_*.json 下载→实测→并入现场层）
echo    178. 有视频场次清单（逐场列视频文件/BV/体积；未挂载盘自动提示）
echo    179. 场次认领（把现场素材逐条归属到具体场次：日期/BV/歌单指纹）
echo    180. 长声表 × 否决台账反连接（同音区存疑移出榜单，防女和声污染）
echo    181. 注入审计（结果指纹版：首页事实/听众说/vocal音域摘要/长声章 是否真落地）
echo    182. 曲目缺口自动补闭环（补搜扩池→缺口优先下载/测量→聚合→回写站点数据）
echo    183. 视频音轨入库（自录/微博直拍视频 → 抽音轨 → 分离/F0 → 入库；G盘未挂载自动跳过）
echo    184. 待人耳确认清单（汇总台账待核+长声闸门，并自动切缺失样本）
echo    185. 音频资产台账（逐批次盘点：文件/体量/已分析/新增；进报告「资产台账」章）
echo    186. 声学探索·可写方向清单（可复算观测，含样本量与可信度分级，供传记取材）
echo    187. 横向素材积攒看板（微博/指数/语料/知识库/影像 是否同步增长 + 缺口告警）
echo    188. 写作专题三题（音域两端 / 颤音指纹 / 音区自觉；现象-方法-数字-反面证据-可引用句）
echo    189. 提取微博 cookie（联想浏览器一键：自动关浏览器→提取→重开）
echo    190. 颤音指纹专题页（topic-vibrato.html：八年漂移 0.27Hz 完整证据链）
echo    191. 微博登录态验证（1 个请求：login 是否 true / 是否被 432 风控）
echo    192. 生涯节点候选（文本挖掘事件→高置信去重候选，供人工策展，不直接上站）
echo    193. 自动关机豁免同步（节假日/调休自动识别；写入 shutdown_skip.txt）
echo    194. 声学×指数交叉分析（正向：哪些曲目指数在涨 / 与演唱能力的关联）
echo    0. 退出
echo.
set "op="
set /p op=  输入编号后回车: 
if "%op%"=="0" exit /b
if "%op%"=="" goto menu
if "%op%"=="1" goto wb_self
if "%op%"=="2" goto wb_studio
if "%op%"=="3" goto wb_novideo
if "%op%"=="4" goto wb_snapshot
if "%op%"=="5" goto wb_cookie_sync
if "%op%"=="6" goto xhs_user_full
if "%op%"=="7" goto xhs_fetch
if "%op%"=="8" goto xhs_links_novideo
if "%op%"=="9" goto xhs_rebuild
if "%op%"=="10" goto bili_space_full
if "%op%"=="11" goto bili_dl
if "%op%"=="12" goto bili_text
if "%op%"=="13" goto fb_collect
if "%op%"=="14" goto fb_repo
if "%op%"=="15" goto fb_candidate
if "%op%"=="16" goto fb_week
if "%op%"=="17" goto trk_import
if "%op%"=="18" goto wb_manual_import
if "%op%"=="19" goto an_analyze
if "%op%"=="20" goto xhs_import
if "%op%"=="21" goto gz_render
if "%op%"=="22" goto wb_live
if "%op%"=="23" goto bili_backfill
if "%op%"=="24" goto sl_build
if "%op%"=="25" goto sl_status
if "%op%"=="26" goto trans_ingest
if "%op%"=="27" goto trans_process
if "%op%"=="28" goto trans_precheck
if "%op%"=="29" goto trans_merge
if "%op%"=="30" goto map_rebuild
if "%op%"=="31" goto home_build
if "%op%"=="32" goto kb_build
if "%op%"=="33" goto kb_vectors
if "%op%"=="34" goto kb_semantic_page
if "%op%"=="35" goto paper_assets
if "%op%"=="36" goto paper_drafts
if "%op%"=="37" goto paper_predictions
if "%op%"=="38" goto pred_verify
if "%op%"=="39" goto dp_all
if "%op%"=="40" goto dp_indexnow
if "%op%"=="41" goto dp_auto
if "%op%"=="42" goto git_push
if "%op%"=="43" goto git_status
if "%op%"=="44" goto arch_full
if "%op%"=="45" goto arch_base
if "%op%"=="46" goto arch_cards
if "%op%"=="47" goto daemon_restart
if "%op%"=="48" goto dash_verify
if "%op%"=="49" goto prop_gen
if "%op%"=="50" goto contradiction_scan
if "%op%"=="51" goto vocal_one
if "%op%"=="52" goto vocal_digest
if "%op%"=="53" goto vocal_share
if "%op%"=="54" goto vocal_voice_page
if "%op%"=="55" goto analysis_board_upd
if "%op%"=="56" goto audit_caliber
if "%op%"=="57" goto build_calibers
if "%op%"=="58" goto build_nav
if "%op%"=="59" goto audit_nav
if "%op%"=="60" goto gate_all
if "%op%"=="61" goto gen_llms
if "%op%"=="62" goto fix_event_effect
if "%op%"=="63" goto open_records
if "%op%"=="64" goto rebuild_matrix
if "%op%"=="65" goto rebuild_raw_long
if "%op%"=="66" goto diag_index
if "%op%"=="67" goto index_guard
if "%op%"=="68" goto build_academic
if "%op%"=="69" goto dl_albums
if "%op%"=="70" goto analyze_albums
if "%op%"=="71" goto report_albums
if "%op%"=="72" goto add_song
if "%op%"=="73" goto one_click_vocal
if "%op%"=="74" goto clean_stems
if "%op%"=="75" goto fav_fetch
if "%op%"=="76" goto dl_other
if "%op%"=="77" goto ctx_compare
if "%op%"=="78" goto stage_report
if "%op%"=="79" goto stage_page
if "%op%"=="80" goto recheck10
if "%op%"=="81" goto qq_match
if "%op%"=="82" goto crosscheck
if "%op%"=="83" goto redraw10
if "%op%"=="84" goto sitemap_lm
if "%op%"=="85" goto elev_def
if "%op%"=="86" goto vocal_sum
if "%op%"=="87" goto audit_ld
if "%op%"=="88" goto idcard
if "%op%"=="89" goto audit_live
if "%op%"=="90" goto crepe_check
if "%op%"=="91" goto open_sun_report
if "%op%"=="92" goto lowc_check
if "%op%"=="93" goto open_lowc_report
if "%op%"=="94" goto watchdog
if "%op%"=="95" goto harden_status
if "%op%"=="96" goto harden_apply
if "%op%"=="97" goto bitlocker_export
if "%op%"=="98" goto s4u_task
if "%op%"=="99" goto date_shift_check
if "%op%"=="100" goto backfill_day
if "%op%"=="101" goto watchdog_selftest
if "%op%"=="102" goto shadow_verify
if "%op%"=="103" goto autologon_status
if "%op%"=="104" goto rebuild_chain
if "%op%"=="105" goto index_mapping
if "%op%"=="106" goto fallback_day
if "%op%"=="107" goto refresh_index
if "%op%"=="108" goto acceptance_check
if "%op%"=="109" goto run_batch_now
if "%op%"=="110" goto bili_traj
if "%op%"=="111" goto bili_traj_export
if "%op%"=="112" goto stage_vocal_series
if "%op%"=="113" goto low_note_verify
if "%op%"=="114" goto facts_preflight
if "%op%"=="115" goto vocal_sync
if "%op%"=="116" goto skill_card
if "%op%"=="117" goto nightly_vocal
if "%op%"=="119" goto album_dates
if "%op%"=="120" goto event_lifecycle
if "%op%"=="121" goto wx_article
if "%op%"=="122" goto pipeline_seed
if "%op%"=="123" goto pipeline_audit
if "%op%"=="124" goto prune_raw
if "%op%"=="125" goto vocal_table
if "%op%"=="126" goto tour_pool
if "%op%"=="127" goto fan_essays
if "%op%"=="128" goto album_remeasure
if "%op%"=="129" goto netease_extra
if "%op%"=="130" goto low_recheck
if "%op%"=="131" goto low_band_traj
if "%op%"=="132" goto essay_quotes
if "%op%"=="133" goto social_figs
if "%op%"=="134" goto media_manifest
if "%op%"=="135" goto media_dl
if "%op%"=="136" goto media_xmly
if "%op%"=="137" goto media_netease
if "%op%"=="138" goto media_qq
if "%op%"=="139" goto media_lizhi
if "%op%"=="140" goto media_elle
if "%op%"=="141" goto media_trans
if "%op%"=="142" goto media_corpus
if "%op%"=="143" goto media_sync
if "%op%"=="144" goto media_analyze
if "%op%"=="145" goto media_cross
if "%op%"=="146" goto media_kb
if "%op%"=="147" goto media_asrfix
if "%op%"=="148" goto audit_preset
if "%op%"=="149" goto media_all
if "%op%"=="150" goto audit_ops
if "%op%"=="151" goto audit_stage_exc
if "%op%"=="152" goto audit_bitrate
if "%op%"=="153" goto album_verify
if "%op%"=="154" goto tavern_quotes
if "%op%"=="155" goto tavern_summary
if "%op%"=="156" goto tavern_ep
if "%op%"=="157" goto low_harmonic
if "%op%"=="158" goto high_harmonic
if "%op%"=="159" goto listen_ledger
if "%op%"=="160" goto listen_rebuild
if "%op%"=="161" goto audit_consistency
if "%op%"=="162" goto make_review_clips
if "%op%"=="163" goto build_debate_archive
if "%op%"=="164" goto make_review_clips
if "%op%"=="166" goto show_arc
if "%op%"=="167" goto talk_batch
if "%op%"=="168" goto build_warehouse
if "%op%"=="169" goto archive_flac
if "%op%"=="170" goto archive_hevc
if "%op%"=="171" goto segment_concert
if "%op%"=="172" goto attribution
if "%op%"=="173" goto expand_pool
if "%op%"=="174" goto cover_catalog
if "%op%"=="175" goto cover_analysis
if "%op%"=="176" goto coverage_index
if "%op%"=="177" goto gap_backfill
if "%op%"=="178" goto video_shows
if "%op%"=="179" goto show_assign
if "%op%"=="180" goto longnotes_verdict
if "%op%"=="181" goto audit_inject
if "%op%"=="182" goto gap_loop
if "%op%"=="183" goto video_ingest
if "%op%"=="184" goto pending_review
if "%op%"=="185" goto audio_assets
if "%op%"=="186" goto explore
if "%op%"=="187" goto streams
if "%op%"=="188" goto deepdives
if "%op%"=="189" goto get_cookie
if "%op%"=="190" goto vibtopic
if "%op%"=="191" goto check_login
if "%op%"=="192" goto tl_cand
if "%op%"=="193" goto hol_skip
if "%op%"=="194" goto cross_ai
echo   [!] 无效选项，请重试
timeout /t 1 /nobreak >nul
goto menu
:wb_self

cls

echo === 微博抓取 - 王晰本人 (断点续传, 只抓新的) ===

cd /d "E:\wx\私有工具\weibo_proxy"


python -X utf8 weibo_proxy.py fetch


echo.

echo 存档: E:\wx\私有工具\weibo_archive\posts + media

echo 提示: 抓完可执行 3(快照) 和 4(更新live-reviews)

pause

goto menu



:wb_studio

cls

echo === 微博抓取 - 王晰工作室 (关键词过滤) ===

cd /d "E:\wx\私有工具\weibo_proxy"


python -X utf8 weibo_proxy_studio.py fetch --all


echo.

echo 存档: E:\wx\私有工具\weibo_archive_studio\posts + media

pause

goto menu



:wb_snapshot

cls

echo === 本地网页快照生成 (增量) ===

cd /d "D:\wx409.github.io"


python -X utf8 project_b\run_weibo_snapshot.py --once


echo.

echo 输出: E:\wx\私有工具\weibo_snapshots\posts\^<YYYY-MM^＞\^<mid^＞.html

pause

goto menu



:wb_live

cls

echo === 更新 live-reviews.html ===

echo 前提: 先在 data\tour_weibo_posts.json 的 matched_to_shows 追加新记录

echo       (sourceType 决定本人=纯文字 / 工作室=可留链接)

cd /d "D:\wx409.github.io"


python -X utf8 project_b\update_live_reviews_tourweibo.py


echo.

echo 下一步: 提交推送(13) + IndexNow(11)

pause

goto menu



:fb_collect

cls

echo === 观众反馈收集 (微博+小红书+B站+Bing) ===
echo [提示] 微博/小红书风控高，可能等待较久；若出现 HTTP 432 请冷却后重试。
echo 快速首次收集: python project_b\collect_show_feedback.py --date 日期 --city 城市 --skip-bili
echo B站补收: 操作中心 33 或加 --bili-only

set /p fdate=请输入演出日期(YYYY-MM-DD, 如2026-08-23): 

set /p fcity=请输入城市(如 广州): 

if "%fdate%"=="" goto fb_collect

if "%fcity%"=="" goto fb_collect


python -X utf8 D:\wx409.github.io\project_b\collect_show_feedback.py --date %fdate% --city %fcity%


echo.

echo 结果: E:\wx\私有工具\show_feedback\

pause

goto menu



:fb_repo

cls

echo === 反馈入库 live 页 (短句+外链, 自动commit+push) ===

set /p fdate=请输入演出日期(YYYY-MM-DD): 

set /p fcity=请输入城市: 

set /p fpage=请输入live页路径(如 live\hui-回-广州-2026.html): 

if "%fdate%"=="" goto fb_repo

if "%fcity%"=="" goto fb_repo

if "%fpage%"=="" goto fb_repo


python -X utf8 D:\wx409.github.io\project_b\build_show_repo.py --date %fdate% --city %fcity% --page %fpage%


pause

goto menu



:fb_candidate

cls

echo === 歌单候选 (反馈反推歌名) ===

set /p fdate=请输入演出日期(YYYY-MM-DD): 

set /p fcity=请输入城市: 

if "%fdate%"=="" goto fb_candidate

if "%fcity%"=="" goto fb_candidate


python -X utf8 D:\wx409.github.io\project_b\build_repo_setlist_candidates.py --date %fdate% --city %fcity%


pause

goto menu



:sl_build

cls

echo === 歌单重建: 长表 ^＞ setlists.json + live/setlists.html ===

echo 前提: 正确歌单已写入长表

echo    E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx

cd /d "D:\wx409.github.io"


python -X utf8 project_b\build_setlists.py

python -X utf8 project_b\build_setlists_page.py


pause

goto menu



:sl_status

cls

echo === 场次标记已举办 + 大屏 rebuild ===

cd /d "D:\wx409.github.io"


python -X utf8 project_b\update_show_status.py --rebuild


pause

goto menu



:dp_all

cls

echo === 完整部署 deploy_all (全流水线生成 + 把关 + commit + IndexNow) ===

cd /d "D:\wx409.github.io"


python -X utf8 project_b\deploy_all.py


echo.

echo 注意: deploy_all 只本地 commit, 需手动 push(13)

pause

goto menu



:dp_indexnow

cls

echo === IndexNow 通知 only ===

cd /d "D:\wx409.github.io"


python -X utf8 project_b\deploy_all.py --notify-only


pause

goto menu



:dp_auto

cls

echo === 全链路 auto_update (watch-deploy-push-indexnow-通知) ===

cd /d "D:\wx409.github.io"


python -X utf8 project_b\auto_update.py --machine laptop --watch


pause

goto menu



:trk_import

cls

echo === 追踪报告入库 (实时追踪md ^＞ live-reviews) ===

echo 读: temp\演出追踪_20260823\实时反馈_手动收集.md

echo 写: data/live_repos.json + live-reviews.html (自动去重)

cd /d "D:\wx409.github.io"


python -X utf8 project_b\import_tracking_repo.py


echo.

echo 提示: 提交推送用 13, 催搜索引擎用 11

pause

goto menu



:xhs_fetch

cls

echo === 小红书按链接抓取 (links.txt ^＞ 本地) ===

echo 前置: 链接文件 D:\wx409.github.io\temp\xhs_links.txt (每行一个分享链接)

echo       cookie 优先读 E:\wx\index_records\xhs.txt

echo 存档: E:\wx\私有工具\xhs_archive\按链接\


python -X utf8 E:\wx\私有工具\xhs_proxy\fetch_xhs_links.py --file "D:\wx409.github.io\temp\xhs_links.txt"


echo 提示: 抓完可执行 18(入库)

pause

goto menu



:xhs_import

cls

echo === 小红书入库 (纯文字 无链接 无id 20字以上) ===

echo 读: E:\wx\私有工具\xhs_archive\_by_links_summary.json

echo 写: live-reviews.html (纯文字, 幂等)

cd /d "D:\wx409.github.io"


python -X utf8 project_b\import_xhs_songs.py


echo --- 渲染歌曲分区 ---


python -X utf8 project_b\render_xhs_songs.py


echo 提示: 提交推送用 13, 催搜索引擎用 11

pause

goto menu



:gz_render
cls
echo === 广州整理摘录重渲染 ===
echo 改完 temp\_gz_quotes.json 后跑本项，重写 live-reviews 广州评论区
cd /d "D:\wx409.github.io"
python -X utf8 project_b\render_gz_quotes.py
echo 提示: 提交推送用 13
pause
goto menu

:xhs_rebuild
cls
echo === 小红书 summary 重建 ===
echo 用途: fetch 中断后 summary 被最后一次运行覆盖，从归档目录重建完整汇总
python -X utf8 project_b\run_xhs_rebuild.py
echo 之后可执行 18(入库)
pause
goto menu

:an_analyze
cls
echo === 评论多层面分析 (论文友好) ===
echo 聚合微博/小红书/B站/Bing 评论: 高频主题/独特观点/评价维度/情感/画像/格言
echo 默认: 广州 2026-08-23; 加 --llm 启用 DeepSeek 归纳层 (需 temp\deepseek_key.json)
cd /d "D:\wx409.github.io"
python -X utf8 project_b\analyze_audience_comments.py --date 2026-08-23 --city 广州
echo 输出: temp\audience_analysis\2026-08-23_广州.json + .md
pause
goto menu

:xhs_user_full
cls
echo === 小红书全量 - 王晰主页 (视频+图文) ===
cd /d "E:\wx\私有工具\xhs_proxy"
python -X utf8 fetch_xhs_user.py
echo 归档: E:\wx\私有工具\xhs_archive\官方账号\王晰\
pause
goto menu

:bili_space_full
cls
echo === B站全量 - 王晰空间 (视频+文字) ===
echo 注意: 空间抓取需 B站登录 Cookie (E:\wx\index_records\bilibili_cookies.txt)
echo       未配置时请把空间视频链接逐条加入 bilibili链接.txt 后走选项26
cd /d "D:\wx409.github.io"
python -X utf8 project_b\download_bilibili.py --space 3493257487059302
pause
goto menu

:wb_novideo
cls
echo === 微博抓取 - 仅文字图片 (本人+工作室, 跳过视频) ===
cd /d "E:\wx\私有工具\weibo_proxy"
python -X utf8 weibo_proxy.py fetch --no-video
python -X utf8 weibo_proxy_studio.py fetch --no-video
pause
goto menu

:xhs_links_novideo
cls
echo === 小红书按链接抓取 - 仅文字图片 ===
echo 前置: D:\wx409.github.io\temp\xhs_links.txt (每行一个分享链接)
cd /d "D:\wx409.github.io"
python -X utf8 E:\wx\私有工具\xhs_proxy\fetch_xhs_links.py --file "D:\wx409.github.io\temp\xhs_links.txt" --no-video
echo 提示: 抓完可执行 18(入库)
pause
goto menu

:bili_dl
cls
echo === B站下载+摘要 - 视频+文字 ===
echo 前置: E:\wx\六巡\20260823广州站\bilibili链接.txt (每行一个链接/BV号)
cd /d "D:\wx409.github.io"
python -X utf8 project_b\download_bilibili.py
echo 输出: E:\wx\六巡\20260823广州站\bilibili视频\
pause
goto menu

:bili_text
cls
echo === B站仅文字摘要 - 不下视频 ===
cd /d "D:\wx409.github.io"
python -X utf8 project_b\download_bilibili.py --no-download
echo 输出: bilibili_summary.md (标题/UP主/时长/简介)
pause
goto menu

:trans_process
cls
echo === 转写加工 - DeepSeek 后处理 ===
echo 提示词: project_b\prompts\transcript_postprocess.md
echo 步骤: 0) 也可先规则提取金句(零token): pipeline --extract-quotes 原始JSON
echo 步骤: 1) v4 转写工具产出原始JSON(句级时间戳)
echo       2) 按提示词用 DeepSeek 加工 -＞ quotes/faqs/timeline/conflicts
echo       3) 加工JSON存到 temp\transcripts_review\ 后跑 29
cd /d "D:\wx409.github.io"
pause
goto menu

:trans_precheck
cls
echo === 转写预筛+待审清单 ===
set /p tpath=请输入加工JSON路径(可多个空格分隔, 回车重输): 
if "%tpath%"=="" goto trans_precheck
cd /d "D:\wx409.github.io"
python -X utf8 project_b\transcript_pipeline.py --precheck %tpath%
echo 清单: temp\transcripts_review\review.md (人工打勾后跑 30)
pause
goto menu

:trans_merge
cls
echo === 转写合并 - 审核通过项 ===
cd /d "D:\wx409.github.io"
python -X utf8 project_b\transcript_pipeline.py --merge
echo 合并目标: live_repos/quotes/timeline/qa_bank/data\tour 单场簇
pause
goto menu

:trans_ingest
cls
echo === 转写txt导入 + ASR专有名词纠错 ===
echo 输入: 清洗后的talk文本(.txt); 自动应用14组专有名词纠错(王露斌→王洛宾等)
set /p tpath=请输入txt路径: 
if "%tpath%"=="" goto trans_ingest
set /p tdate=请输入演出日期(如 2026-08-23): 
set /p tvenue=请输入城市(如 广州): 
cd /d "D:\wx409.github.io"
python -X utf8 project_b\transcript_pipeline.py --ingest-txt "%tpath%" --date %tdate% --venue %tvenue%
echo 产物: temp\transcripts_review\^<文件名^＞.json (已纠错)
echo 之后: 28(DeepSeek加工/策展) 或 29(预筛审核) 或 --extract-quotes 规则金句
pause
goto menu

:map_rebuild

cls

echo === 地图+巡演目录重建 (长表单一事实源) ===

cd /d "D:\wx409.github.io"


python -X utf8 project_b\run_map_rebuild.py


echo.

echo 已更新: data/cities.json + map/index.html + live/index.html

echo 提示: 提交推送用 13, 催搜索引擎用 11

pause

goto menu



:git_push

cls

echo === git 手动 push ===

cd /d "D:\wx409.github.io"

git status -sb

echo.

git push origin main

pause

goto menu



:git_status

cls

echo === git 状态 ===

cd /d "D:\wx409.github.io"

git fetch origin

git status -sb

pause

goto menu

:wb_cookie_sync
cls
echo === 同步微博 Cookie (wb.txt ^＞ 3处抓取工具) ===
echo 源: E:\wx\index_records\wb.txt
echo 目标: weibo_cookies.txt / weibo_proxy/weibo_cookie.json / realtime_cookies/weibo_cookie.json
cd /d "D:\wx409.github.io"
python -X utf8 tools\sync_weibo_cookie.py
pause
goto menu

:wb_manual_import
cls
echo === 微博手动正文入库 (匿名化, 按mid去重) ===
echo 输入: wb链接（复制正文文字）.txt (每段: 日期行 + 正文 + weibo链接)
set /p fdate=请输入演出日期(YYYY-MM-DD, 如 2026-08-23): 
set /p fcity=请输入城市(如 广州): 
set /p wbfile=请输入正文txt路径(回车用默认): 
if "%fdate%"=="" goto wb_manual_import
if "%fcity%"=="" goto wb_manual_import
if "%wbfile%"=="" set "wbfile=E:\wx\六巡\20260823广州站\wb链接（复制正文文字）.txt"
python -X utf8 D:\wx409.github.io\project_b\import_wb_manual.py --date %fdate% --city %fcity% --file "%wbfile%"
echo --- 入库 live 页 ---
set /p fpage=请输入live页路径(回车默认 live\hui-回-广州-2026.html): 
if "%fpage%"=="" set "fpage=live\hui-回-广州-2026.html"
python -X utf8 D:\wx409.github.io\project_b\build_show_repo.py --date %fdate% --city %fcity% --page %fpage% --no-push
echo 下一步: 提交推送(13) + IndexNow(11); 评论分析(21)
pause
goto menu

:bili_backfill
cls
echo === B站翻页补收 (演出后UGC, 最新排序) ===
echo 说明: 默认按最新发布3页, 自动排除本站档案账号, 复用B站登录cookie翻更深
set /p fdate=请输入演出日期(YYYY-MM-DD): 
set /p fcity=请输入城市(如 广州): 
if "%fdate%"=="" goto bili_backfill
if "%fcity%"=="" goto bili_backfill
python -X utf8 D:\wx409.github.io\project_b\collect_show_feedback.py --date %fdate% --city %fcity% --bili-only --bili-pages 3 --bili-order pubdate
echo 结果: E:\wx\私有工具\show_feedback\
echo 下一步: 入库 live 页(6) + 评论分析(21)
pause
goto menu

:home_build
cls
echo === 首页重建 + 动态更新 (五层架构) ===
cd /d "D:\wx409.github.io"
python -X utf8 D:\wx409.github.io\project_b\build_home.py --rebuild
python -X utf8 D:\wx409.github.io\update_index_table.py
python -X utf8 D:\wx409.github.io\project_b\build_home.py --dynamic-only
echo 完成。下一步: 提交推送(13) + IndexNow(11); 日常动态更新已含在选项12/10自动流程
pause
goto menu

:paper_assets
cls
echo === 论文素材索引 ===
start "" "E:\wx\论文素材_王晰作传\数据资产索引.md"
pause
goto menu

:paper_drafts
cls
echo === 论文草稿目录 ===
start "" "E:\wx\论文素材_王晰作传\论文草稿"
pause
goto menu

:paper_predictions
cls
echo === 预测实验档案 ===
start "" "D:\wx409.github.io\temp\预测实验.md"
start "" "D:\wx409.github.io\temp\预测实验\predictions.json"
pause
goto menu

:kb_build
cls
echo === 重建知识库 ===
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_kb_graph.py
echo 知识库已重建: data/kb/*.json + qa_bank 扩充
pause
goto menu

:kb_vectors
cls
echo === 重建知识库语义索引 ===
cd /d "D:\wx409.github.io"
python -X utf8 tools\build_kb_vectors.py
echo 语义索引已重建: data/kb/semantic/*
pause
goto menu

:kb_semantic_page
cls
echo === 打开语义检索页 ===
start "" https://wx409.github.io/search.html?kb=1
pause
goto menu

:pred_verify
cls
echo === 预测最终验证 P001 六巡回广州站 ===
cd /d "D:\wx409.github.io"
python -X utf8 "temp\预测实验\verify_prediction.py" --id P001 --dry
echo.
echo 以上为预览(未写回)。确认后窗口(08-24~08-30)数据完整后正式定论:
set /p ok=窗口数据完整? 输入 y 正式定论, 回车退出: 
if /i "%ok%"=="y" python -X utf8 "temp\预测实验\verify_prediction.py" --id P001
echo 完成。定论已写入 temp\预测实验\predictions.json (verification_log final)
pause
goto menu

:fb_week
cls
echo === 演出反馈一周工作流 (收集-入库-归档-分析-KB-发布) ===
set /p fdate=演出日期(YYYY-MM-DD, 回车=2026-08-23): 
set /p fcity=城市(回车=广州): 
if "%fdate%"=="" set fdate=2026-08-23
if "%fcity%"=="" set fcity=广州
python -X utf8 project_b\feedback_week.py --date %fdate% --city %fcity%
echo 完成: live页反馈+全文归档+评论分析+KB评论维度, 已commit+push+IndexNow
pause
goto menu
:arch_full
cls
echo  [档案一键全量生成] 口径基线 + 年度卡 + digest ...
cd /d "E:\wx\论文素材_王晰作传\基线口径"
python -X utf8 compute_baseline_v1.py
python -X utf8 generate_year_cards.py
echo.
echo  [OK] 年度卡见 档案卡\年度\ ; digest -＞ data\archive_digest.json
pause
goto menu

:arch_base
cls
cd /d "E:\wx\论文素材_王晰作传\基线口径"
python -X utf8 compute_baseline_v1.py
echo  [OK] 基线已重算（年度表/效应/第一张表md）
pause
goto menu

:arch_cards
cls
cd /d "E:\wx\论文素材_王晰作传\基线口径"
python -X utf8 generate_year_cards.py
echo  [OK] 年度卡已全部重新生成
pause
goto menu

:daemon_restart
cls
echo  [重启大屏监测 daemon] 先停止计划任务再启动（加载最新生成器代码与模板）
schtasks /End /TN QQMusicDashboardAutoStart
timeout /t 2 /nobreak >nul
schtasks /Run /TN QQMusicDashboardAutoStart
echo  [OK] 已重启 daemon，启动时会自动 rebuild 一次看板（含当月榜单/档案层）
pause
goto menu

:dash_verify
cls
echo  [大屏 HTML 三查] style 配对 / head 无裸文本 / body 位置
python -X utf8 D:\wx409.github.io\tools\verify_dashboard.py
echo  [提示] 退出码 0 = 结构完好，可放心 push
pause
goto menu

:prop_gen
cls
echo  [命题卡+宣传词条摘要] 扫描 档案卡\命题卡\*.md 生成 data/archive_propositions.json
cd /d E:\wx\论文素材_王晰作传\基线口径
python -X utf8 generate_propositions.py
echo  [OK] 已生成 data\archive_propositions.json（大屏档案层\命题卡层读取）
pause
goto menu

:contradiction_scan
cls
echo  [矛盾扫描] event_effects x 年度表 x 微博行为 生成 矛盾扫描_日期.md
cd /d E:\wx\论文素材_王晰作传\基线口径
python -X utf8 矛盾扫描器.py
echo  [OK] 互斥信号已列出，供命题卡选题
pause
goto menu


:vocal_one
cls
echo  [音域一键] B站下载-人声分离-落盘F0（需先填 音域分析ilibili链接.txt）
cd /d E:\wx\论文素材_王晰作传\音域分析
echo  步骤1: 下载B站视频
python -X utf8 D:\wx409.github.io\project_b\download_bilibili.py ".ilibili链接.txt"
echo  步骤2: 对下载目录逐首 分离+落盘（见 批量下载分离分析.py）
python -X utf8 批量下载分离分析.py
echo  [OK] 已分离并落盘 F0 到 分析结果\ 目录
pause
goto menu

:vocal_digest
cls
echo  [音域谱生成] 10曲最低音 生成 data/archive_vocal.json
cd /d E:\wx\论文素材_王晰作传\基线口径
python -X utf8 generate_vocal.py
echo  [OK] 已生成 data\archive_vocal.json（大屏档案层音域谱读取）
pause
goto menu

:vocal_share
cls
echo  [生成分享图文] 长图+图文版HTML（歌迷向）
cd /d E:\wx\论文素材_王晰作传\音域分析
python -X utf8 生成分享图文.py
echo  [OK] 见 音域分析\分享\ 下 总结长图_竖版.png / 王晰音域实测_图文版.html 等
pause
goto menu

:vocal_voice_page
cls
echo  [更新 voice.html] 重跑音域谱 + 页面 + 首页摘要 + 口径校验
cd /d "E:\wx\论文素材_王晰作传\基线口径"
python -X utf8 generate_vocal.py
python -X utf8 generate_voice_page.py
cd /d "D:\wx409.github.io"
python -X utf8 project_b\inject_vocal_summary.py
python -X utf8 project_b\build_nav.py
python -X utf8 project_b\audit_caliber.py
echo  [OK] data\archive_vocal.json + voice.html + 首页音域摘要已更新
echo  发布: 菜单 39 完整部署，或 git push 后跑  python -X utf8 project_b\deploy_all.py --notify-only
pause
goto menu

:analysis_board_upd
cls
echo  [更新 analysis-board 展板] 演出带动分析页
echo  该页读 dashboard_data.json（tour_song_effects 84场），改内容在页面内手改
echo  位置: D:\wx409.github.io\dashboard\analysis-board.html
echo  完善方向: 顶部加音域结论卡(链接 voice.html) + 归因洞察更新
echo  改动后: git add dashboard/analysis-board.html 后 commit+push
pause
goto menu

:audit_caliber
cls
echo  [口径审计] 长表真值 vs cities/setlists/entity_index/story/llms
cd /d "D:\wx409.github.io"
python -X utf8 project_b\audit_caliber.py
echo  [提示] 退出码 0 = 全部一致；非 0 = 有口径漂移，必须修后再发布
pause
goto menu

:build_calibers
cls
echo  [口径登记表] 生成 data/calibers.json + data/calibers.md（数字字典）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_calibers.py
echo  [OK] 已生成 data\calibers.json 与 data\calibers.md
pause
goto menu

:build_nav
cls
echo  [导航统一] 顶部导航 + 底部全站索引（25页，幂等）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_nav.py
echo  [OK] 导航已统一；生成器重写页面后重跑本项即可恢复
pause
goto menu

:audit_nav
cls
echo  [导航与内链审计] 孤儿页 + 导航漂移
cd /d "D:\wx409.github.io"
python -X utf8 project_b\audit_nav.py
echo  [提示] 退出码 0 = 孤儿页 0 且导航一致
pause
goto menu

:gate_all
cls
echo  [一键把关] 口径 + 登记表 + 导航 + 批处理 + 结构化数据 + sitemap + 指数完整性 + 线上核验
cd /d "D:\wx409.github.io"
python -X utf8 project_b\audit_caliber.py
python -X utf8 project_b\build_calibers.py
python -X utf8 project_b\build_nav.py
python -X utf8 project_b\audit_nav.py
python -X utf8 project_b\audit_bat.py
python -X utf8 project_b\audit_jsonld.py
python -X utf8 project_b\audit_ops_coverage.py
python -X utf8 project_b\check_index_integrity.py
python -X utf8 project_b\update_sitemap_lastmod.py --check
python -X utf8 project_b\audit_live.py --skip-if-unpushed
echo.
echo  [OK] 全部完成（上面两个审计均应为 0 退出码）
pause
goto menu

:gen_llms
cls
echo  [生成 llms.txt] 计数从各 manifest 自动派生（禁手写数字）
cd /d "E:\wx\论文素材_王晰作传\基线口径"
python -X utf8 generate_llms.py
echo  [OK] 已生成 D:\wx409.github.io\llms.txt
echo  [提示] 内容或数据变更后重跑本项即可，数字自动同步
pause
goto menu

:fix_event_effect
cls
echo  [事件效应口径修正] 同窗合并 + 窗口去重叠 + BH-FDR + 非平稳标记
cd /d "E:\wx\论文素材_王晰作传\基线口径"
python -X utf8 事件效应口径修正.py
echo  [OK] 报告: 事件效应口径修正报告_20260909.md / 机读: 事件效应口径修正_20260909.json
pause
goto menu

:open_records
cls
echo  [打开核实记录与文献综述]
start "" "E:\wx\论文素材_王晰作传\档案卡\核实记录_求学履历_20260909.md"
start "" "E:\wx\论文素材_王晰作传\文献综述\文献综述_外部检索_v1.md"
start "" "E:\wx\论文素材_王晰作传\第一性原理总检报告_20260908.md"
pause
goto menu

:rebuild_matrix
cls
echo  [重建指数长表] 从原始库重建 music_index_long.csv（已修千分位逗号缺陷）
echo  源: E:\wx\指数数据库\增补数据库2025.2.22- （含 archived）+ download + 指数vs
cd /d "E:\wx\wx_textmine"
python -X utf8 00_build_matrix.py
echo  [OK] 已重建 E:\wx\wx_textmine_out\music_index_long.csv
echo  [提示] 之后请跑 45/44 重算基线，再跑 39 完整部署
pause
goto menu

:rebuild_raw_long
cls
echo  [重建原始库长表] 逐日 xlsx 转 music_index_raw_long.csv（含当日/昨日指数、排名、收听）
cd /d "E:\wx\论文素材_王晰作传\基线口径"
python -X utf8 build_index_raw_long.py
echo  [OK] 见 E:\wx\wx_textmine_out\music_index_raw_long.csv 与 _coverage.json
pause
goto menu

:diag_index
cls
echo  [指数数据源诊断] 覆盖率对比 + 年度多口径对照（旧表/原始库/当日/昨日）
cd /d "E:\wx\论文素材_王晰作传\基线口径"
python -X utf8 指数数据源诊断.py
echo  [OK] 报告: 指数数据源诊断报告_20260909.md
pause
goto menu

:index_guard
cls
echo  [指数数据源完整性守卫] 长表健康度 + 构建脚本指纹 + 站点与源头一致
cd /d "D:\wx409.github.io"
python -X utf8 project_b\check_index_integrity.py
echo  [提示] 退出码 0 = 完整；1 = 疑似回退到缺陷版构建（禁止对外引用）
pause
goto menu

:build_academic
cls
echo  [生成学术研究页] 读 data\literature.json 渲染 academic.html（含 Schema.org JSON-LD）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_academic.py
python -X utf8 project_b\build_nav.py
echo  [OK] 已生成 academic.html（新增文献只需编辑 data\literature.json）
pause
goto menu

:dl_albums
cls
echo  [下载专辑音频] 七张录音室专辑 + EP 回望（QQ音乐 320k，跳过已存在）
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 批量下载专辑.py
echo  [OK] 见 专辑音频 目录下的各专辑子目录；清单 专辑下载清单.json
pause
goto menu

:analyze_albums
cls
echo  [专辑音域实测] demucs 人声分离 + 逐帧 F0 + 多维声学指标（约 12 分钟）
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 批量专辑音域.py
echo  [OK] 汇总 专辑音域汇总.json ；逐曲 分析结果_专辑 目录
pause
goto menu

:report_albums
cls
echo  [生成专辑音域报告] 报告 + 站点数据 + 长图指纹 + voice.html + 首页摘要
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 生成专辑音域报告.py
python -X utf8 生成声学身份证.py
cd /d "E:\wx\论文素材_王晰作传\基线口径"
python -X utf8 generate_voice_page.py
cd /d "D:\wx409.github.io"
python -X utf8 project_b\inject_vocal_summary.py
python -X utf8 project_b\build_nav.py
python -X utf8 project_b\audit_caliber.py
echo  [OK] 报告 专辑音域报告_v1.md ；长图+指纹 ；voice.html ；首页音域摘要 均已更新
pause
goto menu

:add_song
cls
echo  [添加待测曲目] 搜索 QQ音乐 并把王晰版本写入 待测清单.json
cd /d "E:\wx\论文素材_王晰作传\音域分析"
set /p kw=输入歌名（回车退出）: 
if "%kw%"=="" goto menu
python -X utf8 添加待测曲目.py "%kw%"
pause
goto menu

:one_click_vocal
cls
echo  [一键音域实测] 下载 到 分离测量 到 报告 到 voice.html
echo  默认只处理 待测清单.json 的增量；整张新专辑请用 69/70/71
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 一键音域实测.py
pause
goto menu

:clean_stems
cls
echo  [清理分离人声缓存] 删除 分离_专辑 下的 vocals.wav（释放约 2.9GB）
echo  已测数据（分析结果_专辑 的 f0.csv/stats.json）与音频保留，重算时自动重建
set /p ok=确认删除? 输入 y 继续: 
if /i not "%ok%"=="y" goto menu
rmdir /s /q "E:\wx\论文素材_王晰作传\音域分析\分离_专辑"
echo  [OK] 已清理
pause
goto menu

:fav_fetch
cls
echo  [抓取B站收藏夹] 王晰综艺现场live 清单 + 自动归类
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 抓取B站收藏夹.py
echo  [OK] 清单 他人主导\清单.json
pause
goto menu

:dl_other
cls
echo  [下载他人主导音频] 综艺/晚会/商演/饭拍 转 wav
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 下载他人主导音频.py
echo  [OK] 他人主导 目录下按分类存放
pause
goto menu

:ctx_compare
cls
echo  [情境对比分析] 专辑(他主导) vs 舞台(他人主导) 报告+箱线图+站点
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 对比情境分析.py
cd /d "E:\wx\论文素材_王晰作传\基线口径"
python -X utf8 generate_voice_page.py
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_nav.py
echo  [OK] 报告 情境对比报告.md ；voice.html 板块四已更新
pause
goto menu

:stage_report
cls
echo  [生成他人主导详细报告] 分类明细 + 逐条表 + 音域长图 + 站点数据
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 生成他人主导报告.py
echo  [OK] 他人主导\详细报告.md ；分享\他人主导_音域长图.png
pause
goto menu

:stage_page
cls
echo  [生成舞台实测页] 读 data/archive_stage.json 渲染 stage.html
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_stage_page.py
python -X utf8 project_b\build_nav.py
echo  [OK] stage.html 已更新
pause
goto menu

:recheck10
cls
echo  [复核十曲严格口径] 用现行稳健过滤重测最早 10 曲，输出新旧对照
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 复核十曲严格口径.py
echo  [OK] 复核_十曲严格口径.md
pause
goto menu

:qq_match
cls
echo  [匹配QQ官方版本] 为舞台素材找同曲官方录音（双重校验用）
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 匹配QQ官方版本.py --write-extra
echo  [OK] 他人主导\QQ匹配.json ；已写入待测清单
echo  下一步: 菜单 69 下载（或 批量下载专辑.py --extra-only）后跑菜单 70
pause
goto menu

:crosscheck
cls
echo  [双重校验] 同一首歌 舞台版 vs QQ官方版 逐曲对照
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 双重校验舞台vsQQ.py
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_stage_page.py
python -X utf8 project_b\build_nav.py
echo  [OK] 双重校验_舞台vsQQ官方.md ；stage.html 已更新
pause
goto menu

:redraw10
cls
echo  [重绘十曲图] 按现行「最低稳定音」口径重绘 range_10songs.png
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 重绘十曲图.py
echo  [OK] assets\voice\range_10songs.png 已更新
pause
goto menu

:sitemap_lm
cls
echo  [sitemap lastmod 回填] 按 git 提交日期刷新 144 条 URL 的 lastmod
cd /d "D:\wx409.github.io"
python -X utf8 project_b\update_sitemap_lastmod.py
echo  [OK] sitemap.xml 已刷新（加 --check 可做审计）
pause
goto menu

:elev_def
cls
echo  [电梯定义句] 从 calibers/音域实测/姚峰原话 派生，注入首页+问答库+llms+Person
cd /d "D:\wx409.github.io"
python -X utf8 project_b\elevator_definition.py
echo  [OK] data\elevator_definition.json ；index.html / qa.html 顶部已更新
echo  提示: 再跑 llms.txt 生成步骤才会同步到 llms.txt
pause
goto menu

:vocal_sum
cls
echo  [首页音域摘要] 从 archive_vocal*.json 派生，替换首页手写残留
cd /d "D:\wx409.github.io"
python -X utf8 project_b\inject_vocal_summary.py
echo  [OK] index.html 音域摘要块已更新（加 --check 校验）
pause
goto menu

:audit_ld
cls
echo  [结构化数据审计] JSON-LD 语法 + ResearchProject/FAQPage 必备 + 纪律用词
cd /d "D:\wx409.github.io"
python -X utf8 project_b\audit_jsonld.py
echo  [OK] 审计完成（exit 1 = 不合格，看输出逐条修）
pause
goto menu

:idcard
cls
echo  [分享图重生成] 声学身份证长图 + 版本指纹（供口径审计校验）
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 生成声学身份证.py
echo  [OK] 分享\王晰声学身份证_长图.png ；站点 assets\voice\acoustic_id_card.png + 指纹
pause
goto menu

:audit_live
cls
echo  [线上核验] 图片 200 + 长图 sha256 对指纹 + 关键数字 + 陈旧数字黑名单
echo  提示: 刚 push 完请等 2-3 分钟再跑（Pages 构建/缓存窗口）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\audit_live.py --wait 180
echo  [OK] exit 0 = 通过或网络不可达 SKIP；exit 1 = 线上不一致，看输出逐条修
pause
goto menu

:crepe_check
cls
echo  [CREPE 交叉校验] YIN vs CREPE（CNN）时间对齐比对，自动标记次谐波错误
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 CREPE交叉校验.py
echo  [OK] CREPE交叉校验.md / .json（不一致的曲目会标 ★）
pause
goto menu

:open_sun_report
cls
echo  [打开重测报告] 《向着太阳》音高重测（D#2 78.1Hz 改为 G2 97.8Hz）
start "" "E:\wx\论文素材_王晰作传\音域分析\重测_向着太阳_20260909.md"
pause
goto menu

:watchdog
cls
echo  [漏批看门狗] 反推应完成批次 vs 实际产出；守护进程停摆则拉起+补跑一次
echo  说明: 2026-09-09 Windows 更新自动重启后无人登录，整夜批次全停摆
cd /d "D:\wx409.github.io"
python -X utf8 project_b\watchdog_batches.py
echo  [OK] exit 0 = 无漏批；exit 1 = 有漏批（已尝试自愈，看 logs\watchdog_*.log）
pause
goto menu

:harden_status
cls
echo  [更新重启抑制] 只读查看活动时间/暂停更新/相关服务状态
powershell -ExecutionPolicy Bypass -File "D:\wx409.github.io\tools\harden_windows_update.ps1" -Mode Status
pause
goto menu

:harden_apply
cls
echo  [更新重启抑制] 应用 Manual 档（活动时间06:00-23:00 + 暂停更新35天 + 重启前弹通知）
echo  说明: 需管理员（脚本会自提权弹 UAC）；恢复默认用 -Mode Restore
powershell -ExecutionPolicy Bypass -File "D:\wx409.github.io\tools\harden_windows_update.ps1" -Mode Manual
pause
goto menu

:bitlocker_export
cls
echo  [导出 BitLocker 恢复密钥] 写入 D:\Bitlocer.txt（敏感文件，勿入 git/网盘）
powershell -ExecutionPolicy Bypass -File "D:\wx409.github.io\tools\export_bitlocker_key.ps1"
pause
goto menu

:s4u_task
cls
echo  [守护进程 S4U 改造] 先实测无会话能否跑 headless Edge，再决定是否 Apply
echo  成功 → 再运行同脚本 -Mode Apply；失败 → 改用自动登录方案
powershell -ExecutionPolicy Bypass -File "D:\wx409.github.io\tools\switch_tasks_s4u.ps1" -Mode TestHeadless
pause
goto menu

:date_shift_check
cls
echo  [指数长表日期偏移核查] 列语义 + 守护进程口径 + 影响量化
cd /d "D:\wx409.github.io"
python -X utf8 project_b\verify_index_date_shift.py
pause
goto menu

:lowc_check
cls
echo  [低音复核] LowC 及以下曲目：混音谐波列 + CREPE 交叉校验（判定 YIN 次谐波错误）
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 低音复核_LowC.py
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_stage_page.py
echo  [OK] 低音复核_LowC.json + 站点 data\archive_lowc_verify.json + stage.html 已更新
pause
goto menu

:open_lowc_report
cls
echo  [打开低音复核报告] LowC 及以下曲目复核（16 条通过 / 1 条确认次谐波错误）
start "" "E:\wx\论文素材_王晰作传\音域分析\低音复核报告_LowC_20260909.md"
pause
goto menu

:backfill_day
cls
echo  [按日补录与验收] 预检日档案落位 - 重建长表 - 验收该日覆盖 - 自查长表口径
echo  用途: 当日批次未跑导致长表缺一天时, 从备份拷回 xlsx 后一键补录
echo  口径: 日档案的昨日音乐指数=抓取日前一天的官方值, 故补长表D需要「抓取日D+1」那份文件
echo        例: 要让长表出现 2026-09-08, 需要的是 2026.09.09.xlsx(9/9 晚抓的那份)
set /p bd=  输入日期(YYYY-MM-DD，直接回车=2026-09-09): 
if "%bd%"=="" set "bd=2026-09-09"
cd /d "D:\wx409.github.io"
python -X utf8 project_b\backfill_day.py --date %bd%
echo  [OK] exit 0 = 该日已进入长表；报告见 temp\补录验收_*.md
pause
goto menu

:watchdog_selftest
cls
echo  [看门狗自测] 调度解析/批次匹配/自愈分支，共 10 项，不启动也不补跑真实批次
cd /d "D:\wx409.github.io"
python -X utf8 project_b\watchdog_selftest.py
pause
goto menu

:shadow_verify
cls
echo  [日期偏移影子验证] 复用旁路长表出对照报告（不加 --reuse 会重建，约 6 分钟）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\shadow_date_shift_fix.py --reuse
echo  [OK] 报告: temp\日期偏移影子验证_20260910.md
pause
goto menu

:autologon_status
cls
echo  [自动登录 方案甲] 只读查看状态；开启请另在 PowerShell 运行 -Mode Enable -IUnderstandRisk
echo  更安全做法: 用 Sysinternals Autologon（密码存 LSA 机密），见 -Mode ToolInfo
powershell -ExecutionPolicy Bypass -File "D:\wx409.github.io\tools\autologon_toggle.ps1" -Mode Status
pause
goto menu

:rebuild_chain
cls
echo  [补录后全链路重建] matrix 长表 - baseline 基线 - cards 年度卡 - deploy 流水线 - audit 四查
echo  演练(只跑数据层): 手工加 --only matrix,baseline；不部署: 加 --skip-deploy
cd /d "D:\wx409.github.io"
python -X utf8 project_b\rebuild_after_backfill.py
echo  [OK] 汇总报告: temp\全链路重建_YYYYMMDD.md（每步 PASS/FAIL）
pause
goto menu

:index_mapping
cls
echo  [指数日期映射口径] 当前状态 + 试算补丁（只读，不改文件）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\index_date_mapping_toggle.py --status
echo.
python -X utf8 project_b\index_date_mapping_toggle.py --dry-run
echo  [提示] 确认要改: 同命令加 --apply（自动备份+语法校验）；回滚: --revert
pause
goto menu

:fallback_day
cls
echo  [缺失日备用数据源] 从守护进程合并快照取该日准终值，可生成「次日」日档案让修正映射归位
echo  说明: 仅当找不到真实日档案时使用；真实 addon 文件优先级更高，拷回后自动覆盖
set /p fd=  输入要补的日期(YYYY-MM-DD，直接回车=2026-09-08): 
if "%fd%"=="" set "fd=2026-09-08"
cd /d "D:\wx409.github.io"
python -X utf8 project_b\extract_fallback_day.py --date %fd%
echo  [提示] 真正写入日档案: 同命令加 --install-as-day 2026-09-09（次日日期）
pause
goto menu

:refresh_index
cls
echo  [指数长表+基线+年度卡刷新] 重建长表 + 重跑基线(同步站点 archive_baseline.json) + 年度卡摘要(archive_digest.json)
echo  说明: deploy_all 步骤里没有这一步，故单列；auto_update 每日已自动调用（当天只跑一次）
echo  可选: 加 --force 强制；--check-only 只看长表新鲜度（滞后超过1天=异常）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\refresh_index_baseline.py
pause
goto menu

:acceptance_check
cls
echo  [事故验收总检] 2026-09-09 停摆事故处置全貌: A 根因消除 B 自愈告警 C 口径修正
echo                    D 数据状态(含事故两天) E 站点与长表一致性 F 任务形态 G 产物工作区
echo  判定: 有 FAIL 则退出码 1；WARN 为待观察/待执行（不影响退出码）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\acceptance_check.py
echo  [OK] 报告: temp\事故验收_YYYYMMDD.md
pause
goto menu

:run_batch_now
cls
echo  [立刻补跑一次采集] 看门狗报漏批/日档案缺失/长表缺口时用，不必等下个计划批次
echo  流程: 守护进程 --once 抓一次 - 自动跑 refresh_index_baseline --force 推到长表与站点
echo  安全: 守护进程正在跑批次(日志10分钟内有写入)时默认拒绝, 需 --force 才强行执行
echo  模式: full 全量(约5-10分钟, 含昨日音乐指数列) / quick 极速(约4-5分钟)
set /p bmode=  输入模式(full 或 quick，直接回车=quick): 
if "%bmode%"=="" set "bmode=quick"
cd /d "D:\wx409.github.io"
python -X utf8 project_b\run_batch_now.py --mode %bmode%
echo  [OK] 完成后建议跑 操作中心 108 事故验收总检
pause
goto menu

:bili_traj
cls
echo  [B站轨迹素材采集] 本地搜索王晰同曲多版本素材：纯本地网络，零 AI token
echo  默认温和模式(每曲2词2页)，命中 HTTP 412 自动指数退避并改用本机 cookie
echo  加深: 手工加 --deep (每曲4词) / --tours (一巡~六巡) / --cities(城市)
echo  只解析指定 BV: 同命令加 --bv BV1xxxx BV1yyyy
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 搜索B站轨迹素材.py
echo  [OK] 轨迹素材库.json（增量：已采 BV 跳过、手工标注保留）
pause
goto menu

:bili_traj_export
cls
echo  [导出轨迹素材清单] JSON → 人读清单(md) + 待测链接(txt，格式同 bilibili链接.txt)
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 导出素材清单.py
echo  [OK] 轨迹素材清单.md（含跨时期对比类专节）/ 轨迹待测链接.txt（可直接喂既有管道）
pause
goto menu

:stage_vocal_series
cls
echo  [场次音域实测一键] 跨时期同曲多场次：B站音轨 到 wav 到 人声分离 到 双标准报告
echo  子步骤：下载场次音频.py / 场次音频准备.py / 批量专辑音域.py / 场次音域报告.py / 诊断_低音归属.py
echo  清单：轨迹\场次下载清单_*.json；低音读数存疑时用 复核低音读数.py 与 CREPE复核窗口.py 复核
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 场次音域一键.py
echo  [OK] 让她降落_四版实测.md / .json（双标准 + 场次级一致性）｜台账 场次音频\来源台账.json
pause
goto menu

:low_note_verify
cls
echo  [低音读数复核与终裁] 引擎不一致时以信号为准：CREPE 多配置稳健性 + 谱列解释度 + 四轨归属
echo  步骤：引擎稳健性复核.py（场次/专辑两轮）到 A3终裁.py；另可用 CREPE全量复核.py / 低音仲裁.py / 复核低音读数.py / CREPE复核窗口.py / 诊断_低音归属.py / 谱图取证.py / 伴奏调性闭合.py
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 引擎稳健性复核.py --scope 场次
python -X utf8 引擎稳健性复核.py --scope 专辑
python -X utf8 A3终裁.py
echo  [OK] A3复核交付表.md（可上线状态：双引擎一致 / 已取证 / 待复核 / 次谐波错误）
pause
goto menu

:facts_preflight
cls
echo  [事实预检] 反复出错的事实字段登记表（与 calibers 并列）：正确值 + 出处 + 核实日期 + 已知错误写法
echo  生成文稿/报告/指令前先跑：check_facts_preflight.py；更新登记表：build_facts.py
echo  默认扫描：temp 两份备忘 + E:\wx\论文素材_王晰作传\王晰综合评估报告_20260910.md
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_facts.py --check
python -X utf8 project_b\check_facts_preflight.py --scan-default
echo  [OK] 通过则可继续生成文稿；FAIL 时按提示修正事实后再生成
pause
goto menu

:vocal_sync
cls
echo  [音域三页数据同步] 输入有变化才跑生产脚本（voice/skill/stage 三页的数据源）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\refresh_vocal_pages.py
echo  [OK] 页面重建与推送由每日 deploy_all 链路接管（本项不做页面）
pause
goto menu

:skill_card
cls
echo  [每日唱功卡片] 今日卡片 + 近 30 天历史 + 本地传记素材归档（含可直接发的短文案）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_skill_card.py --rebuild-history --days 30
python -X utf8 project_b\build_skill_page.py
echo  [OK] 站点 data/skill_cards.json 与 skill.html；本地归档 E:\wx\论文素材_王晰作传\传记素材\唱功卡片
pause
goto menu

:nightly_vocal
cls
echo  [每晚声学增量] 只处理未实测的新场次素材（默认上限 6 条）；串烧/组曲自动跳过等人工切分
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 轨迹\每晚增量.py --limit 6
echo  [OK] 已回写 data/archive_stage_tour.json；页面重建由每日 deploy_all 接管
pause
goto menu

:album_dates
cls
echo  [专辑发行日期核验] 用 QQ音乐专辑搜索 publicTime 把 albums.json 的年月精度升级为精确日期
cd /d "D:\wx409.github.io"
python -X utf8 project_b\verify_album_dates.py
echo  [OK] 报告 data/album_release_verify.md；release_date 供「巡演 x 专辑」时序判定
pause
goto menu

:event_lifecycle
cls
echo  [活动生命周期追踪] 官宣/开票/开演的指数前后窗口（前7日/前3日/当日/后3日/后7日）
echo  新活动或新里程碑：编辑 data\event_lifecycle.json 后跑本项，统计自动回填
cd /d "D:\wx409.github.io"
python -X utf8 project_b\track_event_lifecycle.py
echo  [OK] data/event_lifecycle.json + data/event_lifecycle.md
pause
goto menu

:wx_article
cls
echo  [公众号文章留存] 正文常为图片，直抓 HTML 读不到正文；本项把图片抓到本地用离线 OCR 识别
echo  引擎：GOT-OCR 1-3秒/图（默认，快）；信息密集长图用 --engine mineru（精度更高）
echo  用法：python -X utf8 project_b\collect_wx_article.py ^<微信原文链接^> [--engine mineru]
cd /d "D:\wx409.github.io"
set /p wxurl=  粘贴微信原文链接后回车: 
if "%wxurl%"=="" goto menu
python -X utf8 project_b\collect_wx_article.py "%wxurl%"
echo  [OK] 归档到 E:\wx\论文素材_王晰作传\原始材料\微信文章\^<日期^>_^<标题^>\
pause
goto menu

:pipeline_seed
cls
echo  [任务登记表重派生] 从 deploy_all STEPS / 操作中心菜单 / Windows 计划任务 派生单一事实源
cd /d "D:\wx409.github.io"
python -X utf8 project_b\seed_pipeline_registry.py
python -X utf8 project_b\build_pipeline_views.py
echo  [OK] project_b\pipeline_registry.json + tools\install_tasks.ps1 + temp\任务登记表.md
pause
goto menu

:pipeline_audit
cls
echo  [任务一致性审计] 四处描述比对：登记表 / deploy_all / 操作中心 / 计划任务
cd /d "D:\wx409.github.io"
python -X utf8 project_b\audit_pipeline.py
pause
goto menu

:prune_raw
cls
echo  [raw_archive 保留策略] 最近 7 天全留 + 更早每日 1 份；默认只试算
cd /d "D:\wx409.github.io"
python -X utf8 project_b\prune_raw_archive.py
echo  如需执行：python -X utf8 project_b\prune_raw_archive.py --apply
pause
goto menu

:vocal_table
cls
echo  [声学长表] 4 套声学 JSON + 3 处复核状态 归一为 1 长表 + 1 台账（只读旧源，不改旧文件）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_vocal_longtable.py
python -X utf8 project_b\build_vocal_longtable.py --check
echo  查询示例：python -X utf8 project_b\build_vocal_longtable.py --query "多听有益"
pause
goto menu

:tour_pool
cls
echo  [补搜巡演曲目池] 从 64 场歌单反推各巡曲目，找出素材库缺的曲目去 B 站补搜（扩池）
echo  为什么需要：巡演层五巡 0 条的根因是"池子没覆盖五巡曲目"，不是排序问题
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 补搜巡演曲目.py --tour 五巡 --limit 8
echo  不指定 --tour 则按实测覆盖最少的巡次优先；--dry 只看缺口
pause
goto menu

:fan_essays
cls
echo  [歌迷赏析入站] 全文只留本地，站点只放元数据（篇名/篇幅/发表与授权状态 + 声学互证）
echo  步骤：源目录 docx/wps 到 Markdown（本地）到 索引 data\fan_essays.json 到 academic.html 第七节
cd /d "D:\wx409.github.io"
python -X utf8 tools\fan_essays_convert.py
python -X utf8 project_b\build_fan_essays.py
python -X utf8 project_b\build_academic.py
echo  [OK] data\fan_essays.json + academic.html；全文未进仓库、未转载
pause
goto menu

:album_remeasure
cls
echo  [录音室层重测] 人工确认后执行：全新分离重跑 8 专辑 72 曲，再出报告与站点数据
echo  [注意] 事故提醒（2026-09-11）：录音室层曾被 v22 实验目录的分析结果污染（知晓 B1 61.9 变成 C2 65.8）
echo         所以本项不接入每日自动链路；重测后必须比对基线并跑 audit_caliber（分享图指纹）
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 批量专辑音域.py --force
python -X utf8 生成专辑音域报告.py
echo  [OK] 站点 data\archive_vocal_albums.json 已更新
echo  下一步：跑 音域分析\生成声学身份证.py 重画分享图与指纹，再跑站点 project_b\audit_caliber.py
pause
goto menu

:netease_extra
cls
echo  [网易云独有曲目] 网易云有音源、QQ 无（或未测）的曲目，取源后实测
echo  依据：data\netease_catalog.json（王晰条目）与 专辑音域汇总（已测比对）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\netease_extra_songs.py --list
echo  取源实测：python -X utf8 project_b\netease_extra_songs.py --limit 5 --measure
pause
goto menu

:low_recheck
cls
echo  [低音复核工具组] 判据与陷阱见 轨迹\备忘_低音实测方法论_v2_20260911.md
echo  说明：归属最稳的窗口＝「伴奏安静 + 55-70Hz 低音带仍在响」；结论只留结果，理由进备忘
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 核_伴奏静音窗口扫描.py
python -X utf8 核_归属窗口细节.py
python -X utf8 核_人声轨低频扫描.py
python -X utf8 核_B1族混音终检.py
echo  [OK] 产物：伴奏静音窗口扫描_日期.json / 人声轨低频扫描_日期.json / 听辨片段
pause
goto menu
:low_band_traj
cls
echo  [低音带轨迹] 通用：把某素材的低音带单独拎出来，每秒量一次音高
echo  用法：python -X utf8 低音带音高轨迹.py --file 音频路径 --t0 60 --t1 105 --lo 45 --hi 80
echo  可选 --whole 全曲；输出与输入同目录的同名_低音带轨迹.json
cd /d "E:\wx\论文素材_王晰作传\音域分析"
set /p wav=请输入音频路径（wav/mp3，可直接拖入）: 
if "%wav%"=="" goto menu
set /p t0=起始秒（如 60）: 
set /p t1=结束秒（如 105）: 
python -X utf8 低音带音高轨迹.py --file "%wav%" --t0 %t0% --t1 %t1% --lo 45 --hi 80
pause
goto menu
:essay_quotes
cls
echo  [歌迷赏析摘录入站] 全文只留本地；站点只放精选摘录 + 出处（作者授权引用）
echo  数据源：data\essay_quotes.json（人工精选，含 quote/punch/on_index）
echo  落点：首页「金句墙·听众说」+ 歌曲库每曲「赏析摘录」+ 巡演页「曲目赏析摘录」
cd /d "D:\wx409.github.io"
python -X utf8 project_b\inject_essay_quotes.py
python -X utf8 project_b\build_songs_page.py
python -X utf8 project_b\build_nav.py
python -X utf8 project_b\audit_jsonld.py
python -X utf8 project_b\audit_nav.py
echo  [OK] 三处已刷新（标记块幂等；重复执行安全）
pause
goto menu
:social_figs
cls
echo  [社媒出图] 低音实测行动记录配套 6 张（含页脚署名，幂等）
echo  输出：E:\wx\论文素材_王晰作传\社媒\图\
echo  图1 低音尺 / 图2 谐波列真伪 / 图3 基频去哪了 / 图4 MV 低音带轨迹 / 图5-6 低频谱图
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 社媒出图.py
echo  [OK] 稿件：E:\wx\论文素材_王晰作传\社媒\低音实测行动记录_20260911.md
pause
goto menu


:media_manifest
cls
echo  [声音素材库总览] 扫描 E:\wx\声音素材库 并核验各平台 URL/时长，写回清册
echo  产出: E:\wx\声音素材库\manifest\media_manifest.json（保留已有下载记录）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_media_manifest.py
pause
goto menu

:media_dl
cls
echo  [下载 B站/微博 媒体] yt-dlp 取音频轨；已完成的不重复下
echo  覆盖: 音乐图书馆 8P / 晰望你听见 20P / ELLE007 8期 / 抗疫家书 / 520 情书
cd /d "D:\wx409.github.io"
python -X utf8 project_b\download_media.py --all
pause
goto menu

:media_xmly
cls
echo  [喜马拉雅读诗] 走 revision/play/tracks 公开接口取直链
echo  注意: 付费/节目形态条目无直链，脚本会如实记录 blocked_reason
cd /d "D:\wx409.github.io"
python -X utf8 project_b\download_ximalaya.py
pause
goto menu

:media_netease
cls
echo  [网易云 DJ 电台] music.163.com 公开 api 取 31 期清单（读诗/读信合集）
set /p ndl=  是否下载音频? 输入 y 下载，直接回车=只取清单:
cd /d "D:\wx409.github.io"
if /i "%ndl%"=="y" (python -X utf8 project_b\collect_netease_dj.py --download) else (python -X utf8 project_b\collect_netease_dj.py)
pause
goto menu

:media_qq
cls
echo  [QQ音乐 城市漫行] 专辑接口取 26 期清单 + musicu vkey 取音频直链（免登录）
echo  产出: data\radio_citywalk.json 与 E:\wx\声音素材库\media\qq_citywalk\
set /p qdl=  是否下载音频? 输入 y 下载，直接回车=只取清单:
cd /d "D:\wx409.github.io"
if /i "%qdl%"=="y" (python -X utf8 project_b\collect_qq_album.py --download) else (python -X utf8 project_b\collect_qq_album.py)
pause
goto menu

:media_lizhi
cls
echo  [荔枝FM 低音时间] 从 Next.js JS 包挖出的 vodapi 接口（免登录）
echo  产出: data\radio_lizhi.json 与 E:\wx\声音素材库\media\lizhi_diyin\
set /p ldl=  是否下载音频? 输入 y 下载（59期约240MB），直接回车=只取清单:
cd /d "D:\wx409.github.io"
if /i "%ldl%"=="y" (python -X utf8 project_b\collect_lizhi.py --download) else (python -X utf8 project_b\collect_lizhi.py)
pause
goto menu

:media_elle
cls
echo  [ELLE007 发布日期] 用 yt-dlp 读微博 upload_date（平台自身元数据，不推算）
echo  产出: E:\wx\声音素材库\manifest\elle_dates.json
cd /d "D:\wx409.github.io"
python -X utf8 project_b\fetch_elle_dates.py
pause
goto menu

:media_trans
cls
echo  [批量转写] faster-whisper large-v3-turbo 本地 GPU；幂等（已转写则跳过）
echo  注意: 全库统一 vad_filter=False —— 开 VAD 会把低音人声判成静音滤掉（实测 133秒只出21字）
echo  产出: E:\wx\声音素材库\transcripts 下 逐条 .txt 与 .segments.json
set /p tser=  只转写某系列? 输入系列名(如 lizhi_diyin)，直接回车=全部:
cd /d "D:\wx409.github.io"
if "%tser%"=="" (python -X utf8 project_b\transcribe_media.py --all) else (python -X utf8 project_b\transcribe_media.py --only %tser% --all)
pause
goto menu

:media_corpus
cls
echo  [声音语料整合] 转写稿 + 清册 到 data/voice_corpus.json（含出处/可引用级别/主题）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_voice_corpus.py
pause
goto menu

:media_sync
cls
echo  [语料同步] 写进 E:\wx\wx_textmine_corpus\声音素材\（按正文指纹判重，幂等）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\sync_voice_corpus.py
pause
goto menu

:media_analyze
cls
echo  [语料文本分析] 高频词/主题分布/情感倾向/人称/金句候选 到 data/voice_analysis.json
echo  口径: 情感为词表命中非模型判定；金句标注「朗读文本 vs 本人原话」
cd /d "D:\wx409.github.io"
python -X utf8 project_b\analyze_voice_corpus.py
pause
goto menu

:media_cross
cls
echo  [声音 × 指数 × 声学 交叉] 到 data/cross_voice_market.json（传记三主线）
echo  每条结论带限制条件；窗口不足时明确标注「不得下结论」
cd /d "D:\wx409.github.io"
python -X utf8 project_b\cross_voice_market.py
pause
goto menu

:media_kb
cls
echo  [并入知识库] voice_series/voice_episode 实体 + 事实 + 关系（幂等）
echo  注意: 必须排在 deploy_all 的 build_kb_graph 之后（后者重建会抹掉并入部分）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\integrate_voice_kb.py
pause
goto menu

:media_asrfix
cls
echo  [ASR 人名错字校正] 只改确证错字（王熙到王晰、西哥到晰哥），不做模糊匹配
echo  治本措施: transcribe_media.py 已加 initial_prompt 热词
cd /d "D:\wx409.github.io"
python -X utf8 project_b\fix_asr_names.py
pause
goto menu

:audit_preset
cls
echo  [维护者预设审计] 每次对话加载的说明书 vs 站点实际口径（年度值/口径项数/自动化）
echo  漂移必须修 —— 否则会把过期数字当事实带进后续对话
cd /d "D:\wx409.github.io"
python -X utf8 project_b\audit_preset.py
pause
goto menu

:media_all
cls
echo  [声音素材全链路一键] 134到146 依次执行（媒体仅本地留存，不入 git）
echo  1/7 清册  2/7 转写  3/7 语料整合  4/7 语料同步  5/7 文本分析  6/7 交叉分析  7/7 并入知识库
set /p ok2=  确认执行? 输入 y 继续，直接回车退出:
if /i not "%ok2%"=="y" goto menu
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_media_manifest.py
python -X utf8 project_b\transcribe_media.py --all
python -X utf8 project_b\build_voice_corpus.py
python -X utf8 project_b\sync_voice_corpus.py
python -X utf8 project_b\analyze_voice_corpus.py
python -X utf8 project_b\cross_voice_market.py
python -X utf8 project_b\integrate_voice_kb.py
echo  [OK] 全链路完成。建议接着跑 操作中心 39 完整部署 与 108 验收总检
pause
goto menu


:audit_ops
cls
echo  [操作中心覆盖审计] A 部署链关键步骤是否可调 / B 人工功能是否有菜单
echo                      C 反向检查: project_b / tools / 根目录 下带 __main__ 的可运行脚本
echo                        凡不属于「菜单 ∪ 部署链 ∪ 计划任务 ∪ 被引用」即报警
echo  三档: 豁免(一次性修复/库) / 待接入(已知待排期) / 未登记(需警觉)
set /p strict=  严格模式? 输入 s 则 --strict（有未登记即退出码1），直接回车=只报警:
cd /d "D:\wx409.github.io"
if /i "%strict%"=="s" (python -X utf8 project_b\audit_ops_coverage.py --strict) else (python -X utf8 project_b\audit_ops_coverage.py)
pause
goto menu


:audit_stage_exc
cls
echo  [舞台排除项回归审计] 防止生成器把已排除素材/错误曲名/旧样本数"回吞"上线
echo  黑名单与红线需同步 他人主导\_excluded.json 台账；该审计已进部署链（每次部署自动跑）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\audit_stage_exclusions.py
pause
goto menu

:audit_bitrate
cls
echo  [存量音源码率审计] 不信标称，逐文件算真实码率（字节数×8 ÷ 时长）
echo  默认只扫前若干文件（--limit 控制）；用于核对"QQ音乐320k"这类元数据声明是否属实
set /p blim=  扫描条数（直接回车=默认）:
cd /d "D:\wx409.github.io"
if "%blim%"=="" (python -X utf8 project_b\audit_audio_bitrate.py) else (python -X utf8 project_b\audit_audio_bitrate.py --limit %blim%)
pause
goto menu

:album_verify
cls
echo  [专辑层复核状态] 把 A3 终裁（含低音层/QA 抽样）转成站点 per-song / per-album 状态
echo  产出: data\album_verify_status.json（? 待复核读数展示但三不许）
echo  该步骤已进部署链；此处供数据更新后手动重跑
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_album_verify.py
pause
goto menu

:tavern_quotes
cls
echo  [小酒馆金句并入首页] 从 tavern\tavern_summaries.json 取 quotes 追加到 index.html
echo  幂等: 已有标记则跳过；无金句则提示"无金句可插入"
echo  注意: 上游需先跑 155 生成摘要，否则本步无数据可插
cd /d "D:\wx409.github.io"
python -X utf8 project_b\append_tavern_quotes.py
pause
goto menu

:tavern_summary
cls
echo  [小酒馆摘要提取] 从本地全文库逐期提取 主题/个人喜好/金句/关键词
echo  ?? 调用 DeepSeek API，按量计费；建议先 --limit 试跑
set /p tlim=  试跑期数（直接回车=全部106期）:
cd /d "D:\wx409.github.io"
if "%tlim%"=="" (python -X utf8 project_b\build_tavern_summary.py --all) else (python -X utf8 project_b\build_tavern_summary.py --limit %tlim%)
echo  [OK] 完成后可跑 154 把金句并入首页
pause
goto menu

:tavern_ep
cls
echo  [小酒馆摘要版 ep 页重建] 用干净模板替换站内逐字稿全文页
echo  保留 head/标题/导航/合规标注；正文改为 摘要+喜好+金句+本期歌单+官方外链
echo  全文已备份本地全文库，站内不再放全文（合规）
set /p elim=  试跑期数（直接回车=全部106期）:
cd /d "D:\wx409.github.io"
if "%elim%"=="" (python -X utf8 project_b\rebuild_tavern_ep_summary.py --all) else (python -X utf8 project_b\rebuild_tavern_ep_summary.py --limit %elim%)
pause
goto menu


:low_harmonic
cls
echo  [低音谐波列复核] 原始混音谐波列完整性判定
echo  1f0/3f0 缺失即判次谐波；区分「1/2 次谐波」「1/3 次谐波」「基频缺失（待判）」
echo  输出：轨迹\低音复核_谐波列_^<日期^>.json / .md
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 低音复核_谐波列.py --write
pause
goto menu

:high_harmonic
cls
echo  [高音区倍频复核] 对称于低音区的闸门
echo  动机：高音区基频常弱、2 次谐波强，YIN 会锁 2 次谐波「报高一个八度」
echo        （《友谊地久天长》真 C5 523Hz 曾报成 C6 1069Hz）
echo  做法：复用 低音复核_谐波列.py 的 ladder/judge，只把目标换成最高音
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 高音区倍频复核.py --write
pause
goto menu

:listen_ledger
cls
echo  [听辨台账回填] 人耳听辨是证据级别最高的裁决（高于 谐波列、高于 双引擎）
echo  台账：D:\wx409.github.io\data\listening_verdicts.json
echo  样本目录：E:\wx\论文素材_王晰作传\音域分析\听辨样本\
echo  回填字段：tag / song / aspect / verdict / verdict_hz / t_s / listener / date
type "D:\wx409.github.io\data\listening_verdicts.json"
pause
goto menu

:listen_rebuild
cls
echo  [听辨定案后重建] 让定案上站
echo  1) 巡演报告（读台账 → 覆盖机器判定）  2) stage.html  3) 导航
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 生成巡演现场报告.py
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_stage_page.py
python -X utf8 project_b\build_nav.py
python -X utf8 project_b\update_sitemap_lastmod.py
python -X utf8 project_b\audit_caliber.py
pause
goto menu

:audit_consistency
cls
echo  [汇总 vs 明细一致性审计] 防"未复核读数被当结论"与"汇总隐去更低值"
echo  源：data/*.json → 页面；退出码 1 = 需修
cd /d "D:\wx409.github.io"
python -X utf8 project_b\audit_consistency.py
pause
goto menu

:make_review_clips
cls
echo  [听辨样本切制] 把待复核读数切成 6~8 秒小段（人声轨 + 混音）送人耳
echo  先 --list 看待复核；--song + --hz 可单条精确定位
echo  纪律：同名曲目必须按 tag 精确匹配；高音时刻不可用低音的 t_s
cd /d "D:\wx409.github.io"
python -X utf8 project_b\make_review_clips.py --list --mode all
pause
goto menu

:build_debate_archive
cls
echo  [辩音总档生成] 把 09-09 起全部复核与听辨记录汇成一份传记素材
echo  纳入：前史 6 份（十曲口径/LowC/引擎稳健性/让她降落B1/复核备忘）
echo        + 辩音全记录正本 + data/listening_verdicts.json 裁决台账
echo  产出：E:\wx\论文素材_王晰作传\辩音总档_王晰音域.md
echo  注：这是**生成器**，上游变了重跑即刷新，勿手改产出
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_debate_archive.py
pause
goto menu

:extreme_note_review
cls
echo  [极值读数人耳核验] 纪律：最低/最高音无论在哪一层，都必须过人耳才可对外
echo  背景：专辑层"最高音 C6 1067.5Hz"从未人耳核验，经查实为女和声 —— 已作废，
echo        实际最高为 F5 706.0Hz《带着一颗好心去流浪》。
echo  生成器内 HIGH_REJECT 表为抗回退登记；复核请用 162 切样本。
cd /d "D:\wx409.github.io"
python -X utf8 project_b\make_review_clips.py --list --mode high
pause
goto menu

:build_style_metrics
cls
echo  [风格指标生成] 生成 data/archive_style.json
echo   指标一「打两份工」：极端音区快速交替（次/分钟）
echo   指标二「低的要高唱」：低音区/中音区 频谱质心比
echo   口径写死在脚本 docstring，引用前必看
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_style_metrics.py
pause
goto menu

:show_arc
cls
echo  [整场纵向分析] 读已落盘逐帧 F0，算全场 5 分箱的音区走向
echo  产出：data\archive_show_arc.json（只在有序整场素材上有效）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\整场纵向分析.py
pause
goto menu

:talk_batch
cls
echo  [talk 批量转写] faster-whisper 本地缓存模型（GPU）
echo  目录里的 wav/mp4 全部转写；已有同名 txt 自动跳过
set /p wdir=  音频目录（可拖拽）:
set /p wout=  输出目录:
echo  python -X utf8 project_b\转写talk批次.py --dir "%wdir%" --out "%wout%"
cd /d "D:\wx409.github.io"
pause
goto menu

:build_warehouse
cls
echo  [数据仓库] 站点 data\*.json + 指数长表 → DuckDB 单文件
echo  产出：E:\wx\warehouse\wangxi.duckdb + temp\DATA-WAREHOUSE.md
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_warehouse.py
pause
goto menu

:archive_flac
cls
echo  [素材无损压缩] WAV → FLAC（默认只试算，不会动文件）
echo  加 --apply 才真转；逐个比对 PCM md5 通过才删原 WAV
cd /d "D:\wx409.github.io"
python -X utf8 project_b\archive_compress_media.py
pause
goto menu

:archive_hevc
cls
echo  [视频省空间] HEVC 重编码（默认只试算）
echo  三重闸门：音频 md5 一致 + PSNR 至少 40dB + 体积压到七成以下 才替换原件
cd /d "D:\wx409.github.io"
python -X utf8 project_b\archive_reencode_hevc.py
pause
goto menu

:segment_concert
cls
echo  [整场切曲] 三层判据：掌声边界 / 能量谷 / f0 断裂
set /p wavf=  整场 wav 路径:
set /p slist= 该场歌单（分号分隔，可空）:
echo  python -X utf8 project_b\segment_concert.py --wav "%wavf%" --setlist "%slist%"
cd /d "D:\wx409.github.io"
pause
goto menu

:attribution
cls
echo  [归因检验] 四问：安慰剂 / 剂量-反应 / 事前趋势 / 中介链 + 多重比较校正
echo  事件表：temp\归因事件表.json｜产出 temp\归因报告.md
cd /d "D:\wx409.github.io"
python -X utf8 project_b\attribution_report.py
pause
goto menu

:expand_pool
cls
echo  [追踪池核查] 把「歌单唱过」与「大屏源表已追踪」对账，找可补曲目
echo  默认试算；--apply 才写源表（写前自动备份 xlsx）
echo  源表：E:\wx\index_records\收听人数（2026.7.24）.xlsx
cd /d "D:\wx409.github.io"
python -X utf8 project_b\expand_track_pool.py
pause
goto menu

:cover_catalog
cls
echo  [曲目谱系] 64 场唱过的每首歌 → 场次/首唱末唱/自有或翻唱/有无指数
echo  产出：data\cover_catalog.json + temp\曲目谱系.md
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_cover_catalog.py
pause
goto menu

:cover_analysis
cls
echo  [翻唱价值分析] 把没有指数数据的 222 首变成可引用结论
echo  产出：data\cover_analysis.json + temp\翻唱价值分析.md
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_cover_analysis.py
pause
goto menu

:coverage_index
cls
echo  [场次覆盖索引] 64 场：哪些已实测入库、哪些只有素材、哪些完全空白
echo  口径A=有实测数据（可进结论）｜口径B=有本地素材（含未实测，证据强度分级）
echo  产出：data\coverage_index.json
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_coverage_index.py
pause
goto menu

:gap_backfill
cls
echo  [缺口场次补录] 覆盖地图里还没有素材的场次：下载 B 站音轨 → wav → demucs 分离 + 逐帧 F0 → 并入现场层
echo  清单：E:\wx\论文素材_王晰作传\音域分析\轨迹\场次下载清单_缺口补录_*.json
echo  跑完再回站点侧执行：covergage 索引 → 现场报告聚合 → stage.html → 声学报告 → 审计
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
set /p spec=  清单文件名（留空则跑全部 场次下载清单_*.json）:
if "%spec%"=="" (python -X utf8 场次音域一键.py) else (python -X utf8 场次音域一键.py --spec "%spec%")
echo.
echo  接着回站点重建（本菜单 176 → 58 顺序执行）：
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_coverage_index.py
pause
goto menu

:video_shows
cls
echo  [有视频场次清单] 扫描本地视频（含 G 盘自录原件），逐场列出文件/BV/体积/已测素材
echo  产出：E:\wx\论文素材_王晰作传\有视频场次清单_王晰巡演.md ＋ data\video_shows.json
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_video_show_list.py
pause
goto menu

:show_assign
cls
echo  [场次认领] 四级证据：①日期直配 ②BV映射 ③歌单指纹 ④巡次城市唯一 ⑤同巡同城最近 ⑥巡次±2天
echo  产出：data\show_assignment.json（逐素材 show_date/证据级 + 场级汇总）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_show_assignment.py
pause
goto menu

:longnotes_verdict
cls
echo  [长声表反连接] 同曲同 Hz（±3%）被否决 → 移榜；同音区存疑 → 留档但不进榜单/共识句
echo  产出：data\archive_long_notes.json 增加 verdict_check 块 + top_flagged
cd /d "D:\wx409.github.io"
python -X utf8 project_b\audit_long_notes_verdicts.py
pause
goto menu

:audit_inject
cls
echo  [注入审计] 只看结果：注入产物有没有出现在页面可见位置（锚点断链会被抓出）
echo  背景：2026-09-21 曾因锚点被重建清掉，5 个注入器长期 no-op 而无人报警
cd /d "D:\wx409.github.io"
python -X utf8 project_b\audit_injections.py
pause
goto menu

:gap_loop
cls
echo  [缺口自动补闭环] 三步串起来，等价于每日 10:00 + 每晚 22:00 两个计划任务的手动版
echo   ① 补搜扩池：按 64 场歌单缺口搜 B 站（已过滤注记/环节/串烧/合唱，变体归一）
echo   2) 缺口优先增量：优先下载「该巡该曲还没实测」的候选（下载→分离→F0→回写）
echo   3) 聚合：重跑巡演现场报告，站点 data/archive_stage_tour.json 更新
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 补搜巡演曲目.py --limit 8
python -X utf8 每晚增量.py --limit 6
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 生成巡演现场报告.py
echo  完成；如需上线请回主菜单跑 39/44（部署）
pause
goto menu

:video_ingest
cls
echo  [视频音轨入库] 把「不在管道输入里」的自录/微博视频接进声学链路
echo   1) 抽轨：ffmpeg -vn 取音频，输出 44.1k wav 到 场次音频\wav_自录视频 批次目录
echo   2) 分析：批量专辑音域.py --root wav_自录视频（分离 + 逐帧 F0）
echo   3) 入库：生成巡演现场报告.py（已注册 wav_自录视频_分析）
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 视频音轨入库.py --dry
echo  --- 以上为计划；按任意键执行抽轨（全量，幂等） ---
pause
python -X utf8 视频音轨入库.py
cd /d "E:\wx\论文素材_王晰作传\音域分析"
set HF_HUB_OFFLINE=1
python -X utf8 批量专辑音域.py --root "E:\wx\论文素材_王晰作传\音域分析\场次音频\wav_自录视频"
cd /d "E:\wx\论文素材_王晰作传\音域分析\轨迹"
python -X utf8 生成巡演现场报告.py
pause
goto menu

:pending_review
cls
echo  [待人耳确认清单] 单一事实源：台账待核 + 长声闸门被移出条目；并自动切缺失样本
echo  产出：temp\待听辨清单.md（人读）＋ data\pending_review.json（机读，不含本地路径）
echo  听完后：159 听辨台账回填 -^> 160 定案后重建
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_pending_review.py --cut
pause
goto menu

:audio_assets
cls
echo  [音频资产台账] 逐批次清点：音频文件数/体量/已分析产物/本日新增
echo  产出：data\audio_assets.json（机读）＋ 音域分析\音频资产台账.md（本地人读）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_audio_assets.py
pause
goto menu

:explore
cls
echo  [可写方向清单] 把已有数据能回答的问题逐条算出来（非观点，全部可复算）
echo  产出：data\\explore_findings.json ＋ 本地 声学探索_可写方向.md
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_explore_findings.py
pause
goto menu

:streams
cls
echo  [横向素材积攒看板] 声学层之外，其余素材流是否在同步增长（含近7日新增/滞后天数/缺口）
echo  产出：data\\asset_streams.json ＋ 本地 横向素材积攒看板.md
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_asset_streams.py
pause
goto menu

:deepdives
cls
echo  [写作专题三题] 从可复算观测里挑三题深挖，含反面证据与可直接引用的句子
echo  产出：data\\topic_deepdives.json ＋ 本地 专题深挖_三题_写作素材.md ＋ 报告「写作专题」章
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_topic_deepdives.py
pause
goto menu

:get_cookie
cls
echo  [提取微博 cookie] 从「联想浏览器 SLBrowser」读取你自己的微博会话
echo  ＊ 运行前请确保已在联想浏览器登录 m.weibo.cn（脚本会自动关闭并重开浏览器）
echo  产出：E:\wx\私有工具\weibo_cookies.txt（旧文件自动备份）
call "E:\wx\私有工具\提取微博Cookie_联想.bat"
goto menu

:vibtopic
cls
echo  [颤音指纹专题页] 生成 topic-vibrato.html（含反面证据与可引用句）
echo  生成后跑 build_nav.py（导航与页脚索引单一事实源）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_topic_page.py
python -X utf8 project_b\build_nav.py
pause
goto menu

:check_login
cls
echo  [微博登录态验证] 只发 1 个最轻请求（/api/config），判断 cookie 是否有效
cd /d "E:\wx\私有工具"
python -X utf8 验证微博登录态.py
pause
goto menu

:tl_cand
cls
echo  [生涯节点候选] 口径：textmine_events 不得直接当站内事实引用（见 data/calibers.md）
echo  产出：E:\wx\论文素材_王晰作传\生涯节点候选_来自文本挖掘.md ＋ temp\timeline_candidates.json
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_timeline_candidates.py
pause
goto menu

:hol_skip
cls
echo  [自动关机豁免同步] 从官方节假日日历(含调休)自动生成不关机日
echo  规则：目标日(次日01:30)为 周六/周日/周一 或 法定放假日 → 不关机
echo  可用参数：--days 120（窗口）｜--skip-weekdays 6,7,1（星期）｜--respect-makeup（调休上班日按工作日算）
cd /d "D:\wx409.github.io"
python -X utf8 project_b\holiday_skip_sync.py --days 120
pause
goto menu

:cross_ai
cls
echo  [声学×指数交叉] 正向视角：微观起伏 + 相关分析（含多重比较校正与稳健性对照）
echo  产出：data/acoustic_index_cross.json ＋ 声学×指数交叉_正向分析.md
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_acoustic_index_cross.py
pause
goto menu
