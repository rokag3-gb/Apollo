@echo off
chcp 65001 >nul
powershell.exe -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
pause
