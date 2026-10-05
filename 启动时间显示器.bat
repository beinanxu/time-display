@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PYW="
where pythonw >nul 2>nul && set "PYW=pythonw"
if not defined PYW where pyw >nul 2>nul && set "PYW=pyw"
if not defined PYW set "PYW=pythonw.exe"

echo 正在启动时间显示器...
start "" "%PYW%" "%~dp0app.py"
exit
