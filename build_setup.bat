@echo off
cd /d %~dp0

if not exist dist\VEXPER-SISTEMAS.exe (
    echo Executavel nao encontrado em dist\VEXPER-SISTEMAS.exe
    echo Gerando executavel primeiro...
    call build_exe.bat --no-pause
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

"%ISCC_PATH%" installer.iss
if errorlevel 1 (
    echo Falha ao gerar instalador.
    exit /b 1
)

echo.
echo Instalador gerado com sucesso:
echo dist\VEXPER-SISTEMAS-Setup.exe
