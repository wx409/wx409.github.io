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
echo   [地图线]

echo    15. 地图+巡演目录重建 (长表 ^> cities.json/map/目录, 联动)

echo.

echo   [发布线]

echo    10. 完整部署 deploy_all (12步+commit+IndexNow)

echo    11. IndexNow 通知 only (已push后催抓取)

echo    12. 全链路 auto_update (watch-deploy-push-indexnow)

echo    13. git 手动 push

echo    14. git 状态查看 (ahead/behind)

echo.

echo     0. 退出

echo.

set "op="

set /p op=请输入选项数字后回车: 

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