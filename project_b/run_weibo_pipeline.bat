@echo off
rem WangXi weibo -> KB pipeline (scheduled task entry; log to logs/weibo_pipeline.log)
rem 2026-09-24 修：原脚本只跑「抓取」，漏了后面两步，导致语料库停在 2026-08-14 而归档已到 09-17。
rem   步骤1 微博抓取（直连 432 时自动走 CDP 兜底，见 pipeline_weibo_update.py）
rem   步骤2 归档 -> 语料库（wx_textmine\00_build_corpus.py）
rem   步骤3 语料 -> 知识库（wx_textmine\run_pipeline.py all）
set PY="C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe"
set LOG="D:\wx409.github.io\logs\weibo_pipeline.log"

echo [%date% %time%] === 步骤1/3 抓取微博 === >> %LOG%
%PY% "D:\wx409.github.io\project_b\pipeline_weibo_update.py" >> %LOG% 2>&1

echo [%date% %time%] === 步骤2/3 归档 -> 语料库 === >> %LOG%
%PY% -X utf8 "E:\wx\wx_textmine\00_build_corpus.py" >> %LOG% 2>&1

echo [%date% %time%] === 步骤3/3 语料 -> 知识库（textmine all）=== >> %LOG%
cd /d "E:\wx\wx_textmine"
%PY% -X utf8 run_pipeline.py all >> %LOG% 2>&1
echo [%date% %time%] === 管线结束 === >> %LOG%
