@echo off
rem 排错用：保留黑窗能看到报错和自检结果
chcp 65001 >nul
cd /d "%~dp0"
echo === 自检 ===
python "%~dp0app.py" --probe
if exist _probe.txt type _probe.txt
echo.
echo === 启动 ===
python "%~dp0app.py"
pause
