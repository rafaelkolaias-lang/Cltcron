"""Pacote do app desktop Cronômetro Leve.

Estrutura modular extraída do antigo `app.py` monolítico (>4400 linhas).
Entrypoint oficial: `main.py` (na raiz) ou `python -m app`.

O __init__ re-exporta os símbolos consumidos por testes e por callers
externos para preservar compatibilidade com `from app import X`.
"""
from app.config import (
    ARQUIVO_ESTADO_SESSAO,
    ARQUIVO_FILA_OFFLINE,
    ARQUIVO_LOG_TECNICO,
    ARQUIVO_LOGIN_SALVO,
    ARQUIVO_REGRESSIVA,
    HISTORICO_VERSOES,
    INTERVALO_HEARTBEAT_SEGUNDOS,
    INTERVALO_LOOP_SEGUNDOS,
    INTERVALO_SCAN_APPS_SEGUNDOS,
    INTERVALO_STATUS_BANCO_SEGUNDOS,
    INTERVALO_UI_MILISSEGUNDOS,
    INTERVALO_UPSERT_RELATORIO_SEGUNDOS,
    INTERVALO_VERIFICAR_UPDATE_MS,
    LIMITE_HORAS_AVISO,
    LIMITE_HORAS_MAXIMO,
    LIMITE_OCIOSO_SEGUNDOS,
    LOG_TEC,
    MODO_SCRIPT,
    TOLERANCIA_VALIDACAO_SEGUNDOS,
    URL_ATUALIZACAO,
    VERSAO_APLICACAO,
    LogTecnico,
)
from app.hooks_input import DetectorInputSintetico
from app.monitor import EstadoMonitor, MonitorDeUso
from app.win32_utils import (
    converter_segundos_para_inteiro,
    dividir_tempos_por_dia,
    formatar_hhmmss,
    listar_nomes_apps_visiveis,
    obter_aplicativo_em_foco,
    obter_segundos_ocioso_windows,
)

__all__ = [
    "ARQUIVO_ESTADO_SESSAO",
    "ARQUIVO_FILA_OFFLINE",
    "ARQUIVO_LOG_TECNICO",
    "ARQUIVO_LOGIN_SALVO",
    "ARQUIVO_REGRESSIVA",
    "DetectorInputSintetico",
    "EstadoMonitor",
    "HISTORICO_VERSOES",
    "INTERVALO_HEARTBEAT_SEGUNDOS",
    "INTERVALO_LOOP_SEGUNDOS",
    "INTERVALO_SCAN_APPS_SEGUNDOS",
    "INTERVALO_STATUS_BANCO_SEGUNDOS",
    "INTERVALO_UI_MILISSEGUNDOS",
    "INTERVALO_UPSERT_RELATORIO_SEGUNDOS",
    "INTERVALO_VERIFICAR_UPDATE_MS",
    "LIMITE_HORAS_AVISO",
    "LIMITE_HORAS_MAXIMO",
    "LIMITE_OCIOSO_SEGUNDOS",
    "LOG_TEC",
    "LogTecnico",
    "MODO_SCRIPT",
    "MonitorDeUso",
    "TOLERANCIA_VALIDACAO_SEGUNDOS",
    "URL_ATUALIZACAO",
    "VERSAO_APLICACAO",
    "converter_segundos_para_inteiro",
    "dividir_tempos_por_dia",
    "formatar_hhmmss",
    "listar_nomes_apps_visiveis",
    "obter_aplicativo_em_foco",
    "obter_segundos_ocioso_windows",
]
