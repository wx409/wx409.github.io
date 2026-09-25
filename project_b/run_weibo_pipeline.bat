@echo off
chcp 936 >nul
rem WangXi weibo -> corpus -> KB pipeline (scheduled task entry)
rem 2026-09-24 修复：原脚本只跑了「抓取」，漏了「归档->语料库」「语料->知识库」两步，
rem            导致语料库停在 2026-08-14 而归档已到 09-17。
rem 2026-09-25 暂关官方 API 步骤：应用 wangxi_research 因「无 ICP 备案」被驳回；
rem     据《应用审核产品指南》，文案审核只为"来源地址显示"（只读不发则不需要），
rem     且 12.1 明令拒绝"从新浪网站抓取信息"的应用 → 开放平台路线不可行。
rem     若将来启用（备案域名 / 新建「移动应用」过审），把下面三行 rem 去掉即可。
rem echo [%date% %time%] === 步骤0/3 官方API采集（需高级读取权限）=== >> %LOG%
rem cd /d "E:\wx\私有工具"
rem %PY% -X utf8 "E:\wx\私有工具\微博开放API.py" --fetch >> %LOG% 2>&1
set PY="C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe"
set LOG="D:\wx409.github.io\logs\weibo_pipeline.log"

echo [%date% %time%] === 步骤1/3 抓取微博（直连 -> CDP 兜底）=== >> %LOG%
cd /d "D:\wx409.github.io"
%PY% "D:\wx409.github.io\project_b\pipeline_weibo_update.py" >> %LOG% 2>&1

echo [%date% %time%] === 步骤2/3 归档 -> 语料库 === >> %LOG%
%PY% -X utf8 "E:\wx\wx_textmine\00_build_corpus.py" >> %LOG% 2>&1

echo [%date% %time%] === 步骤3/3 语料 -> 知识库（textmine all）=== >> %LOG%
cd /d "E:\wx\wx_textmine"
%PY% -X utf8 run_pipeline.py all >> %LOG% 2>&1
echo [%date% %time%] === 管线结束 === >> %LOG%
