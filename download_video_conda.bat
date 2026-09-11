@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

conda run -n link-video-downloader python -c "import linkvideo" >nul 2>&1
if errorlevel 1 goto :not_installed

set /p "VIDEO_URL=请粘贴小红书、B站或 YouTube 链接："
if not defined VIDEO_URL exit /b 1
set /p "VIDEO_QUALITY=选择清晰度 best/2160p/1440p/1080p/720p/480p/360p（默认 best）："
if not defined VIDEO_QUALITY set "VIDEO_QUALITY=best"
conda run --no-capture-output -n link-video-downloader linkvideo "%VIDEO_URL%" --quality "%VIDEO_QUALITY%"
echo.
pause
exit /b %errorlevel%

:not_installed
echo 尚未安装，请先双击 setup_conda_windows.bat。
pause
exit /b 1

