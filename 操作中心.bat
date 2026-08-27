@echo off

title 王晰档案站 · 操作中心

setlocal EnableExtensions



:menu

cls

echo ============================================

echo    王晰档案站 · 操作中心

echo    (说明文档: temp\运维SOP_新微博与评论处理.md)

echo ============================================

echo.

echo   [官方账号 · 全量下载]

echo     1. 微博全量 - 王晰本人 (文字+图片+视频)

echo     2. 微博全量 - 王晰工作室 (文字+图片+视频)

echo    22. 小红书全量 - 王晰主页 (文字+图片+视频)

echo    23. B站全量 - 王晰空间 (文字+视频)

echo.

echo   [微博线]

echo     3. 本地网页快照 (weibo_snapshots)

echo     4. 更新 live-reviews (本人纯文字/工作室留链接)

echo    24. 微博抓取 - 仅文字图片 (跳过视频)

echo.

echo   [评论线]

echo     5. 观众反馈收集 (微博+小红书+B站+Bing)

echo     6. 反馈入库 live 页 (短句+外链)

echo     7. 歌单候选 (反馈反推歌名)

echo     8. 歌单重建 (长表 ^> setlists.json + 页面)

echo     9. 场次标记已举办 + 大屏 rebuild

echo    16. 追踪报告入库 (实时追踪md ^> live-reviews)
echo    32. 微博手动正文入库 (wb链接txt ^> 匿名化 ^> live页+分析)
echo    33. B站翻页补收 (--bili-only, 3页, 最新排序)

echo.

echo   [小红书线]

echo    17. 小红书按链接抓取 - 视频+图文全量 (links.txt)

echo    25. 小红书按链接抓取 - 仅文字图片 (links.txt)

echo    18. 小红书入库 (按歌曲归类 纯文字 无链接无id)
echo    19. 广州整理摘录重渲染 (改完 _gz_quotes.json 后跑)
echo    20. 小红书summary重建 (抓取中断后恢复完整汇总)
echo    21. 评论多层面分析 (微博/小红书/B站, 论文友好, 默认广州场)
echo.
echo   [视频线]
echo    26. B站下载+摘要 - 视频+文字 (bilibili链接.txt)
echo    27. B站仅文字摘要 - 不下视频
echo.
echo   [转写线]
echo    28. 转写加工 - DeepSeek 后处理 (提示词在 project_b\prompts)
echo    29. 转写预筛+待审清单 (pipeline --precheck, 需加工JSON路径)
echo    30. 转写合并 - 审核通过项 (pipeline --merge)
echo    31. 转写txt导入 + ASR专有名词纠错 (--ingest-txt)
echo.
echo   [地图线]

echo    15. 地图+巡演目录重建 (长表 ^> cities.json/map/目录, 联动)

echo.

echo   [发布线]

echo    10. 完整部署 deploy_all (12步+commit+IndexNow)

echo    11. IndexNow 通知 only (已push后催抓取)

echo    12. 全链路 auto_update (watch-deploy-push-indexnow)
echo    34. 首页重建+动态更新 (五层架构, 摘要卡自动刷新)

echo    13. git 手动 push

echo    14. git 状态查看 (ahead/behind)

echo.

echo     0. 退出

echo.

set "op="

echo.
echo   [论文素材]
echo    91. 打开论文素材索引
echo    92. 打开论文草稿目录
echo    93. 打开预测实验档案
set /p op=请输入选项数字后回车: 

if "%op%"=="91" goto paper_assets
if "%op%"=="92" goto paper_drafts
if "%op%"=="93" goto paper_predictions
if "%op%"=="" exit /b



if "%op%"=="1" goto wb_self

if "%op%"=="2" goto wb_studio

if "%op%"=="3" goto wb_snapshot

if "%op%"=="4" goto wb_live

if "%op%"=="5" goto fb_collect

if "%op%"=="6" goto fb_repo

if "%op%"=="7" goto fb_candidate

if "%op%"=="8" goto sl_build

if "%op%"=="9" goto sl_status

if "%op%"=="10" goto dp_all

if "%op%"=="11" goto dp_indexnow

if "%op%"=="12" goto dp_auto

if "%op%"=="13" goto git_push

if "%op%"=="14" goto git_status
if "%op%"=="34" goto home_build

if "%op%"=="15" goto map_rebuild

if "%op%"=="16" goto trk_import

if "%op%"=="17" goto xhs_fetch

if "%op%"=="18" goto xhs_import
if "%op%"=="19" goto gz_render
if "%op%"=="20" goto xhs_rebuild
if "%op%"=="21" goto an_analyze

if "%op%"=="22" goto xhs_user_full

if "%op%"=="23" goto bili_space_full

if "%op%"=="24" goto wb_novideo

if "%op%"=="25" goto xhs_links_novideo

if "%op%"=="26" goto bili_dl

if "%op%"=="27" goto bili_text

if "%op%"=="28" goto trans_process

if "%op%"=="29" goto trans_precheck

if "%op%"=="30" goto trans_merge

if "%op%"=="31" goto trans_ingest
if "%op%"=="32" goto wb_manual_import
if "%op%"=="33" goto bili_backfill

if "%op%"=="0" exit /b

echo   [!] 无效选项，请重试

pause

goto menu



:wb_self

cls

echo === 微博抓取 - 王晰本人 (断点续传, 只抓新的) ===

cd /d "E:\wx\私有工具\weibo_proxy"

chcp 65001 >nul

python -X utf8 weibo_proxy.py fetch

chcp 936 >nul

echo.

echo 存档: E:\wx\私有工具\weibo_archive\posts + media

echo 提示: 抓完可执行 3(快照) 和 4(更新live-reviews)

pause

goto menu



:wb_studio

cls

echo === 微博抓取 - 王晰工作室 (关键词过滤) ===

cd /d "E:\wx\私有工具\weibo_proxy"

chcp 65001 >nul

python -X utf8 weibo_proxy_studio.py fetch

chcp 936 >nul

echo.

echo 存档: E:\wx\私有工具\weibo_archive_studio\posts + media

pause

goto menu



:wb_snapshot

cls

echo === 本地网页快照生成 (增量) ===

cd /d "D:\wx409.github.io"

chcp 65001 >nul

python -X utf8 project_b\run_weibo_snapshot.py --once

chcp 936 >nul

echo.

echo 输出: E:\wx\私有工具\weibo_snapshots\posts\<YYYY-MM>\<mid>.html

pause

goto menu



:wb_live

cls

echo === 更新 live-reviews.html ===

echo 前提: 先在 data\tour_weibo_posts.json 的 matched_to_shows 追加新记录

echo       (sourceType 决定本人=纯文字 / 工作室=可留链接)

cd /d "D:\wx409.github.io"

chcp 65001 >nul

python -X utf8 project_b\update_live_reviews_tourweibo.py

chcp 936 >nul

echo.

echo 下一步: 提交推送(13) + IndexNow(11)

pause

goto menu



:fb_collect

cls

echo === 观众反馈收集 (微博+小红书+B站+Bing) ===

set /p fdate=请输入演出日期(YYYY-MM-DD, 如2026-08-23): 

set /p fcity=请输入城市(如 广州): 

if "%fdate%"=="" goto fb_collect

if "%fcity%"=="" goto fb_collect

chcp 65001 >nul

python -X utf8 D:\wx409.github.io\project_b\collect_show_feedback.py --date %fdate% --city %fcity%

chcp 936 >nul

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

chcp 65001 >nul

python -X utf8 D:\wx409.github.io\project_b\build_show_repo.py --date %fdate% --city %fcity% --page %fpage%

chcp 936 >nul

pause

goto menu



:fb_candidate

cls

echo === 歌单候选 (反馈反推歌名) ===

set /p fdate=请输入演出日期(YYYY-MM-DD): 

set /p fcity=请输入城市: 

if "%fdate%"=="" goto fb_candidate

if "%fcity%"=="" goto fb_candidate

chcp 65001 >nul

python -X utf8 D:\wx409.github.io\project_b\build_repo_setlist_candidates.py --date %fdate% --city %fcity%

chcp 936 >nul

pause

goto menu



:sl_build

cls

echo === 歌单重建: 长表 ^> setlists.json + live/setlists.html ===

echo 前提: 正确歌单已写入长表

echo    E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx

cd /d "D:\wx409.github.io"

chcp 65001 >nul

python -X utf8 project_b\build_setlists.py

python -X utf8 project_b\build_setlists_page.py

chcp 936 >nul

pause

goto menu



:sl_status

cls

echo === 场次标记已举办 + 大屏 rebuild ===

cd /d "D:\wx409.github.io"

chcp 65001 >nul

python -X utf8 project_b\update_show_status.py --rebuild

chcp 936 >nul

pause

goto menu



:dp_all

cls

echo === 完整部署 deploy_all (12步生成 + commit + IndexNow) ===

cd /d "D:\wx409.github.io"

chcp 65001 >nul

python -X utf8 project_b\deploy_all.py

chcp 936 >nul

echo.

echo 注意: deploy_all 只本地 commit, 需手动 push(13)

pause

goto menu



:dp_indexnow

cls

echo === IndexNow 通知 only ===

cd /d "D:\wx409.github.io"

chcp 65001 >nul

python -X utf8 project_b\deploy_all.py --notify-only

chcp 936 >nul

pause

goto menu



:dp_auto

cls

echo === 全链路 auto_update (watch-deploy-push-indexnow-通知) ===

cd /d "D:\wx409.github.io"

chcp 65001 >nul

python -X utf8 project_b\auto_update.py --machine laptop --watch

chcp 936 >nul

pause

goto menu



:trk_import

cls

echo === 追踪报告入库 (实时追踪md ^> live-reviews) ===

echo 读: temp\演出追踪_20260823\实时反馈_手动收集.md

echo 写: data/live_repos.json + live-reviews.html (自动去重)

cd /d "D:\wx409.github.io"

chcp 65001 >nul

python -X utf8 project_b\import_tracking_repo.py

chcp 936 >nul

echo.

echo 提示: 提交推送用 13, 催搜索引擎用 11

pause

goto menu



:xhs_fetch

cls

echo === 小红书按链接抓取 (links.txt ^> 本地) ===

echo 前置: 链接文件 D:\wx409.github.io\temp\xhs_links.txt (每行一个分享链接)

echo       cookie 优先读 E:\wx\index_records\xhs.txt

echo 存档: E:\wx\私有工具\xhs_archive\按链接\

chcp 65001 >nul

python -X utf8 E:\wx\私有工具\xhs_proxy\fetch_xhs_links.py --file "D:\wx409.github.io\temp\xhs_links.txt"

chcp 936 >nul

echo 提示: 抓完可执行 18(入库)

pause

goto menu



:xhs_import

cls

echo === 小红书入库 (纯文字 无链接 无id 20字以上) ===

echo 读: E:\wx\私有工具\xhs_archive\_by_links_summary.json

echo 写: live-reviews.html (纯文字, 幂等)

cd /d "D:\wx409.github.io"

chcp 65001 >nul

python -X utf8 project_b\import_xhs_songs.py

chcp 936 >nul

echo --- 渲染歌曲分区 ---

chcp 65001 >nul

python -X utf8 project_b\render_xhs_songs.py

chcp 936 >nul

echo 提示: 提交推送用 13, 催搜索引擎用 11

pause

goto menu



:gz_render
cls
echo === 广州整理摘录重渲染 ===
echo 改完 temp\_gz_quotes.json 后跑本项，重写 live-reviews 广州评论区
cd /d "D:\wx409.github.io"
chcp 65001 >nul
python -X utf8 project_b\render_gz_quotes.py
chcp 936 >nul
echo 提示: 提交推送用 13
pause
goto menu

:xhs_rebuild
cls
echo === 小红书 summary 重建 ===
echo 用途: fetch 中断后 summary 被最后一次运行覆盖，从归档目录重建完整汇总
chcp 65001 >nul
python -X utf8 project_b\run_xhs_rebuild.py
chcp 936 >nul
echo 之后可执行 18(入库)
pause
goto menu

:an_analyze
cls
echo === 评论多层面分析 (论文友好) ===
echo 聚合微博/小红书/B站/Bing 评论: 高频主题/独特观点/评价维度/情感/画像/格言
echo 默认: 广州 2026-08-23; 加 --llm 启用 DeepSeek 归纳层 (需 temp\deepseek_key.json)
cd /d "D:\wx409.github.io"
chcp 65001 >nul
python -X utf8 project_b\analyze_audience_comments.py --date 2026-08-23 --city 广州
chcp 936 >nul
echo 输出: temp\audience_analysis\2026-08-23_广州.json + .md
pause
goto menu

:xhs_user_full
cls
echo === 小红书全量 - 王晰主页 (视频+图文) ===
cd /d "E:\wx\私有工具\xhs_proxy"
chcp 65001 >nul
python -X utf8 fetch_xhs_user.py
chcp 936 >nul
echo 归档: E:\wx\私有工具\xhs_archive\官方账号\王晰\
pause
goto menu

:bili_space_full
cls
echo === B站全量 - 王晰空间 (视频+文字) ===
echo 注意: 空间抓取需 B站登录 Cookie (E:\wx\index_records\bilibili_cookies.txt)
echo       未配置时请把空间视频链接逐条加入 bilibili链接.txt 后走选项26
cd /d "D:\wx409.github.io"
chcp 65001 >nul
python -X utf8 project_b\download_bilibili.py --space 3493257487059302
chcp 936 >nul
pause
goto menu

:wb_novideo
cls
echo === 微博抓取 - 仅文字图片 (本人+工作室, 跳过视频) ===
cd /d "E:\wx\私有工具\weibo_proxy"
chcp 65001 >nul
python -X utf8 weibo_proxy.py fetch --no-video
python -X utf8 weibo_proxy_studio.py fetch --no-video
chcp 936 >nul
pause
goto menu

:xhs_links_novideo
cls
echo === 小红书按链接抓取 - 仅文字图片 ===
echo 前置: D:\wx409.github.io\temp\xhs_links.txt (每行一个分享链接)
cd /d "D:\wx409.github.io"
chcp 65001 >nul
python -X utf8 E:\wx\私有工具\xhs_proxy\fetch_xhs_links.py --file "D:\wx409.github.io\temp\xhs_links.txt" --no-video
chcp 936 >nul
echo 提示: 抓完可执行 18(入库)
pause
goto menu

:bili_dl
cls
echo === B站下载+摘要 - 视频+文字 ===
echo 前置: E:\wx\六巡\20260823广州站\bilibili链接.txt (每行一个链接/BV号)
cd /d "D:\wx409.github.io"
chcp 65001 >nul
python -X utf8 project_b\download_bilibili.py
chcp 936 >nul
echo 输出: E:\wx\六巡\20260823广州站\bilibili视频\
pause
goto menu

:bili_text
cls
echo === B站仅文字摘要 - 不下视频 ===
cd /d "D:\wx409.github.io"
chcp 65001 >nul
python -X utf8 project_b\download_bilibili.py --no-download
chcp 936 >nul
echo 输出: bilibili_summary.md (标题/UP主/时长/简介)
pause
goto menu

:trans_process
cls
echo === 转写加工 - DeepSeek 后处理 ===
echo 提示词: project_b\prompts\transcript_postprocess.md
echo 步骤: 0) 也可先规则提取金句(零token): pipeline --extract-quotes 原始JSON
echo 步骤: 1) v4 转写工具产出原始JSON(句级时间戳)
echo       2) 按提示词用 DeepSeek 加工 -> quotes/faqs/timeline/conflicts
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
chcp 65001 >nul
python -X utf8 project_b\transcript_pipeline.py --precheck %tpath%
chcp 936 >nul
echo 清单: temp\transcripts_review\review.md (人工打勾后跑 30)
pause
goto menu

:trans_merge
cls
echo === 转写合并 - 审核通过项 ===
cd /d "D:\wx409.github.io"
chcp 65001 >nul
python -X utf8 project_b\transcript_pipeline.py --merge
chcp 936 >nul
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
chcp 65001 >nul
python -X utf8 project_b\transcript_pipeline.py --ingest-txt "%tpath%" --date %tdate% --venue %tvenue%
chcp 936 >nul
echo 产物: temp\transcripts_review\<文件名>.json (已纠错)
echo 之后: 28(DeepSeek加工/策展) 或 29(预筛审核) 或 --extract-quotes 规则金句
pause
goto menu

:map_rebuild

cls

echo === 地图+巡演目录重建 (长表单一事实源) ===

cd /d "D:\wx409.github.io"

chcp 65001 >nul

python -X utf8 project_b\run_map_rebuild.py

chcp 936 >nul

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
chcp 65001 >nul
python -X utf8 D:\wx409.github.io\project_b\import_wb_manual.py --date %fdate% --city %fcity% --file "%wbfile%"
echo --- 入库 live 页 ---
set /p fpage=请输入live页路径(回车默认 live\hui-回-广州-2026.html): 
if "%fpage%"=="" set "fpage=live\hui-回-广州-2026.html"
python -X utf8 D:\wx409.github.io\project_b\build_show_repo.py --date %fdate% --city %fcity% --page %fpage% --no-push
chcp 936 >nul
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
chcp 65001 >nul
python -X utf8 D:\wx409.github.io\project_b\collect_show_feedback.py --date %fdate% --city %fcity% --bili-only --bili-pages 3 --bili-order pubdate
chcp 936 >nul
echo 结果: E:\wx\私有工具\show_feedback\
echo 下一步: 入库 live 页(6) + 评论分析(21)
pause
goto menu

:home_build
cls
echo === 首页重建 + 动态更新 (五层架构) ===
cd /d "D:\wx409.github.io"
chcp 65001 >nul
python -X utf8 D:\wx409.github.io\project_b\build_home.py --rebuild
python -X utf8 D:\wx409.github.io\update_index_table.py
python -X utf8 D:\wx409.github.io\project_b\build_home.py --dynamic-only
chcp 936 >nul
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