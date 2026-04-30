"""MonitorDeUso e EstadoMonitor — coração do cronômetro.

Encapsula sessão, heartbeat, fila offline, foco/apps, persistência local
e integração com o detector de input sintético.
"""
from __future__ import annotations

import ctypes
import json
import platform
import socket
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime

from banco import BancoDados

from app.config import (
    ARQUIVO_ESTADO_SESSAO,
    ARQUIVO_FILA_OFFLINE,
    INTERVALO_HEARTBEAT_SEGUNDOS,
    INTERVALO_LOOP_SEGUNDOS,
    INTERVALO_SCAN_APPS_SEGUNDOS,
    INTERVALO_STATUS_BANCO_SEGUNDOS,
    INTERVALO_UPSERT_RELATORIO_SEGUNDOS,
    LIMITE_HORAS_MAXIMO,
    LIMITE_OCIOSO_SEGUNDOS,
    LOG_TEC,
    VERSAO_APLICACAO,
)
from app.hooks_input import DetectorInputSintetico
from app.win32_utils import (
    converter_segundos_para_inteiro,
    dividir_tempos_por_dia,
    listar_nomes_apps_visiveis,
    obter_aplicativo_em_foco,
    obter_segundos_ocioso_windows,
)


@dataclass
class EstadoMonitor:
    rodando: bool
    situacao: str
    segundos_trabalhando: int
    segundos_ocioso: int
    segundos_pausado: int
    ultimo_erro: str
    # T24: feedback visual rico na UI
    offline: bool = False          # True quando a app está em modo offline
    mensagem_sucesso: str = ""     # mensagem transitória (auto-expira; ex.: "fila re-enviada")


class MonitorDeUso:
    def __init__(self, banco: BancoDados) -> None:
        self._banco = banco
        self._trava = threading.Lock()
        self._parar = threading.Event()
        self._thread_loop: threading.Thread | None = None

        self._id_sessao: int | None = None
        self._token_sessao: str = ""
        self._referencia_data_sessao: date | None = None

        self._user_id: str = ""
        self._nome_exibicao: str = ""
        self._id_atividade: int = 0
        self._titulo_atividade: str = ""

        self._sessao_carregada: bool = False
        self._rodando: bool = False
        self._situacao_manual: str = "pausado"
        self._situacao_calculada: str = "pausado"

        self._segundos_trabalhando_float: float = 0.0
        self._segundos_ocioso_float: float = 0.0
        self._segundos_pausado_float: float = 0.0

        self._nome_app_foco: str = "desconhecido"
        self._titulo_janela_foco: str = ""
        self._id_foco_aberto: int | None = None
        # Acumulação cumulativa do foco atual — espelha o padrão de cronometro_apps_intervalos.
        # Se o app crashar, o último UPDATE periódico já gravou os segundos até ali, eliminando
        # o "fantasma de 3h" que vinha do cap aplicado a registros com fim_em IS NULL.
        self._segundos_em_foco_atual: int = 0
        self._mono_ultimo_acumulo_foco: float = 0.0
        self._mono_ultimo_flush_foco: float = 0.0

        self._ultimo_heartbeat_mono: float = 0.0
        self._ultimo_sync_status_mono: float = 0.0
        self._ultimo_flush_fila_mono: float = 0.0
        self._ultimo_marco_mono: float = 0.0
        self._ultimo_upsert_relatorio_mono: float = 0.0
        self._ultimo_erro: str = ""
        self._offline_notificado: bool = False
        # T24: mensagem transitória de sucesso (auto-expira no snapshot após ~10s)
        self._mensagem_sucesso: str = ""
        self._mensagem_sucesso_expira_mono: float = 0.0

        self._mapa_intervalos_apps: dict[str, dict] = {}
        self._ultimo_scan_apps_mono: float = 0.0
        self._ultimo_save_estado_mono: float = 0.0
        self._inicio_sessao_cache: datetime | None = None
        # Cache de sessões já validadas no banco — evita repetir SELECT por item no flush offline.
        self._cache_sessoes_validas: dict[int, bool] = {}

        # Fase 2 — Detector de input humano vs sintético (auto-clickers)
        # Roda em thread separada com hooks low-level. Operação transparente:
        # não altera o cálculo de horas, só registra em cronometro_input_stats.
        self._detector_input = DetectorInputSintetico()

    def _registrar_erro_locked(self, mensagem: str) -> None:
        self._ultimo_erro = (mensagem or "").strip()[:240]

    def _registrar_sucesso_locked(self, mensagem: str, segundos: float = 10.0) -> None:
        """Mensagem transitória de sucesso — auto-expira após `segundos` via snapshot."""
        self._mensagem_sucesso = (mensagem or "").strip()[:240]
        self._mensagem_sucesso_expira_mono = time.monotonic() + max(0.0, segundos)

    def _snapshot_locked(self) -> EstadoMonitor:
        trabalhando = self._segundos_trabalhando_float
        ocioso = self._segundos_ocioso_float
        pausado = self._segundos_pausado_float

        if self._rodando and self._ultimo_marco_mono > 0:
            agora = time.monotonic()
            delta = max(0.0, agora - self._ultimo_marco_mono)

            if self._situacao_manual == "pausado":
                pausado += delta
            else:
                if self._situacao_calculada == "ocioso":
                    ocioso += delta
                else:
                    trabalhando += delta

        # Expira mensagem transitória de sucesso após o tempo configurado.
        msg_sucesso = self._mensagem_sucesso
        if msg_sucesso and time.monotonic() >= self._mensagem_sucesso_expira_mono:
            self._mensagem_sucesso = ""
            msg_sucesso = ""

        return EstadoMonitor(
            rodando=self._rodando,
            situacao=self._situacao_calculada,
            segundos_trabalhando=converter_segundos_para_inteiro(trabalhando),
            segundos_ocioso=converter_segundos_para_inteiro(ocioso),
            segundos_pausado=converter_segundos_para_inteiro(pausado),
            ultimo_erro=self._ultimo_erro,
            offline=self._offline_notificado,
            mensagem_sucesso=msg_sucesso,
        )

    def obter_estado(self) -> EstadoMonitor:
        with self._trava:
            return self._snapshot_locked()

    def tem_sessao_carregada(self) -> bool:
        with self._trava:
            return self._sessao_carregada

    def _delta_tempo_locked(self) -> float:
        if self._rodando and self._ultimo_marco_mono > 0:
            return max(0.0, time.monotonic() - self._ultimo_marco_mono)
        return 0.0

    def obter_segundos_cronometro(self) -> int:
        with self._trava:
            delta = self._delta_tempo_locked()
            trab = self._segundos_trabalhando_float
            ocioso = self._segundos_ocioso_float
            if self._situacao_manual != "pausado":
                if self._situacao_calculada == "ocioso":
                    ocioso += delta
                else:
                    trab += delta
            return int(trab + ocioso)

    def obter_segundos_trabalhando(self) -> int:
        with self._trava:
            delta = self._delta_tempo_locked()
            trab = self._segundos_trabalhando_float
            if self._situacao_manual != "pausado" and self._situacao_calculada != "ocioso":
                trab += delta
            return int(trab)

    def obter_segundos_pausado(self) -> int:
        with self._trava:
            delta = self._delta_tempo_locked()
            pausado = self._segundos_pausado_float
            if self._situacao_manual == "pausado":
                pausado += delta
            return int(pausado)

    def _acumular_tempo_ate_agora_locked(self, mono_agora: float) -> None:
        if self._ultimo_marco_mono <= 0:
            self._ultimo_marco_mono = mono_agora
            return

        if not self._rodando:
            self._ultimo_marco_mono = mono_agora
            return

        delta = max(0.0, mono_agora - self._ultimo_marco_mono)
        if delta <= 0:
            return

        if self._situacao_manual == "pausado":
            self._segundos_pausado_float += delta
        else:
            if self._situacao_calculada == "ocioso":
                self._segundos_ocioso_float += delta
            else:
                # Não acumula acima do limite máximo
                if self._segundos_trabalhando_float < LIMITE_HORAS_MAXIMO:
                    self._segundos_trabalhando_float = min(
                        self._segundos_trabalhando_float + delta,
                        float(LIMITE_HORAS_MAXIMO),
                    )

        self._ultimo_marco_mono = mono_agora

    def _inserir_evento(
        self,
        tipo_evento: str,
        situacao: str,
        idle_segundos: int,
        id_sessao: int | None = None,
        user_id: str | None = None,
        ocorrido_em: datetime | None = None,
    ) -> None:
        _id = id_sessao if id_sessao is not None else self._id_sessao
        _uid = user_id if user_id is not None else self._user_id
        if _id is None or not _uid:
            return

        try:
            self._banco.executar(
                """
                INSERT INTO cronometro_eventos_status
                    (id_sessao, user_id, tipo_evento, situacao, ocorrido_em, idle_segundos)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [_id, _uid, tipo_evento, situacao, ocorrido_em or datetime.now(), int(idle_segundos)],
            )
            LOG_TEC.log("evento", f"{tipo_evento} -> {situacao}", {
                "id_sessao": _id, "user_id": _uid, "idle": int(idle_segundos),
            })
        except Exception as erro:
            LOG_TEC.log("evento_erro", f"falha ao inserir {tipo_evento}", {"erro": str(erro)})
            raise

    def _flush_input_stats_locked_free(self) -> None:
        """
        Lê o snapshot acumulado pelo DetectorInputSintetico desde o último
        flush e insere uma linha em cronometro_input_stats. Chamado pelo loop
        fora de self._trava (por isso o sufixo _locked_free).
        """
        # Snapshot leve (só copia e zera os contadores do detector)
        seg_humano, seg_sintetico, min_ts, max_ts = self._detector_input.snapshot_e_limpar()
        if seg_humano == 0 and seg_sintetico == 0:
            return

        # Captura campos de sessão (snapshot atômico)
        with self._trava:
            id_sessao = self._id_sessao
            user_id = self._user_id
            ref_data = self._referencia_data_sessao or date.today()

        if id_sessao is None or not user_id:
            return

        bucket_inicio_em = (
            datetime.fromtimestamp(min_ts) if min_ts > 0 else datetime.now()
        )

        try:
            self._banco.executar(
                """
                INSERT INTO cronometro_input_stats
                    (id_sessao, user_id, bucket_inicio_em,
                     segundos_input_humano, segundos_input_sintetico, referencia_data)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [
                    id_sessao, user_id, bucket_inicio_em,
                    int(seg_humano), int(seg_sintetico), ref_data,
                ],
            )
            LOG_TEC.log("detector_input", "stats gravado", {
                "id_sessao": id_sessao,
                "humano": int(seg_humano),
                "sintetico": int(seg_sintetico),
                "ref_data": str(ref_data),
            })
        except Exception as erro:
            LOG_TEC.log("detector_input", "falha ao gravar stats", {"erro": str(erro)})
            # não propaga — perder um bucket não é crítico

    # --- Fila offline ---

    def _carregar_fila_offline(self) -> list[dict]:
        try:
            if ARQUIVO_FILA_OFFLINE.exists():
                return json.loads(ARQUIVO_FILA_OFFLINE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _salvar_fila_offline(self, fila: list[dict]) -> None:
        try:
            ARQUIVO_FILA_OFFLINE.write_text(
                json.dumps(fila, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _adicionar_a_fila_offline(
        self,
        tipo_evento: str,
        situacao: str,
        idle_segundos: int,
        ocorrido_em: datetime | None = None,
    ) -> None:
        fila = self._carregar_fila_offline()
        tam_antes = len(fila)
        ocorrido_iso = (ocorrido_em or datetime.now()).isoformat()
        fila.append({
            "tipo_evento": tipo_evento,
            "situacao": situacao,
            "idle_segundos": idle_segundos,
            "id_sessao": self._id_sessao,
            "user_id": self._user_id,
            "ocorrido_em": ocorrido_iso,
        })
        self._salvar_fila_offline(fila)
        LOG_TEC.log("offline_fila", f"+{tipo_evento}", {
            "tipo_evento": tipo_evento,
            "situacao": situacao,
            "idle": int(idle_segundos),
            "id_sessao": self._id_sessao,
            "user_id": self._user_id,
            "ocorrido_em": ocorrido_iso,
            "fila_antes": tam_antes,
            "fila_depois": len(fila),
        })

    def _sessao_valida_para_replay(self, id_sessao) -> bool | None:
        """Verifica se `id_sessao` existe em `cronometro_sessoes`.
        Retorna True/False se conseguiu consultar, ou None se o banco estiver inacessível
        (nesse caso o caller deve manter o item na fila, não descartar).
        Usa cache local para evitar SELECT repetido por item.
        """
        try:
            ids = int(id_sessao)
        except (TypeError, ValueError):
            return False
        if ids <= 0:
            return False
        if ids in self._cache_sessoes_validas:
            return self._cache_sessoes_validas[ids]
        try:
            linha = self._banco.consultar_um(
                "SELECT 1 AS ok FROM cronometro_sessoes WHERE id_sessao = %s LIMIT 1",
                [ids],
            )
        except Exception:
            return None  # banco indisponível
        valido = linha is not None
        self._cache_sessoes_validas[ids] = valido
        return valido

    def _tentar_flush_fila_offline(self) -> None:
        """Re-envia eventos pendentes. Descarta itens órfãos (sessão inexistente / FK violation)
        em vez de travar a fila. Preserva itens válidos e retoma no próximo tick em caso de
        erro genuíno de conexão.
        """
        fila = self._carregar_fila_offline()
        if not fila:
            return
        tam_inicial = len(fila)
        inicio_flush = datetime.now()
        LOG_TEC.log("offline_flush_inicio", f"tentando reenviar {tam_inicial}", {
            "fila_tam": tam_inicial,
            "iniciado_em": inicio_flush.isoformat(),
        })

        nova_fila: list[dict] = []
        enviados = 0
        descartados = 0
        falhou_conexao = False
        falhou_em: dict | None = None

        for idx, item in enumerate(fila):
            if falhou_conexao:
                # Preserva restante; a fila retoma no próximo flush.
                nova_fila.append(item)
                continue

            id_sessao_item = item.get("id_sessao")
            # Primeiro valida a sessão. None = banco indisponível → aborta flush preservando item.
            validade = self._sessao_valida_para_replay(id_sessao_item)
            if validade is None:
                falhou_em = {"tipo_evento": item.get("tipo_evento"), "indice": idx, "erro": "banco_indisponivel"}
                LOG_TEC.log("offline_flush_item", f"FALHA_CONEXAO {item.get('tipo_evento','')}", falhou_em)
                nova_fila.append(item)
                falhou_conexao = True
                continue
            if validade is False:
                LOG_TEC.log("offline_flush_item", f"DESCARTADO_ORFAO {item.get('tipo_evento','')}", {
                    "tipo_evento": item.get("tipo_evento"),
                    "id_sessao": id_sessao_item,
                    "motivo": "sessao_inexistente",
                    "indice": idx,
                })
                descartados += 1
                continue

            try:
                ocorrido = datetime.fromisoformat(item["ocorrido_em"])
                self._banco.executar(
                    """
                    INSERT INTO cronometro_eventos_status
                        (id_sessao, user_id, tipo_evento, situacao, ocorrido_em, idle_segundos)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        item["id_sessao"],
                        item["user_id"],
                        item["tipo_evento"],
                        item["situacao"],
                        ocorrido,
                        int(item["idle_segundos"]),
                    ],
                )
                LOG_TEC.log("offline_flush_item", f"OK {item.get('tipo_evento', '')}", {
                    "tipo_evento": item.get("tipo_evento"),
                    "situacao": item.get("situacao"),
                    "id_sessao": item.get("id_sessao"),
                    "user_id": item.get("user_id"),
                    "ocorrido_em": item.get("ocorrido_em"),
                    "indice": idx,
                })
                enviados += 1
            except Exception as erro:
                msg_erro = str(erro).lower()
                # FK violation ou sessão sumiu entre validação e INSERT → descarta, não bloqueia.
                if "foreign key" in msg_erro or "1452" in msg_erro or "fk" in msg_erro:
                    LOG_TEC.log("offline_flush_item", f"DESCARTADO_FK {item.get('tipo_evento','')}", {
                        "tipo_evento": item.get("tipo_evento"),
                        "id_sessao": id_sessao_item,
                        "motivo": "fk_violation",
                        "erro": str(erro),
                        "indice": idx,
                    })
                    descartados += 1
                    # Invalida a sessão no cache para os próximos itens
                    try: self._cache_sessoes_validas[int(id_sessao_item)] = False
                    except Exception: pass
                else:
                    falhou_em = {"tipo_evento": item.get("tipo_evento"), "indice": idx, "erro": str(erro)}
                    LOG_TEC.log("offline_flush_item", f"FALHA {item.get('tipo_evento','')}", falhou_em)
                    nova_fila.append(item)
                    falhou_conexao = True

        pendentes = len(nova_fila)
        # Sempre persiste — para remover itens descartados mesmo quando nada foi enviado.
        self._salvar_fila_offline(nova_fila)

        conexao_saiu_do_offline = False
        if (enviados > 0 or descartados > 0) and pendentes == 0 and self._offline_notificado:
            self._offline_notificado = False
            self._notificar_conexao_restaurada(enviados)
            conexao_saiu_do_offline = True
            LOG_TEC.log("conexao_restaurada", f"fila limpa — enviados={enviados} descartados={descartados}", {
                "reenviados": enviados,
                "descartados": descartados,
            })

        if enviados > 0 or descartados > 0:
            msg = (
                f"Fila offline: {enviados} eventos re-enviados"
                + (f", {descartados} descartados" if descartados else "")
                + (f", {pendentes} ainda pendentes" if pendentes else " (fila limpa)")
            )
            # Mensagem transitória (auto-some em ~10s). Não usa _registrar_erro_locked para
            # não ficar com aparência de erro persistente na UI.
            self._registrar_sucesso_locked(msg, 10.0)

        LOG_TEC.log("offline_flush_fim", f"enviados={enviados} descartados={descartados} pendentes={pendentes}", {
            "tam_inicial": tam_inicial,
            "enviados": enviados,
            "descartados": descartados,
            "pendentes": pendentes,
            "duracao_seg": (datetime.now() - inicio_flush).total_seconds(),
            "falhou_em": falhou_em,
        })

        # Consolida tempos parciais imediatamente ao sair do offline — o painel web
        # enxerga o período offline sem depender de replay evento a evento.
        if conexao_saiu_do_offline:
            try:
                self._upsert_relatorio_parcial()
                LOG_TEC.log("conexao_restaurada", "relatorio parcial consolidado apos reconexao")
            except Exception as erro:
                LOG_TEC.log("conexao_erro", "falha ao consolidar parcial pos-reconexao", {"erro": str(erro)})

    def _notificar_sem_conexao(self) -> None:
        """Popup Windows não-bloqueante avisando sobre queda de conexão."""
        def _popup() -> None:
            ctypes.windll.user32.MessageBoxW(
                0,
                "O Cronômetro perdeu a conexão com o servidor.\n\n"
                "O cronômetro continua rodando normalmente.\n"
                "Os dados serão enviados automaticamente quando a conexão voltar.",
                "Cronômetro — Sem conexão com o servidor",
                0x00010030,  # MB_OK | MB_ICONWARNING | MB_SETFOREGROUND
            )
        threading.Thread(target=_popup, daemon=True).start()

    def _notificar_conexao_restaurada(self, eventos_enviados: int) -> None:
        """Popup Windows não-bloqueante avisando que a conexão voltou."""
        def _popup() -> None:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Conexão com o servidor restaurada!\n\n"
                f"{eventos_enviados} evento(s) pendente(s) foram enviados com sucesso.",
                "Cronômetro — Conexão restaurada",
                0x00010040,  # MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND
            )
        threading.Thread(target=_popup, daemon=True).start()

    def _sanear_registros_abertos_do_usuario(self, user_id: str) -> None:
        """Fecha registros antigos com fim_em IS NULL, aplicando caps de sanidade:
        - cronometro_foco_janela:
            - se segundos_em_foco > 0 (cliente novo): usa inicio_em + segundos_em_foco como verdade.
            - senão (registros legados): cap de 3h sobre inicio_em — só pra não deixar fim_em nulo.
        - cronometro_apps_intervalos: teto de 20h por período (app aberto acima disso é fantasma).
        Roda antes de iniciar/restaurar sessão para não deixar lixo legado poluindo gráficos.
        """
        uid = (user_id or "").strip()
        if not uid:
            return
        try:
            # Registros novos (segundos_em_foco > 0): a duração real foi acumulada
            # em tempo real pelo _flush_foco_periodico até o crash. Fecha exatamente em
            # inicio_em + segundos_em_foco — sem inflar até cap arbitrário.
            linhas_foco_novos = self._banco.executar_e_contar(
                """
                UPDATE cronometro_foco_janela
                   SET fim_em = DATE_ADD(inicio_em, INTERVAL segundos_em_foco SECOND)
                 WHERE user_id = %s
                   AND fim_em IS NULL
                   AND segundos_em_foco > 0
                """,
                [uid],
            )
            # Registros legados (segundos_em_foco = 0, cliente antigo): cap de 3h como fallback.
            linhas_foco_legados = self._banco.executar_e_contar(
                """
                UPDATE cronometro_foco_janela
                   SET fim_em = DATE_ADD(inicio_em, INTERVAL 3 HOUR)
                 WHERE user_id = %s
                   AND fim_em IS NULL
                   AND segundos_em_foco = 0
                   AND inicio_em < NOW() - INTERVAL 3 HOUR
                """,
                [uid],
            )
            linhas_foco = int(linhas_foco_novos) + int(linhas_foco_legados)
            linhas_apps = self._banco.executar_e_contar(
                """
                UPDATE cronometro_apps_intervalos
                   SET fim_em = DATE_ADD(inicio_em, INTERVAL 20 HOUR)
                 WHERE user_id = %s
                   AND fim_em IS NULL
                   AND inicio_em < NOW() - INTERVAL 20 HOUR
                """,
                [uid],
            )
            # Só loga se houve limpeza real — evita poluir o log com "nada fechado" em cada iniciar/restaurar.
            if linhas_foco > 0 or linhas_apps > 0:
                LOG_TEC.log("saneamento", f"user={uid}", {
                    "foco_fechados": linhas_foco,
                    "apps_fechados": linhas_apps,
                })
        except Exception as erro:
            LOG_TEC.log("saneamento_erro", f"user={uid}", {"erro": str(erro)})

    def _abrir_foco(self, nome_app: str, titulo: str) -> None:
        if self._id_sessao is None:
            return

        self._id_foco_aberto = self._banco.executar(
            """
            INSERT INTO cronometro_foco_janela
                (id_sessao, user_id, nome_app, titulo_janela, inicio_em, fim_em, segundos_em_foco)
            VALUES (%s, %s, %s, %s, %s, NULL, 0)
            """,
            [self._id_sessao, self._user_id, nome_app, (titulo or None), datetime.now()],
        )
        # Reseta contadores cumulativos do foco recém-aberto.
        self._segundos_em_foco_atual = 0
        self._mono_ultimo_acumulo_foco = time.monotonic()
        self._mono_ultimo_flush_foco = self._mono_ultimo_acumulo_foco
        LOG_TEC.log("foco", f"abrir {nome_app}", {"titulo": titulo or "", "id_foco": self._id_foco_aberto})

    def _fechar_foco(self) -> None:
        if self._id_foco_aberto is None:
            return

        # Antes de fechar, acumula o tempo restante desde o último acúmulo.
        self._acumular_foco_locked(time.monotonic())

        self._banco.executar(
            "UPDATE cronometro_foco_janela SET fim_em = %s, segundos_em_foco = %s WHERE id_foco = %s",
            [datetime.now(), int(self._segundos_em_foco_atual), self._id_foco_aberto],
        )
        LOG_TEC.log("foco", "fechar", {
            "id_foco": self._id_foco_aberto,
            "segundos_em_foco": int(self._segundos_em_foco_atual),
        })
        self._id_foco_aberto = None
        self._segundos_em_foco_atual = 0
        self._mono_ultimo_acumulo_foco = 0.0
        self._mono_ultimo_flush_foco = 0.0

    def _acumular_foco_locked(self, mono_agora: float) -> None:
        """Soma delta desde o último acúmulo no contador em memória.

        Chamado a cada tick do _loop e antes de qualquer UPDATE/fechamento.
        Operação puramente em memória — UPDATE periódico vai pra _flush_foco_periodico.
        """
        if self._id_foco_aberto is None:
            return
        if self._mono_ultimo_acumulo_foco <= 0:
            self._mono_ultimo_acumulo_foco = mono_agora
            return
        delta = mono_agora - self._mono_ultimo_acumulo_foco
        if delta <= 0:
            return
        self._segundos_em_foco_atual += int(delta)
        self._mono_ultimo_acumulo_foco = mono_agora

    def _flush_foco_periodico(self, mono_agora: float, intervalo: float) -> bool:
        """Grava segundos_em_foco no banco a cada `intervalo` segundos (sem fechar fim_em).

        Retorna True se houve flush. Chamado FORA do lock — id e segundos são
        snapshots resolvidos antes da chamada.
        """
        if self._id_foco_aberto is None:
            return False
        if (mono_agora - self._mono_ultimo_flush_foco) < intervalo:
            return False
        id_snap = self._id_foco_aberto
        seg_snap = int(self._segundos_em_foco_atual)
        self._mono_ultimo_flush_foco = mono_agora
        try:
            self._banco.executar(
                "UPDATE cronometro_foco_janela SET segundos_em_foco = %s WHERE id_foco = %s",
                [seg_snap, id_snap],
            )
        except Exception:
            return False
        return True

    def _abrir_intervalo_app_locked(self, nome_app: str) -> int | None:
        if self._id_sessao is None or not self._user_id:
            return None
        return self._banco.executar(
            """
            INSERT INTO cronometro_apps_intervalos
                (id_sessao, user_id, nome_app, inicio_em, segundos_em_foco, segundos_segundo_plano)
            VALUES (%s, %s, %s, %s, 0, 0)
            """,
            [self._id_sessao, self._user_id, nome_app, datetime.now()],
        )

    def _atualizar_intervalos_apps_locked(self, apps_visiveis: set[str], delta: int) -> None:
        nome_foco = self._nome_app_foco or "desconhecido"
        agora = datetime.now()

        # Acumula deltas em memória e fecha apps que sumiram
        apps_fechados = []
        for nome_app in list(self._mapa_intervalos_apps.keys()):
            dados = self._mapa_intervalos_apps[nome_app]
            if nome_app in apps_visiveis:
                if nome_app == nome_foco:
                    dados["segundos_em_foco"] += delta
                else:
                    dados["segundos_segundo_plano"] += delta
            else:
                apps_fechados.append(nome_app)

        # Batch UPDATE de todos os apps ativos + fechados em uma operação
        for nome_app in apps_fechados:
            dados = self._mapa_intervalos_apps.pop(nome_app)
            try:
                self._banco.executar(
                    """
                    UPDATE cronometro_apps_intervalos
                    SET fim_em = %s, segundos_em_foco = %s, segundos_segundo_plano = %s
                    WHERE id_intervalo = %s
                    """,
                    [agora, dados["segundos_em_foco"], dados["segundos_segundo_plano"], dados["id_intervalo"]],
                )
            except Exception:
                pass

        # Batch UPDATE dos apps ativos (uma query com executar_muitos)
        updates_ativos = []
        for dados in self._mapa_intervalos_apps.values():
            updates_ativos.append([dados["segundos_em_foco"], dados["segundos_segundo_plano"], dados["id_intervalo"]])
        if updates_ativos:
            try:
                self._banco.executar_muitos(
                    """
                    UPDATE cronometro_apps_intervalos
                    SET segundos_em_foco = %s, segundos_segundo_plano = %s
                    WHERE id_intervalo = %s
                    """,
                    updates_ativos,
                )
            except Exception:
                pass

        # Abre intervalos para apps novos (INSERT já com valores corretos, sem UPDATE extra)
        for nome_app in apps_visiveis:
            if nome_app in self._mapa_intervalos_apps:
                continue
            try:
                seg_foco = delta if nome_app == nome_foco else 0
                seg_bg = 0 if nome_app == nome_foco else delta
                id_intervalo = self._banco.executar(
                    """
                    INSERT INTO cronometro_apps_intervalos
                        (id_sessao, user_id, nome_app, inicio_em, segundos_em_foco, segundos_segundo_plano)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [self._id_sessao, self._user_id, nome_app, agora, seg_foco, seg_bg],
                )
                if id_intervalo:
                    self._mapa_intervalos_apps[nome_app] = {
                        "id_intervalo": id_intervalo,
                        "segundos_em_foco": seg_foco,
                        "segundos_segundo_plano": seg_bg,
                    }
            except Exception:
                pass

    def _fechar_todos_intervalos_apps_locked(self) -> None:
        if not self._mapa_intervalos_apps:
            return
        agora = datetime.now()
        for dados in self._mapa_intervalos_apps.values():
            try:
                self._banco.executar(
                    """
                    UPDATE cronometro_apps_intervalos
                    SET fim_em = %s, segundos_em_foco = %s, segundos_segundo_plano = %s
                    WHERE id_intervalo = %s
                    """,
                    [agora, dados["segundos_em_foco"], dados["segundos_segundo_plano"], dados["id_intervalo"]],
                )
            except Exception:
                pass
        self._mapa_intervalos_apps.clear()

    def _montar_atividade_status_locked(self) -> str:
        titulo = (self._titulo_atividade or "").strip()
        if not titulo:
            return ""
        return titulo[:255]

    def _montar_apps_json_locked(self) -> str:
        nome_foco = self._nome_app_foco or "desconhecido"
        abertos: list[dict] = []
        for nome_app, dados in self._mapa_intervalos_apps.items():
            if not nome_app or nome_app == "desconhecido":
                continue
            abertos.append({
                "nome_app": nome_app,
                "em_foco": nome_app == nome_foco,
                "segundos_em_foco": int(dados.get("segundos_em_foco", 0) or 0),
                "segundos_segundo_plano": int(dados.get("segundos_segundo_plano", 0) or 0),
            })
        abertos.sort(key=lambda item: (
            0 if item.get("em_foco") else 1,
            -int(item.get("segundos_em_foco", 0) or 0) - int(item.get("segundos_segundo_plano", 0) or 0),
            str(item.get("nome_app", "")),
        ))
        payload = {
            "abertos": abertos,
            "em_foco": {
                "nome_app": nome_foco,
                "titulo_janela": self._titulo_janela_foco or "",
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    def _atualizar_status_atual_locked(self) -> None:
        if not self._user_id:
            return

        situacao = self._situacao_calculada or "pausado"
        atividade = self._montar_atividade_status_locked()
        inicio_em = getattr(self, "_inicio_sessao_cache", None)

        if inicio_em is None and self._id_sessao is not None:
            linha_sessao = self._banco.consultar_um(
                "SELECT iniciado_em FROM cronometro_sessoes WHERE id_sessao = %s LIMIT 1",
                [self._id_sessao],
            )
            if linha_sessao:
                inicio_em = linha_sessao["iniciado_em"]
                self._inicio_sessao_cache = inicio_em

        apps_json = self._montar_apps_json_locked()
        agora = datetime.now()
        segundos_pausado = int(self._segundos_pausado_float)

        try:
            self._banco.executar(
                """
                INSERT INTO usuarios_status_atual
                    (user_id, situacao, atividade, inicio_em, ultimo_em, segundos_pausado, apps_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    situacao = VALUES(situacao),
                    atividade = VALUES(atividade),
                    inicio_em = VALUES(inicio_em),
                    ultimo_em = VALUES(ultimo_em),
                    segundos_pausado = VALUES(segundos_pausado),
                    apps_json = VALUES(apps_json)
                """,
                [self._user_id, situacao, atividade, inicio_em, agora, segundos_pausado, apps_json],
            )
            LOG_TEC.log("status_banco", f"upsert user={self._user_id} sit={situacao}", {
                "segundos_pausado": segundos_pausado,
                "apps_json_tam": len(apps_json or ""),
            })
        except Exception as erro:
            LOG_TEC.log("status_erro", f"falha upsert user={self._user_id}", {"erro": str(erro)})
            raise

    def _limpar_status_atual(self) -> None:
        if not self._user_id:
            return

        apps_json = json.dumps(
            {"abertos": [], "em_foco": {"nome_app": "desconhecido", "titulo_janela": ""}},
            ensure_ascii=False,
        )

        self._banco.executar(
            """
            INSERT INTO usuarios_status_atual
                (user_id, situacao, atividade, inicio_em, ultimo_em, segundos_pausado, apps_json)
            VALUES (%s, %s, %s, NULL, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                situacao = VALUES(situacao),
                atividade = VALUES(atividade),
                inicio_em = NULL,
                ultimo_em = VALUES(ultimo_em),
                segundos_pausado = VALUES(segundos_pausado),
                apps_json = VALUES(apps_json)
            """,
            [self._user_id, "pausado", "", datetime.now(), 0, apps_json],
        )

    def _salvar_estado_local_locked(self, sessao_em_aberto: bool) -> None:
        estado = self._snapshot_locked()

        dados = {
            "sessao_em_aberto": bool(sessao_em_aberto),
            "id_sessao": self._id_sessao,
            "token_sessao": self._token_sessao,
            "user_id": self._user_id,
            "nome_exibicao": self._nome_exibicao,
            "id_atividade": self._id_atividade,
            "titulo_atividade": self._titulo_atividade,
            "situacao_manual": self._situacao_manual,
            "situacao_calculada": self._situacao_calculada,
            "segundos_trabalhando": float(estado.segundos_trabalhando),
            "segundos_ocioso": float(estado.segundos_ocioso),
            "segundos_pausado": float(estado.segundos_pausado),
            "versao_app": VERSAO_APLICACAO,
            "salvo_em": datetime.now().isoformat(),
        }

        try:
            ARQUIVO_ESTADO_SESSAO.write_text(
                json.dumps(dados, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _limpar_estado_local(self) -> None:
        try:
            if ARQUIVO_ESTADO_SESSAO.exists():
                ARQUIVO_ESTADO_SESSAO.unlink()
        except Exception:
            pass

    def _carregar_estado_local(self) -> dict | None:
        try:
            if not ARQUIVO_ESTADO_SESSAO.exists():
                return None
            return json.loads(ARQUIVO_ESTADO_SESSAO.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _sessao_do_banco_esta_aberta(self, id_sessao: int, token_sessao: str, user_id: str) -> bool:
        linha = self._banco.consultar_um(
            """
            SELECT id_sessao
            FROM cronometro_sessoes
            WHERE id_sessao = %s
              AND token_sessao = %s
              AND user_id = %s
              AND finalizado_em IS NULL
            LIMIT 1
            """,
            [int(id_sessao), str(token_sessao), str(user_id)],
        )
        return bool(linha)

    def obter_dados_sessao_pendente_do_usuario(self, user_id: str) -> dict | None:
        dados = self._carregar_estado_local()
        if not dados:
            return None

        if str(dados.get("user_id") or "").strip() != (user_id or "").strip():
            return None

        if not bool(dados.get("sessao_em_aberto")):
            return None

        id_sessao = int(dados.get("id_sessao") or 0)
        token_sessao = str(dados.get("token_sessao") or "").strip()
        if id_sessao <= 0 or not token_sessao:
            return None

        try:
            if not self._sessao_do_banco_esta_aberta(id_sessao, token_sessao, user_id):
                return None
        except Exception:
            return None

        return dados

    def restaurar_sessao(self, dados: dict, nome_exibicao_atual: str) -> None:
        # Fecha registros antigos pendurados antes de restaurar — evita lixo legado nos gráficos.
        self._sanear_registros_abertos_do_usuario(str(dados.get("user_id") or "").strip())
        with self._trava:
            if self._thread_loop and self._thread_loop.is_alive():
                raise RuntimeError("Já existe uma sessão em execução.")

            self._id_sessao = int(dados.get("id_sessao") or 0)
            self._token_sessao = str(dados.get("token_sessao") or "").strip()
            self._referencia_data_sessao = date.today()
            self._user_id = str(dados.get("user_id") or "").strip()
            self._nome_exibicao = (nome_exibicao_atual or "").strip() or str(dados.get("nome_exibicao") or "").strip()
            self._id_atividade = int(dados.get("id_atividade") or 0)
            self._titulo_atividade = str(dados.get("titulo_atividade") or "").strip()

            self._segundos_trabalhando_float = float(dados.get("segundos_trabalhando") or 0.0)
            self._segundos_ocioso_float = float(dados.get("segundos_ocioso") or 0.0)
            self._segundos_pausado_float = float(dados.get("segundos_pausado") or 0.0)

            self._sessao_carregada = True
            self._rodando = False
            self._situacao_manual = "pausado"
            self._situacao_calculada = "pausado"

            self._nome_app_foco = "desconhecido"
            self._titulo_janela_foco = ""
            self._id_foco_aberto = None
            self._segundos_em_foco_atual = 0
            self._mono_ultimo_acumulo_foco = 0.0
            self._mono_ultimo_flush_foco = 0.0

            self._mapa_intervalos_apps = {}
            self._ultimo_scan_apps_mono = 0.0

            agora = time.monotonic()
            self._ultimo_marco_mono = agora
            self._ultimo_heartbeat_mono = agora
            self._ultimo_sync_status_mono = agora
            self._ultimo_upsert_relatorio_mono = agora
            self._ultimo_erro = ""

            self._salvar_estado_local_locked(sessao_em_aberto=True)
            self._atualizar_status_atual_locked()

    def iniciar(self, user_id: str, nome_exibicao: str, id_atividade: int, titulo_atividade: str) -> None:
        LOG_TEC.log("sessao", "iniciar()", {
            "user_id": user_id, "id_atividade": id_atividade, "titulo": titulo_atividade,
        })
        # Fecha registros antigos pendurados antes de abrir novos — evita lixo legado nos gráficos.
        self._sanear_registros_abertos_do_usuario(user_id)
        with self._trava:
            if self._sessao_carregada:
                raise RuntimeError("Já existe uma sessão carregada. Finalize ou retome a atual.")

            self._user_id = (user_id or "").strip()
            self._nome_exibicao = (nome_exibicao or "").strip()
            self._id_atividade = int(id_atividade)
            self._titulo_atividade = (titulo_atividade or "").strip()

            self._segundos_trabalhando_float = 0.0
            self._segundos_ocioso_float = 0.0
            self._segundos_pausado_float = 0.0

            self._sessao_carregada = True
            self._rodando = True
            self._situacao_manual = "rodando"
            self._situacao_calculada = "trabalhando"

            self._token_sessao = uuid.uuid4().hex

            maquina = socket.gethostname()
            sistema = f"{platform.system()} {platform.release()}"

            self._id_sessao = self._banco.executar(
                """
                INSERT INTO cronometro_sessoes
                    (user_id, token_sessao, maquina_nome, sistema, versao_app, iniciado_em, finalizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, NULL)
                """,
                [self._user_id, self._token_sessao, maquina, sistema, VERSAO_APLICACAO, datetime.now()],
            )
            self._referencia_data_sessao = date.today()

            self._mapa_intervalos_apps = {}
            self._ultimo_scan_apps_mono = 0.0

            agora = time.monotonic()
            self._ultimo_marco_mono = agora
            self._ultimo_heartbeat_mono = agora
            self._ultimo_sync_status_mono = agora
            self._ultimo_upsert_relatorio_mono = agora
            self._ultimo_erro = ""

            self._inserir_evento("inicio", "trabalhando", 0)

            nome, titulo = obter_aplicativo_em_foco()
            self._nome_app_foco = nome
            self._titulo_janela_foco = titulo
            self._abrir_foco(nome, titulo)

            self._salvar_estado_local_locked(sessao_em_aberto=True)
            self._atualizar_status_atual_locked()

            self._parar = threading.Event()
            self._thread_loop = threading.Thread(target=self._loop, daemon=True)
            self._thread_loop.start()

        # Fase 2: inicia detector de input sintético em paralelo (fora do lock)
        try:
            self._detector_input.iniciar()
        except Exception as e:
            LOG_TEC.log("detector_input", "falha ao iniciar", {"erro": str(e)})

    def pausar(self) -> None:
        LOG_TEC.log("sessao", "pausar()")
        with self._trava:
            if not self._sessao_carregada:
                return
            if not self._rodando or self._situacao_manual == "pausado":
                return
            # Impedir pausa enquanto estiver ocioso — evita que o editor
            # esconda tempo ocioso reclassificando como "pausado"
            if self._situacao_calculada == "ocioso":
                return

            self._acumular_tempo_ate_agora_locked(time.monotonic())
            self._rodando = False
            self._situacao_manual = "pausado"
            self._situacao_calculada = "pausado"

            try:
                self._fechar_foco()
            except Exception:
                pass

            try:
                self._fechar_todos_intervalos_apps_locked()
            except Exception:
                pass

            self._salvar_estado_local_locked(sessao_em_aberto=True)
            self._atualizar_status_atual_locked()
            _id_snap = self._id_sessao
            _uid_snap = self._user_id

        try:
            self._inserir_evento("pausa", "pausado", 0, _id_snap, _uid_snap)
        except Exception:
            pass

        # Persiste totais parciais imediatamente ao pausar — o painel web passa a enxergar o bloco concluído.
        try:
            self._upsert_relatorio_parcial()
        except Exception:
            pass

    def retomar(self) -> None:
        LOG_TEC.log("sessao", "retomar()")
        with self._trava:
            if not self._sessao_carregada:
                return
            if self._rodando:
                return

            self._rodando = True
            self._situacao_manual = "rodando"
            self._situacao_calculada = "trabalhando"

            agora = time.monotonic()
            self._ultimo_marco_mono = agora
            self._ultimo_heartbeat_mono = agora
            self._ultimo_sync_status_mono = agora

            nome, titulo = obter_aplicativo_em_foco()
            self._nome_app_foco = nome
            self._titulo_janela_foco = titulo

            try:
                self._abrir_foco(nome, titulo)
            except Exception:
                pass

            if not self._thread_loop or not self._thread_loop.is_alive():
                self._parar = threading.Event()
                self._thread_loop = threading.Thread(target=self._loop, daemon=True)
                self._thread_loop.start()

            self._salvar_estado_local_locked(sessao_em_aberto=True)
            self._atualizar_status_atual_locked()
            _id_snap = self._id_sessao
            _uid_snap = self._user_id

        # Fase 2: detector de input sintético foi iniciado em iniciar() e
        # permanece ativo durante toda a vida da app. Snapshot só ocorre no
        # heartbeat que só dispara com _rodando=True, então pausa/retorno
        # não precisa mexer nele.

        try:
            self._inserir_evento("retorno", "trabalhando", 0, _id_snap, _uid_snap)
        except Exception:
            pass

    def pausar_e_preservar_sessao(self) -> None:
        self.pausar()

    # -------------------- Relatório parcial (upsert) --------------------
    def _upsert_relatorio_com_snapshots(
        self,
        id_sessao: int,
        user_id: str,
        id_atividade: int,
        seg_trab_float: float,
        seg_oci_float: float,
        seg_pau_float: float,
        ref_data_fallback: date,
        texto_relatorio: str,
        com_fechamento: bool,
    ) -> None:
        """Grava/atualiza `cronometro_relatorios` por (id_sessao, referencia_data).
        Usa SELECT + UPDATE/INSERT para não depender de UNIQUE KEY (evita ALTER no banco).
        Divide totais por dia quando a sessão cruza meia-noite.
        """
        if id_sessao is None or not user_id:
            return
        try:
            fim_em_agora = datetime.now()
            inicio_em = None
            try:
                linha_sessao = self._banco.consultar_um(
                    "SELECT iniciado_em FROM cronometro_sessoes WHERE id_sessao = %s LIMIT 1",
                    [id_sessao],
                )
                if linha_sessao and linha_sessao.get("iniciado_em"):
                    inicio_em = linha_sessao["iniciado_em"]
            except Exception:
                inicio_em = None
            if not isinstance(inicio_em, datetime):
                inicio_em = datetime.combine(ref_data_fallback, datetime.min.time())

            fatias = dividir_tempos_por_dia(
                inicio_em,
                fim_em_agora,
                converter_segundos_para_inteiro(seg_trab_float),
                converter_segundos_para_inteiro(seg_oci_float),
                converter_segundos_para_inteiro(seg_pau_float),
            )

            texto_efetivo = (texto_relatorio or "").strip() or "Sessão em andamento (parcial)"

            for dia, seg_trab_dia, seg_oci_dia, seg_pau_dia in fatias:
                segundos_total_dia = seg_trab_dia + seg_oci_dia
                existente = None
                try:
                    existente = self._banco.consultar_um(
                        "SELECT id_relatorio FROM cronometro_relatorios WHERE id_sessao = %s AND referencia_data = %s LIMIT 1",
                        [id_sessao, dia],
                    )
                except Exception:
                    existente = None

                if existente and existente.get("id_relatorio"):
                    self._banco.executar(
                        """
                        UPDATE cronometro_relatorios
                           SET id_atividade = %s,
                               relatorio = %s,
                               segundos_total = %s,
                               segundos_trabalhando = %s,
                               segundos_ocioso = %s,
                               segundos_pausado = %s,
                               criado_em = %s
                         WHERE id_relatorio = %s
                        """,
                        [
                            int(id_atividade) if id_atividade else None,
                            texto_efetivo,
                            int(segundos_total_dia),
                            int(seg_trab_dia),
                            int(seg_oci_dia),
                            int(seg_pau_dia),
                            fim_em_agora,
                            int(existente["id_relatorio"]),
                        ],
                    )
                    LOG_TEC.log("relatorio", f"UPDATE dia={dia}", {
                        "id_relatorio": existente["id_relatorio"],
                        "trab": seg_trab_dia, "oci": seg_oci_dia, "pau": seg_pau_dia,
                        "fechamento": com_fechamento,
                    })
                else:
                    self._banco.executar(
                        """
                        INSERT INTO cronometro_relatorios
                            (id_sessao, user_id, id_atividade, relatorio, segundos_total,
                             segundos_trabalhando, segundos_ocioso, segundos_pausado, criado_em, referencia_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            id_sessao,
                            user_id,
                            int(id_atividade) if id_atividade else None,
                            texto_efetivo,
                            int(segundos_total_dia),
                            int(seg_trab_dia),
                            int(seg_oci_dia),
                            int(seg_pau_dia),
                            fim_em_agora,
                            dia,
                        ],
                    )
                    LOG_TEC.log("relatorio", f"INSERT dia={dia}", {
                        "trab": seg_trab_dia, "oci": seg_oci_dia, "pau": seg_pau_dia,
                        "fechamento": com_fechamento,
                    })
        except Exception as erro:
            LOG_TEC.log("relatorio_erro", "upsert falhou", {"erro": str(erro)})

    def _upsert_relatorio_parcial(self) -> None:
        """Wrapper do upsert que coleta snapshots do state atual sob lock e chama o worker fora.
        Atualiza acumuladores com `_acumular_tempo_ate_agora_locked` antes do snapshot.
        """
        with self._trava:
            if self._id_sessao is None or not self._user_id:
                return
            self._acumular_tempo_ate_agora_locked(time.monotonic())
            id_sessao_snap = self._id_sessao
            user_id_snap = self._user_id
            id_ativ_snap = int(self._id_atividade) if self._id_atividade else 0
            seg_trab_snap = self._segundos_trabalhando_float
            seg_oci_snap = self._segundos_ocioso_float
            seg_pau_snap = self._segundos_pausado_float
            ref_data_snap = self._referencia_data_sessao or date.today()

        self._upsert_relatorio_com_snapshots(
            id_sessao_snap, user_id_snap, id_ativ_snap,
            seg_trab_snap, seg_oci_snap, seg_pau_snap,
            ref_data_snap, texto_relatorio="", com_fechamento=False,
        )

    def zerar_sessao(self) -> None:
        """Para o cronômetro, salva relatório da sessão zerada e descarta o estado local."""
        LOG_TEC.log("sessao", "zerar_sessao()")
        with self._trava:
            if not self._sessao_carregada or self._id_sessao is None:
                return

            self._acumular_tempo_ate_agora_locked(time.monotonic())
            self._rodando = False
            self._situacao_manual = "pausado"
            self._situacao_calculada = "pausado"
            self._inicio_sessao_cache = None

            try:
                self._fechar_foco()
            except Exception:
                pass

            try:
                self._fechar_todos_intervalos_apps_locked()
            except Exception:
                pass

            # Capturar snapshots dentro do lock antes de zerar
            _id_snap = self._id_sessao
            _uid_snap = self._user_id
            _id_ativ_snap = self._id_atividade
            _seg_trab_snap = self._segundos_trabalhando_float
            _seg_ocio_snap = self._segundos_ocioso_float
            _seg_paus_snap = self._segundos_pausado_float
            _ref_data_snap = self._referencia_data_sessao or date.today()

            self._sessao_carregada = False
            self._segundos_trabalhando_float = 0.0
            self._segundos_ocioso_float = 0.0
            self._segundos_pausado_float = 0.0
            self._ultimo_marco_mono = 0.0
            self._parar.set()
            self._limpar_estado_local()

        try:
            self._inserir_evento("zerar", "pausado", 0, _id_snap, _uid_snap)
        except Exception as e:
            print(f"[zerar_sessao] Falha ao gravar evento 'zerar': {e}")

        try:
            self._banco.executar(
                "UPDATE cronometro_sessoes SET finalizado_em = %s WHERE id_sessao = %s",
                [datetime.now(), _id_snap],
            )
        except Exception:
            pass

        # Consolida na mesma linha parcial já criada ao longo da sessão (ou insere se não existir).
        # Sessões que cruzam meia-noite continuam sendo divididas em múltiplas linhas por referencia_data.
        try:
            self._upsert_relatorio_com_snapshots(
                _id_snap, _uid_snap, int(_id_ativ_snap) if _id_ativ_snap else 0,
                _seg_trab_snap, _seg_ocio_snap, _seg_paus_snap,
                _ref_data_snap, texto_relatorio="Sessão zerada", com_fechamento=True,
            )
        except Exception:
            pass

        try:
            self._limpar_status_atual()
        except Exception:
            pass

    def finalizar(self, relatorio: str) -> None:
        LOG_TEC.log("sessao", "finalizar()", {"relatorio_tam": len(relatorio or "")})
        with self._trava:
            if not self._sessao_carregada or self._id_sessao is None or not self._user_id:
                raise RuntimeError("Você precisa clicar em INICIAR antes de FINALIZAR.")

            self._acumular_tempo_ate_agora_locked(time.monotonic())
            self._rodando = False
            self._situacao_manual = "pausado"
            self._situacao_calculada = "pausado"
            self._inicio_sessao_cache = None

            try:
                self._fechar_foco()
            except Exception:
                pass

            try:
                self._fechar_todos_intervalos_apps_locked()
            except Exception:
                pass

        try:
            self._inserir_evento("finalizar", "pausado", 0)
        except Exception:
            pass

        try:
            self._banco.executar(
                "UPDATE cronometro_sessoes SET finalizado_em = %s WHERE id_sessao = %s",
                [datetime.now(), self._id_sessao],
            )
        except Exception:
            pass

        # Consolida na mesma linha parcial já criada ao longo da sessão (ou insere se não existir).
        # Sessões que cruzam meia-noite continuam sendo divididas em múltiplas linhas por referencia_data.
        ref_data_fallback = self._referencia_data_sessao or date.today()
        texto_relatorio = (relatorio or "").strip()
        try:
            self._upsert_relatorio_com_snapshots(
                self._id_sessao, self._user_id, int(self._id_atividade),
                self._segundos_trabalhando_float, self._segundos_ocioso_float, self._segundos_pausado_float,
                ref_data_fallback, texto_relatorio=texto_relatorio, com_fechamento=True,
            )
        except Exception:
            pass

        with self._trava:
            self._sessao_carregada = False
            self._parar.set()
            self._limpar_estado_local()

        try:
            self._limpar_status_atual()
        except Exception:
            pass

    def _loop(self) -> None:
        try:
            ultimo_foco = ("", "")

            while not self._parar.is_set():
                time.sleep(INTERVALO_LOOP_SEGUNDOS)
                mono_agora = time.monotonic()

                try:
                    idle = obter_segundos_ocioso_windows()
                    nome_foco, titulo_foco = obter_aplicativo_em_foco()
                except Exception as e:
                    with self._trava:
                        self._registrar_erro_locked(f"Falha foco/idle: {e}")
                    continue

                # Scan de apps visíveis a cada INTERVALO_SCAN_APPS_SEGUNDOS (fora da lock — pode ser lento)
                apps_visiveis_scan: set[str] | None = None
                delta_scan = 0
                if (mono_agora - self._ultimo_scan_apps_mono) >= INTERVALO_SCAN_APPS_SEGUNDOS:
                    try:
                        apps_visiveis_scan = listar_nomes_apps_visiveis()
                    except Exception:
                        apps_visiveis_scan = set()
                    delta_scan = max(1, int(mono_agora - self._ultimo_scan_apps_mono)) if self._ultimo_scan_apps_mono > 0 else int(INTERVALO_SCAN_APPS_SEGUNDOS)
                    self._ultimo_scan_apps_mono = mono_agora

                # Flags para operações de banco — decididas dentro do lock,
                # executadas FORA para não bloquear Pausar/Retomar/Iniciar
                _foco_mudou       = False
                _evt_situacao: tuple | None = None
                _fazer_heartbeat  = False
                _hb_situacao      = ""
                _hb_idle          = 0
                _fazer_flush      = False
                _fazer_status     = False
                _salvar_local     = False
                _fazer_upsert_relatorio = False

                try:
                    with self._trava:
                        if not self._sessao_carregada:
                            continue
                        if not self._rodando:
                            continue

                        # ── Atualização de estado puro (sem banco) ──────────
                        situacao_anterior = self._situacao_calculada
                        nova_situacao = "ocioso" if idle >= LIMITE_OCIOSO_SEGUNDOS else "trabalhando"
                        self._situacao_calculada = nova_situacao
                        self._acumular_tempo_ate_agora_locked(mono_agora)
                        # Acumula segundos do foco atual em memória (UPDATE no banco vai
                        # acontecer fora do lock via _flush_foco_periodico).
                        self._acumular_foco_locked(mono_agora)
                        self._nome_app_foco = nome_foco
                        self._titulo_janela_foco = titulo_foco
                        foco_atual = (nome_foco, titulo_foco)

                        # ── Marcar o que precisa ir ao banco ─────────────────
                        if foco_atual != ultimo_foco:
                            _foco_mudou = True

                        if situacao_anterior != nova_situacao:
                            if situacao_anterior == "trabalhando" and nova_situacao == "ocioso":
                                _evt_situacao = ("ocioso_inicio", "ocioso", idle)
                            elif situacao_anterior == "ocioso" and nova_situacao == "trabalhando":
                                _evt_situacao = ("ocioso_fim", "trabalhando", idle)

                        if (mono_agora - self._ultimo_heartbeat_mono) >= INTERVALO_HEARTBEAT_SEGUNDOS:
                            self._ultimo_heartbeat_mono = mono_agora
                            _fazer_heartbeat = True
                            _fazer_flush     = True
                            _hb_situacao     = self._situacao_calculada
                            _hb_idle         = idle

                        if (mono_agora - self._ultimo_sync_status_mono) >= INTERVALO_STATUS_BANCO_SEGUNDOS:
                            self._ultimo_sync_status_mono = mono_agora
                            _fazer_status = True

                        if (mono_agora - self._ultimo_save_estado_mono) >= 10.0:
                            self._ultimo_save_estado_mono = mono_agora
                            _salvar_local = True

                        if (mono_agora - self._ultimo_upsert_relatorio_mono) >= INTERVALO_UPSERT_RELATORIO_SEGUNDOS:
                            self._ultimo_upsert_relatorio_mono = mono_agora
                            _fazer_upsert_relatorio = True

                except Exception as e:
                    with self._trava:
                        self._registrar_erro_locked(f"Falha loop: {e}")

                # ── Operações de banco FORA do lock ──────────────────────────

                if _salvar_local:
                    try:
                        with self._trava:
                            self._salvar_estado_local_locked(sessao_em_aberto=True)
                    except Exception:
                        pass

                if _foco_mudou:
                    try:
                        self._fechar_foco()
                    except Exception:
                        pass
                    try:
                        self._abrir_foco(nome_foco, titulo_foco)
                    except Exception:
                        pass
                    ultimo_foco = foco_atual
                else:
                    # Foco não mudou — flush periódico do contador cumulativo
                    # mantém segundos_em_foco em dia no banco mesmo sem troca,
                    # de modo que crash/kill não deixe registro com fim_em NULL
                    # e duração correta. Mesmo intervalo do scan de apps (10s).
                    try:
                        self._flush_foco_periodico(mono_agora, INTERVALO_SCAN_APPS_SEGUNDOS)
                    except Exception:
                        pass

                if apps_visiveis_scan is not None:
                    try:
                        self._atualizar_intervalos_apps_locked(apps_visiveis_scan, delta_scan)
                    except Exception as e:
                        with self._trava:
                            self._registrar_erro_locked(f"Falha scan apps: {e}")

                if _evt_situacao:
                    try:
                        self._inserir_evento(*_evt_situacao)
                    except Exception as e:
                        LOG_TEC.log("conexao_erro", f"inserir_evento falhou: {_evt_situacao[0]}", {
                            "operacao": "inserir_evento",
                            "tipo_evento": _evt_situacao[0],
                            "situacao": _evt_situacao[1] if len(_evt_situacao) > 1 else None,
                            "erro": str(e),
                            "offline_antes": self._offline_notificado,
                        })
                        self._adicionar_a_fila_offline(*_evt_situacao)

                if _fazer_flush:
                    try:
                        self._tentar_flush_fila_offline()
                    except Exception as e:
                        LOG_TEC.log("conexao_erro", "flush_fila_offline falhou", {
                            "operacao": "flush_fila_offline",
                            "erro": str(e),
                        })

                if _fazer_heartbeat:
                    try:
                        self._inserir_evento("heartbeat", _hb_situacao, _hb_idle)
                    except Exception as e:
                        LOG_TEC.log("conexao_erro", "heartbeat falhou", {
                            "operacao": "heartbeat",
                            "situacao": _hb_situacao,
                            "idle": _hb_idle,
                            "erro": str(e),
                            "entrou_offline": not self._offline_notificado,
                        })
                        with self._trava:
                            self._registrar_erro_locked(f"Falha heartbeat: {e}")
                            if not self._offline_notificado:
                                self._offline_notificado = True
                                self._notificar_sem_conexao()
                        self._adicionar_a_fila_offline("heartbeat", _hb_situacao, _hb_idle)

                    # Fase 2: flush do detector de input sintético (junto do heartbeat)
                    try:
                        self._flush_input_stats_locked_free()
                    except Exception as e:
                        LOG_TEC.log("detector_input", "flush falhou", {"erro": str(e)})

                if _fazer_status:
                    try:
                        estava_offline = self._offline_notificado
                        self._atualizar_status_atual_locked()
                        with self._trava:
                            if self._offline_notificado:
                                self._offline_notificado = False
                                self._registrar_erro_locked("")
                        if estava_offline:
                            LOG_TEC.log("status_restaurado", "usuarios_status_atual voltou a aceitar upsert", {
                                "operacao": "atualizar_status_atual",
                            })
                    except Exception as e:
                        LOG_TEC.log("conexao_erro", "status_atual falhou", {
                            "operacao": "atualizar_status_atual",
                            "erro": str(e),
                            "entrou_offline": not self._offline_notificado,
                        })
                        with self._trava:
                            self._registrar_erro_locked(f"Falha status atual: {e}")
                            if not self._offline_notificado:
                                self._offline_notificado = True
                                self._notificar_sem_conexao()

                if _fazer_upsert_relatorio:
                    try:
                        self._upsert_relatorio_parcial()
                    except Exception:
                        pass

        finally:
            try:
                self._banco.fechar_conexao_da_thread()
            except Exception:
                pass
