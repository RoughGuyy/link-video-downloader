@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

conda --version >nul 2>&1
if errorlevel 1 goto :conda_error

conda env list | findstr /R /C:"^link-video-downloader " >nul
if errorlevel 1 (
  echo 正在创建 Conda 环境 link-video-downloader...
  conda create -n link-video-downloader python=3.11 pip -y
  if errorlevel 1 goto :install_error
)

echo 正在安装项目、FFmpeg 和下载组件...
conda run -n link-video-downloader python -m pip install -e .
if errorlevel 1 goto :install_error

echo.
echo 安装完成。以后双击 download_video_conda.bat 即可。
pause
exit /b 0

:conda_error
echo 未找到 Conda，请先安装或打开 Miniconda Prompt。
pause
exit /b 1

:install_error
echo 安装失败，请检查网络连接后重试。
pause
exit /b 1

