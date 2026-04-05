@echo off
title Validacao Cronometro
chcp 65001 >nul
cd /d "C:\xampp\htdocs\dashboard\Cronometro"

set "FALHOU=0"

echo.
echo ==========================================
echo  VALIDACAO COMPLETA DO CRONOMETRO
echo ==========================================
echo.

echo [1/4] Ruff (lint)...
python -m ruff check .
if errorlevel 1 (
    echo *** LINT FALHOU ***
    set "FALHOU=1"
) else (
    echo OK
)
echo.

echo [2/4] MyPy (tipos)...
python -m mypy banco.py atividades.py declaracoes_dia.py --ignore-missing-imports --no-error-summary 2>nul
if errorlevel 1 (
    echo *** TYPECHECK COM AVISOS ***
) else (
    echo OK
)
echo.

echo [3/4] Pytest (testes)...
python -m pytest tests/ -v --tb=short --cov=. --cov-report=term
if errorlevel 1 (
    echo *** TESTES FALHARAM ***
    set "FALHOU=1"
) else (
    echo OK
)
echo.

echo [4/4] Bandit (seguranca)...
python -m bandit -r . -ll --exclude=./tests,./build,./dist -q 2>nul
if errorlevel 1 (
    echo *** ALERTAS DE SEGURANCA ***
) else (
    echo OK
)
echo.

echo ==========================================
if "%FALHOU%"=="1" (
    echo  RESULTADO: FALHOU
    echo  Corrija os erros antes de commitar.
) else (
    echo  RESULTADO: TUDO OK
    echo  Pode commitar com seguranca.
)
echo ==========================================
echo.
pause
