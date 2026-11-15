@echo off
chcp 936 >nul
REM 以调试模式启动默认浏览器（保留登录态），供 Playwright 接管抓抖音作品列表。
REM 用法：先关掉浏览器，再双击本文件；之后回到 DSH 说"浏览器已开"。

set "PORT=9333"
set "PROFILE=%LOCALAPPDATA%\wx409_browser_debug"
set "URL=https://www.douyin.com/user/MS4wLjABAAAA6ORM3-ViSSI9SXozDl3OTaLLTHf-gm0ew9PgHRHr1ZA"

echo === 以调试端口 %PORT% 启动浏览器 ===
echo 配置目录：%PROFILE%
echo.

set "BROWSER="
for %%P in (
  "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
  "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
  "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
  "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
  "%LOCALAPPDATA%\SLBrowser\SLBrowser.exe"
) do (
  if exist %%P if not defined BROWSER set "BROWSER=%%~P"
)

if not defined BROWSER (
  echo [错误] 没找到 Edge / Chrome / 联想浏览器，请手动把浏览器路径告诉我。
  pause
  exit /b 1
)

echo 启动：%BROWSER%
start "" "%BROWSER%" --remote-debugging-port=%PORT% --user-data-dir="%PROFILE%" "%URL%"

echo.
echo 浏览器已启动。若抖音提示登录，请扫码登录一次（登录态会保存在上面的配置目录）。
echo 完成后回到 DSH，说一句“浏览器已开”。
pause
