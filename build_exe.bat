@echo off
cd /d %~dp0

if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist VEXPER-SISTEMAS.spec del /f /q VEXPER-SISTEMAS.spec

call .venv\Scripts\activate.bat

python -m PyInstaller --clean --noconfirm --onefile --windowed ^
--name VEXPER-SISTEMAS ^
--icon=icon.ico ^
--add-data "logo.png;." ^
--add-data "1.png;." ^
--add-data "icon.ico;." ^
--add-data "icon.png;." ^
sync_agent.py