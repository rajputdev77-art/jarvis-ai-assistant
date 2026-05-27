@echo off
REM ═══════════════════════════════════════════════════════════════
REM   Install JARVIS auto-start via Windows Task Scheduler
REM   - Trigger: At log on (current user)
REM   - Delay:   3 seconds (not 12 like the old Startup script)
REM   - Priority: HIGH (-rl HIGHEST)
REM   - Detached pythonw.exe so no console window
REM ═══════════════════════════════════════════════════════════════
title Install JARVIS Auto-Start
echo.
echo  ====================================================
echo   Installing JARVIS Task Scheduler auto-start
echo  ====================================================
echo.

REM Delete old task if exists
schtasks /Delete /TN "JARVIS_AutoStart" /F >nul 2>&1

REM Create the new task
schtasks /Create /TN "JARVIS_AutoStart" ^
  /TR "\"C:\Users\Dev\JARVIS\venv\Scripts\pythonw.exe\" \"C:\Users\Dev\JARVIS\jarvis.py\"" ^
  /SC ONLOGON /RL HIGHEST /DELAY 0000:03 /F

if %errorlevel%==0 (
    echo.
    echo  [OK]  JARVIS will now auto-launch 3 seconds after each login.
    echo        Task name: JARVIS_AutoStart
    echo.
    echo  To disable: run uninstall_autostart.bat
) else (
    echo.
    echo  [FAIL] Could not create scheduled task.
    echo         Try running this as Administrator.
)
echo.
pause
