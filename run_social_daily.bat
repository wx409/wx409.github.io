@echo off
rem 社交抓取·每日兜底（计划任务 wx409_social_daily，每日 09:30）
rem 与启动文件夹方案并存：同一自然日已成功跑过则自动跳过（temp\auto_fetch_social_state.json）
rem 失败不致命；cookie 失效时只告警不硬跑（四态 + 三通道通知）
chcp 65001 >nul
call "D:\wx409.github.io\auto_fetch_social.bat"
