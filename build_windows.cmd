@echo off
setlocal
cd /d "%~dp0"
py -m PyInstaller --clean --noconfirm FilmMeta.spec
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)
echo Created dist\FilmMeta.exe
pause
