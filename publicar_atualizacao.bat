@echo off
setlocal
cd /d %~dp0

echo === Publicacao de Atualizacao (Metodo Facil) ===

echo [1/4] Gerando executavel...
call build_exe.bat
if errorlevel 1 (
    echo Falha ao gerar executavel.
    exit /b 1
)

echo [2/4] Gerando instalador...
call build_setup.bat
if errorlevel 1 (
    echo Falha ao gerar instalador.
    exit /b 1
)

set /p VERSION=Informe a versao (ex: 1.2.0): 
if "%VERSION%"=="" (
    echo Versao nao informada.
    exit /b 1
)

set /p BASE_URL=Informe a URL publica base (ex: https://cdn.seusite.com/vexper): 
if "%BASE_URL%"=="" (
    echo URL base nao informada.
    exit /b 1
)

set /p NOTES=Notas da versao (opcional): 
if "%NOTES%"=="" set "NOTES=Atualizacao automatica publicada."

echo [3/4] Gerando pacote publico de atualizacao...
python scripts\publish_update_bundle.py --version "%VERSION%" --base-url "%BASE_URL%" --notes "%NOTES%"
if errorlevel 1 (
    echo Falha ao gerar pacote publico.
    exit /b 1
)

echo [4/4] Concluido.
echo Pasta pronta para upload: public_update
pause
