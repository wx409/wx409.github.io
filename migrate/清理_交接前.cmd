@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
echo ============================================
echo  交接前清理（旧机将交给孩子使用）
echo ============================================
echo.
echo 本脚本只删除【登录凭据/密钥】，不动项目数据。
echo 删除不可恢复。请确认已经在新机完成迁移与验收。
echo.
set /p GO=输入 YES 继续，其他任意键退出：
if /i not "%GO%"=="YES" ( echo 已取消。 & pause & exit /b 0 )

set LIST=
if exist "E:\wx\index_records\wb.txt"                  set LIST=!LIST! "E:\wx\index_records\wb.txt"
if exist "E:\wx\index_records\xhs.txt"                 set LIST=!LIST! "E:\wx\index_records\xhs.txt"
if exist "E:\wx\私有工具\weibo_cookies.txt"             set LIST=!LIST! "E:\wx\私有工具\weibo_cookies.txt"
if exist "E:\wx\私有工具\weibo_proxy\weibo_cookie.json" set LIST=!LIST! "E:\wx\私有工具\weibo_proxy\weibo_cookie.json"
if exist "E:\wx\私有工具\xhs_proxy\xhs_cookie.json"     set LIST=!LIST! "E:\wx\私有工具\xhs_proxy\xhs_cookie.json"
if exist "E:\wx\私有工具\realtime_cookies"             set LIST=!LIST! "E:\wx\私有工具\realtime_cookies"
if exist "E:\wx\index_records\qqmusic.txt"             set LIST=!LIST! "E:\wx\index_records\qqmusic.txt"
if exist "D:\wx409.github.io\secrets.bat"              set LIST=!LIST! "D:\wx409.github.io\secrets.bat"
if exist "D:\wx409.github.io\.env"                     set LIST=!LIST! "D:\wx409.github.io\.env"

echo.
echo 将删除以下凭据：
echo !LIST!
echo.
set /p OK2=确认删除？输入 DELETE 执行：
if /i not "%OK2%"=="DELETE" ( echo 已取消。 & pause & exit /b 0 )

for %%F in (!LIST!) do (
  if exist "%%~F" (
    if /i "%%~aF" NEQ "" (
      rmdir /s /q "%%~F" 2>nul && echo   [DEL] %%~F
    )
  )
  if exist "%%~F" ( del /f /q "%%~F" >nul 2>&1 & echo   [DEL] %%~F )
)

echo.
echo ============================================
echo 还需你手动完成（脚本不代做）：
echo  1) 退出微信/微博/小红书/QQ音乐/GitHub/DSH 登录
echo  2) 浏览器：清除保存的密码与 Cookie
echo  3) GitHub：吊销本机用过的 token / 移除本机 SSH key
echo  4) Windows：新建孩子账户，迁移或删除你的账户数据
echo  5) 检查 E:\wx\论文素材_王晰作传\音域分析\听辨样本 与 场次音频 是否需删
echo ============================================
pause
exit /b 0
