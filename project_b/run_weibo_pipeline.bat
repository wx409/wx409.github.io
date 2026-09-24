@echo off
chcp 936 >nul
rem WangXi weibo -> corpus -> KB pipeline (scheduled task entry)
rem 2026-09-24 修复：原脚本只跑了「抓取」，漏了「归档->语料库」「语料->知识库」两步，
rem            导致语料库停在 2026-08-14 而归档已到 09-17。
rem 2026-09-24 新增：官方开放平台 API 采集（高级接口权限通过后自动生效；未通过则跳过）。
set PY="C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe"
set LOG="D:\wx409.github.io\logs\weibo_pipeline.log"

echo [%date% %time%] === 步骤0/4 官方API采集（无风控；权限未通过时自动跳过）=== >> %LOG%
cd /d "E:\wx\私有工具"
%PY% -X utf8 "E:\wx\私有工具\微博开放API.py" --fetch >> %LOG% 2>&1

echo [%date% %time%] === 步骤1/4 抓取微博（直连 -> CDP 兜底）=== >> %LOG%
cd /d "D:\wx409.github.io"
%PY% "D:\wx409.github.io\project_b\pipeline_weibo_update.py" >> %LOG% 2>&1

echo [%date% %time%] === 步骤2/4 归档 -> 语料库 === >> %LOG%
%PY% -X utf8 "E:\wx\wx_textmine\00_build_corpus.py" >> %LOG% 2>&1

echo [%date% %time%] === 步骤3/4 语料 -> 知识库（textmine all）=== >> %LOG%
cd /d "E:\wx\wx_textmine"
%PY% -X utf8 run_pipeline.py all >> %LOG% 2>&1
echo [%date% %time%] === 管线结束 === >> %LOG%
