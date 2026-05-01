"""Sincronização das pastas lógicas do banco com a raiz do canal no MEGA.

Compara `mega_pasta_logica` (banco, ativas) com a listagem real da raiz de cada
canal no MEGA. Pastas que sumiram do MEGA (admin apagou manualmente) viram
inativas no banco em lote.

Tarefa 2 do !executar.md. Roda 1x/dia, 60s após clicar Iniciar, em thread
separada, lotes de 300. Falha de listagem de qualquer canal → aborta sem
inativar nada (defesa contra inativação em massa indevida quando MEGA
está offline / login falhou).

Estado consumido pela UI via `obter_estado_atual_mega_sync()` — `JanelaSubtarefas`
bloqueia `Declarar Tarefa` enquanto status ∈ {sincronizando, erro,
nao_sincronizado}.
"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Callable, Optional

from app import config as _cfg
from app.mega_uploader import (
    ErroMega,
    ErroPainelHTTP,
    ErroUploadMega,
    MegaUploader,
    PainelMegaApi,
)

LOG = _cfg.LOG_TEC

LOTE_INATIVAR = 300

# Lock interno: garante que não rolem 2 syncs ao mesmo tempo (after timer +
# clique manual em "Iniciar" repetido).
_lock_execucao = threading.Lock()
_thread_atual: Optional[threading.Thread] = None

# Callbacks da UI que querem ser notificados a cada mudança de status.
# `JanelaSubtarefas` registra um callback ao abrir e desregistra ao fechar.
_listeners: list[Callable[[str, dict], None]] = []
_listeners_lock = threading.Lock()


def registrar_listener(cb: Callable[[str, dict], None]) -> None:
    """Adiciona callback chamado em cada mudança de status. Idempotente."""
    with _listeners_lock:
        if cb not in _listeners:
            _listeners.append(cb)


def remover_listener(cb: Callable[[str, dict], None]) -> None:
    with _listeners_lock:
        try:
            _listeners.remove(cb)
        except ValueError:
            pass


def _notificar(user_id: str, estado: dict) -> None:
    with _listeners_lock:
        copia = list(_listeners)
    for cb in copia:
        try:
            cb(user_id, dict(estado))
        except Exception as e:
            LOG.log("MEGA_SYNC", "listener_falhou", {"erro": str(e)})


def _agora_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _hoje_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _atualizar_estado(user_id: str, **mudancas) -> dict:
    estado = _cfg.carregar_estado_mega_sync(user_id)
    estado.update(mudancas)
    _cfg.salvar_estado_mega_sync(user_id, estado)
    _notificar(user_id, estado)
    return estado


def obter_estado_atual_mega_sync(user_id: str) -> dict:
    """Snapshot do estado atual (sem efeitos colaterais)."""
    return _cfg.carregar_estado_mega_sync(user_id)


def _normalizar_nome_pasta_mega(nome: str) -> str:
    """MEGAcmd às vezes adiciona '/' no fim de pastas em alguns formatos.
    Normaliza pra comparar com o banco (que guarda só "NN - Titulo")."""
    return (nome or "").strip().rstrip("/")


def _executar_sincronizacao_blocking(
    user_id: str,
    uploader: MegaUploader,
    api: PainelMegaApi,
) -> tuple[bool, str]:
    """Executa a sync de fato (síncrono). Retorna (ok, mensagem_erro).

    Política conservadora: se a listagem da raiz de QUALQUER canal falhar,
    aborta sem inativar nada (não-fatal pra outros canais? não — abortar
    inteiro é mais seguro: parcial pode dar a falsa impressão de sync ok).
    """
    LOG.log("MEGA_SYNC", "iniciando", {"user_id": user_id})

    try:
        canais = api.pastas_logicas_para_sync()
    except ErroPainelHTTP as e:
        return False, f"Falha ao consultar painel: {e}"
    except Exception as e:
        return False, f"Erro inesperado consultando painel: {e}"

    if not canais:
        LOG.log("MEGA_SYNC", "sem_canais_aplicaveis", {"user_id": user_id})
        return True, ""

    # Login MEGA antes de listar — falha aqui aborta sem mexer no banco.
    try:
        uploader.garantir_logado()
    except ErroMega as e:
        return False, f"Login no MEGA falhou: {e}"
    except Exception as e:
        return False, f"Erro inesperado no login MEGA: {e}"

    ids_para_inativar: list[int] = []
    for canal in canais:
        id_atividade = int(canal.get("id_atividade") or 0)
        titulo = str(canal.get("titulo_atividade") or "")
        raiz = str(canal.get("pasta_raiz_mega") or "").strip()
        pastas_banco = canal.get("pastas_logicas") or []

        if not raiz:
            LOG.log("MEGA_SYNC", "canal_sem_raiz", {"id_atividade": id_atividade, "titulo": titulo})
            continue
        if not pastas_banco:
            continue

        # Lista a raiz uma vez por canal — operação eficiente.
        try:
            nomes_no_mega = uploader.listar(raiz)
        except ErroUploadMega as e:
            return False, f"Falha ao listar canal '{titulo}' no MEGA: {e}"
        except Exception as e:
            return False, f"Erro listando canal '{titulo}' no MEGA: {e}"

        set_mega = {_normalizar_nome_pasta_mega(n) for n in nomes_no_mega}
        for p in pastas_banco:
            nome_banco = _normalizar_nome_pasta_mega(str(p.get("nome_pasta") or ""))
            if not nome_banco:
                continue
            if nome_banco not in set_mega:
                idpl = int(p.get("id_pasta_logica") or 0)
                if idpl > 0:
                    ids_para_inativar.append(idpl)

    if not ids_para_inativar:
        LOG.log("MEGA_SYNC", "nenhuma_pasta_pra_inativar", {"user_id": user_id})
        return True, ""

    LOG.log("MEGA_SYNC", "inativando_em_lote", {"qtd": len(ids_para_inativar)})

    # Lotes de 300 (servidor permite 1000, mas 300 dá timeout folgado).
    for i in range(0, len(ids_para_inativar), LOTE_INATIVAR):
        lote = ids_para_inativar[i : i + LOTE_INATIVAR]
        try:
            api.marcar_pastas_logicas_inativas_lote(lote)
        except ErroPainelHTTP as e:
            return False, f"Falha ao inativar lote no painel: {e}"
        except Exception as e:
            return False, f"Erro inesperado inativando lote: {e}"

    LOG.log("MEGA_SYNC", "concluido_ok", {"user_id": user_id, "inativadas": len(ids_para_inativar)})
    return True, ""


def executar_sincronizacao_async(
    user_id: str,
    uploader: MegaUploader,
    api: PainelMegaApi,
) -> bool:
    """Dispara a sync em thread separada. Retorna True se a thread foi
    iniciada, False se já existe uma em andamento (não enfileira)."""
    global _thread_atual

    if not _lock_execucao.acquire(blocking=False):
        LOG.log("MEGA_SYNC", "ignorada_concorrente", {"user_id": user_id})
        return False

    _atualizar_estado(
        user_id,
        status="sincronizando",
        ultima_tentativa=_agora_iso(),
        mensagem_erro="",
    )

    def _alvo():
        try:
            ok, msg = _executar_sincronizacao_blocking(user_id, uploader, api)
            if ok:
                _atualizar_estado(
                    user_id,
                    status="sincronizado",
                    ultima_sync_ok=_agora_iso(),
                    data_sync_ok=_hoje_str(),
                    mensagem_erro="",
                )
            else:
                _atualizar_estado(
                    user_id,
                    status="erro",
                    mensagem_erro=msg or "erro desconhecido",
                )
        except Exception as e:
            LOG.log("MEGA_SYNC", "erro_inesperado", {"erro": str(e)})
            _atualizar_estado(user_id, status="erro", mensagem_erro=f"Erro inesperado: {e}")
        finally:
            _lock_execucao.release()

    t = threading.Thread(target=_alvo, name=f"MegaSync-{user_id}", daemon=True)
    _thread_atual = t
    t.start()
    return True
