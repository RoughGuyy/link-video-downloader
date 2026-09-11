@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo 正在创建独立运行环境...
py -3 -m venv .venv 2>nul
if errorlevel 1 python -m venv .venv
if errorlevel 1 goto :python_error

echo 正在安装依赖...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto :install_error

echo.
echo 安装完成。以后双击 download_video.bat 即可。
pause
exit /b 0

:python_error
echo 未找到 Python 3.10 或更高版本，请先安装 Python。
pause
exit /b 1

:install_error
echo 安装失败，请检查网络连接后重试。
pause
exit /b 1

