@echo off
cd /d %~dp0

echo Gerando executavel atualizado antes do setup...
call build_exe.bat --no-pause
if errorlevel 1 (
    echo Falha ao gerar executavel.
    exit /b 1
)

set "ISCC_PATH="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"

if "%ISCC_PATH%"=="" (
    echo Inno Setup 6 nao encontrado.
    echo Instale em: https://jrsoftware.org/isdl.php
    exit /b 1
)

set "APP_VERSION="
for /f "tokens=2 delims==" %%i in ('findstr /B /C:"APP_VERSION" sync_agent.py') do set "APP_VERSION=%%i"
set "APP_VERSION=%APP_VERSION: =%"
set "APP_VERSION=%APP_VERSION:"=%"
if "%APP_VERSION%"=="" set "APP_VERSION=1.0.0"

echo Usando AppVersion: %APP_VERSION%
"%ISCC_PATH%" /DMyAppVersion=%APP_VERSION% installer.iss
if errorlevel 1 (
    echo Falha ao gerar instalador.
    exit /b 1
)

echo.
echo Instalador gerado com sucesso:
echo dist\VEXPER-SISTEMAS-Setup.exe
