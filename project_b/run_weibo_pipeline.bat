@echo off
rem WangXi weibo -> KB pipeline (scheduled task entry; log to logs/weibo_pipeline.log)
"C:\Users\yezhe\AppData\Local\Programs\Python\Python310\python.exe" "D:\wx409.github.io\project_b\pipeline_weibo_update.py" > "D:\wx409.github.io\logs\weibo_pipeline.log" 2>&1
