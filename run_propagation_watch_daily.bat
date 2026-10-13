@echo off
rem 传播监测·每日轻量巡逻（计划任务 wx409_propagation_watch_daily，每日 23:40）
rem 只跑廉价部分：cookie 三态（失效写站点通知 + 本地日志）+ 窗口簇状/单条突增判定 + 规则二
rem 不联网抓取、不改站点页面；台账 temp\propagation_watch.log
chcp 65001 >nul
"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" -X utf8 "D:\wx409.github.io\project_b\propagation_watch.py" --light --since 24 %*
