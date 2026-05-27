@echo off
title Uninstall JARVIS Auto-Start
echo.
echo  ====================================================
echo   Removing JARVIS auto-start
echo  ====================================================
schtasks /Delete /TN "JARVIS_AutoStart" /F
if exist "C:\Users\Dev\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS.cmd" (
    del /q "C:\Users\Dev\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS.cmd"
    echo  [OK] Removed old Startup-folder JARVIS.cmd too.
)
echo.
echo  JARVIS will no longer auto-start. Run install_autostart.bat to re-enable.
echo.
pause
