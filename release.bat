@echo off
title Release Cronometro
chcp 65001 >nul
cd /d "C:\xampp\htdocs\dashboard\Cronometro"

echo.
echo ==========================================
echo  RELEASE CRONOMETRO
echo ==========================================
echo.

:: 1. Pegar versao do app.py
for /f "tokens=2 delims==" %%a in ('findstr /C:"VERSAO_APLICACAO" app.py') do set "VERSAO_RAW=%%a"
set "VERSAO=%VERSAO_RAW: =%"
set "VERSAO=%VERSAO:~2,-1%"
echo Versao detectada: %VERSAO%
echo.

:: 2. Build do .exe
echo [1/5] Limpando build anterior...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [2/5] Gerando CronometroLeve.exe...
python -m PyInstaller --clean --noconfirm CronometroLeve.spec
if errorlevel 1 (
    echo ERRO ao gerar o exe.
    pause
    exit /b 1
)

echo [3/5] Copiando para painel/downloads...
if not exist "painel\downloads" mkdir "painel\downloads"
copy /y "dist\CronometroLeve.exe" "painel\downloads\CronometroLeve.exe"

:: 4. Git commit + tag
echo [4/5] Commitando e criando tag %VERSAO%...
git add -A
git commit -m "release(%VERSAO%): build atualizado"
git tag -a %VERSAO% -m "Release %VERSAO%" 2>nul
git push origin main
git push origin %VERSAO%

:: 5. GitHub Release (precisa do gh CLI: winget install GitHub.cli)
echo [5/5] Criando release no GitHub...
where gh >nul 2>nul
if errorlevel 1 (
    echo.
    echo AVISO: gh CLI nao encontrado. Instale com: winget install GitHub.cli
    echo O .exe foi buildado mas a release no GitHub precisa ser criada manualmente.
    echo Ou instale o gh e rode: gh release create %VERSAO% dist\CronometroLeve.exe --title "%VERSAO%" --notes "Release %VERSAO%"
) else (
    gh release create %VERSAO% dist\CronometroLeve.exe --title "Cronometro %VERSAO%" --notes "Release %VERSAO% - Build atualizado do CronometroLeve.exe" --latest
    if errorlevel 1 (
        echo AVISO: Falha ao criar release. Pode ser que a tag ja exista.
    ) else (
        echo Release criada com sucesso!
    )
)

echo.
echo ==========================================
echo  RELEASE %VERSAO% CONCLUIDA
echo  EXE: dist\CronometroLeve.exe (12MB)
echo ==========================================
echo.
pause
