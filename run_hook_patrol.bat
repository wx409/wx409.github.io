@echo off
rem 钩子巡逻（演出日 21:00–24:00 每 30 分钟；也用于每日轻量巡逻）
rem 只做：cookie 三态 + 窗口簇状/单条突增判定 + 钩子抽取（--light 口径），不做重活
rem 失败非致命：调用方（night_show_intake / 计划任务）只记不阻断
chcp 65001 >nul
"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" -X utf8 "D:\wx409.github.io\project_b\propagation_watch.py" --light --since 4
"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" -X utf8 "D:\wx409.github.io\project_b\hook_miner.py" --quiet %*
