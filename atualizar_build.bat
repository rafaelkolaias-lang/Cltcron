@echo off
title Atualizar build CronometroLeve
chcp 65001 >nul

cd /d "%~dp0"

echo ==========================================
echo PASTA ATUAL:
cd
echo ==========================================
echo.

echo Fechando build antigo...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Gerando novo exe...
python -m PyInstaller --clean --noconfirm CronometroLeve.spec
if errorlevel 1 (
    echo.
    echo ==========================================
    echo ERRO ao gerar o exe.
    echo Verifique o terminal acima.
    echo ==========================================
    pause
    exit /b 1
)

echo.
echo Criando pasta de download, se nao existir...
if not exist "painel\downloads" mkdir "painel\downloads"

echo.
echo Movendo exe novo para o painel...
if exist "painel\downloads\CronometroLeve.exe" del /f /q "painel\downloads\CronometroLeve.exe"
move /y "dist\CronometroLeve.exe" "painel\downloads\CronometroLeve.exe"
if errorlevel 1 (
    echo.
    echo ==========================================
    echo ERRO ao mover o exe para painel\downloads.
    echo ==========================================
    pause
    exit /b 1
)

echo.
echo Limpando pastas intermediarias (build e dist)...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo ==========================================
echo BUILD ATUALIZADO COM SUCESSO
echo.
echo EXE FINAL EM:
echo %~dp0painel\downloads\CronometroLeve.exe
echo ==========================================
echo.
pause