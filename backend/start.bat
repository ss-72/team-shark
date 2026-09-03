@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0..\start.ps1"
