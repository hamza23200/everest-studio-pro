@echo off
echo =====================================================================
echo  Everest Studio Pro - PyInstaller One-Click Build Script
echo =====================================================================
echo Building EverestStudio.exe...

pyinstaller --noconsole --onefile --name "EverestStudio" --clean main.py

echo.
if exist "dist\EverestStudio.exe" (
    echo [SUCCESS] Binary created at: dist\EverestStudio.exe
) else (
    echo [ERROR] Build failed. Verify pyinstaller is installed.
)
echo =====================================================================
pause

