@echo off
REM Tells JARVIS to show the dashboard. Writes the .hud_show sentinel.
echo %time% > "C:\Users\Dev\JARVIS\.hud_show"
REM Also launch HUD if not running (idempotent)
tasklist /FI "IMAGENAME eq pythonw.exe" /FO csv 2>nul | findstr /I "pythonw" >nul
if errorlevel 1 (
    start "" /B "C:\Users\Dev\JARVIS\venv\Scripts\pythonw.exe" "C:\Users\Dev\JARVIS\hud_arc.py"
)
exit
