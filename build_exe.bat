@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

python -m pip install -e ".[build]"
if errorlevel 1 goto :build_error

python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name LinkVideoDownloader ^
  --distpath release ^
  --workpath build\pyinstaller ^
  --specpath build ^
  --collect-all yt_dlp ^
  --collect-all imageio_ffmpeg ^
  launcher_gui.py
if errorlevel 1 goto :build_error

echo.
echo 构建完成：release\LinkVideoDownloader.exe
pause
exit /b 0

:build_error
echo 构建失败，请查看上方错误信息。
pause
exit /b 1
