@echo off
title 王晰档案站 · 操作中心 (v3)
setlocal EnableExtensions
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
echo    39. 完整部署 deploy_all（25步+commit+IndexNow，末尾自动口径/导航/bat 把关）
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

echo === 完整部署 deploy_all (25步生成 + 把关 + commit + IndexNow) ===

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
echo  [更新 voice.html] 重跑音域谱+页面生成
cd /d E:\wx\论文素材_王晰作传\基线口径
python -X utf8 generate_vocal.py
python -X utf8 generate_voice_page.py
echo  [OK] 已生成 data\archive_vocal.json 与 voice.html
echo  改动后: git add voice.html assets\voice data\archive_vocal.json 后 commit+push
echo  IndexNow 提交参考 temp\indexnow_batch_all.py 的写法
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
echo  [一键把关] 口径审计 + 口径登记表 + 导航统一 + 导航审计
cd /d "D:\wx409.github.io"
python -X utf8 project_b\audit_caliber.py
python -X utf8 project_b\build_calibers.py
python -X utf8 project_b\build_nav.py
python -X utf8 project_b\audit_nav.py
python -X utf8 project_b\audit_bat.py
python -X utf8 project_b\audit_ops_coverage.py
python -X utf8 project_b\check_index_integrity.py
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
echo  [生成专辑音域报告] 报告 + 站点数据 + 重渲染 voice.html
cd /d "E:\wx\论文素材_王晰作传\音域分析"
python -X utf8 生成专辑音域报告.py
cd /d "E:\wx\论文素材_王晰作传\基线口径"
python -X utf8 generate_voice_page.py
cd /d "D:\wx409.github.io"
python -X utf8 project_b\build_nav.py
echo  [OK] 报告 专辑音域报告_v1.md ；voice.html 已更新
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
