from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from banco import BancoDados


def formatar_hhmmss(segundos: int) -> str:
    segundos = max(0, int(segundos or 0))
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segs = segundos % 60
    return f"{horas:02d}:{minutos:02d}:{segs:02d}"


@dataclass
class ItemDeclaracaoDia:
    id_item: int
    id_atividade: int
    titulo_atividade: str
    segundos_declarados: int
    o_que_fez: str
    observacao: str
    id_subtarefa: int | None = None
    canal_entrega: str = ""
    concluida_em: datetime | None = None


@dataclass
class SubtarefaDeclaracaoDia:
    id_subtarefa: int
    id_atividade: int
    titulo_atividade: str
    user_id: str
    referencia_data: date | None
    titulo: str
    canal_entrega: str
    concluida: bool
    segundos_gastos: int
    observacao: str
    concluida_em: datetime | None
    criada_em: datetime | None
    atualizada_em: datetime | None
    bloqueada_pagamento: bool
    id_pagamento: int | None


class RepositorioDeclaracoesDia:
    def __init__(self, banco: BancoDados) -> None:
        self._banco = banco
        self._estrutura_garantida = False

    # ==========================================================
    # Estrutura
    # ==========================================================
    def _garantir_estrutura(self) -> None:
        if self._estrutura_garantida:
            return

        self._criar_tabela_declaracoes_dia_itens()
        self._criar_tabela_subtarefas()
        self._criar_tabela_historico_subtarefas()
        self._garantir_colunas_pagamentos()
        self._garantir_colunas_declaracoes_dia_itens()
        self._garantir_colunas_subtarefas()
        self._garantir_indices()

        self._estrutura_garantida = True

    def _criar_tabela_declaracoes_dia_itens(self) -> None:
        self._banco.executar(
            """
            CREATE TABLE IF NOT EXISTS declaracoes_dia_itens (
              id_item BIGINT NOT NULL AUTO_INCREMENT,
              user_id VARCHAR(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
              referencia_data DATE NOT NULL,
              id_atividade INT NOT NULL,
              id_subtarefa BIGINT NULL,
              segundos_declarados INT NOT NULL DEFAULT 0,
              o_que_fez VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL,
              canal_entrega VARCHAR(180) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
              observacao VARCHAR(600) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
              criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (id_item),
              KEY idx_user_data (user_id, referencia_data),
              KEY idx_atividade (id_atividade),
              KEY idx_subtarefa (id_subtarefa)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

    def _criar_tabela_subtarefas(self) -> None:
        self._banco.executar(
            """
            CREATE TABLE IF NOT EXISTS atividades_subtarefas (
              id_subtarefa BIGINT NOT NULL AUTO_INCREMENT,
              id_atividade INT NOT NULL,
              user_id VARCHAR(60) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
              referencia_data DATE DEFAULT NULL,
              titulo VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL,
              canal_entrega VARCHAR(180) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
              concluida TINYINT(1) NOT NULL DEFAULT 0,
              segundos_gastos INT NOT NULL DEFAULT 0,
              observacao VARCHAR(600) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
              id_sessao BIGINT DEFAULT NULL,
              id_relatorio INT DEFAULT NULL,
              concluida_em DATETIME DEFAULT NULL,
              criada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              atualizada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              bloqueada_pagamento TINYINT(1) NOT NULL DEFAULT 0,
              id_pagamento INT DEFAULT NULL,
              bloqueada_em DATETIME DEFAULT NULL,
              PRIMARY KEY (id_subtarefa),
              KEY idx_subtarefas_user_data_atividade (user_id, referencia_data, id_atividade),
              KEY idx_subtarefas_atividade (id_atividade),
              KEY idx_subtarefas_pagamento (id_pagamento)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

    def _criar_tabela_historico_subtarefas(self) -> None:
        self._banco.executar(
            """
            CREATE TABLE IF NOT EXISTS atividades_subtarefas_historico (
              id_historico BIGINT NOT NULL AUTO_INCREMENT,
              id_subtarefa BIGINT NOT NULL,
              acao VARCHAR(40) COLLATE utf8mb4_unicode_ci NOT NULL,
              user_id_alvo VARCHAR(60) COLLATE utf8mb4_unicode_ci NOT NULL,
              user_id_executor VARCHAR(60) COLLATE utf8mb4_unicode_ci NOT NULL,
              dados_antes LONGTEXT NULL,
              dados_depois LONGTEXT NULL,
              criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (id_historico),
              KEY idx_hist_subtarefa (id_subtarefa),
              KEY idx_hist_user_data (user_id_alvo, criado_em)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

    def _obter_colunas_tabela(self, nome_tabela: str) -> set[str]:
        linhas = self._banco.consultar_todos(
            """
            SELECT COLUMN_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
            """,
            [nome_tabela],
        )
        return {str(linha["COLUMN_NAME"]).strip() for linha in linhas}

    def _garantir_coluna(self, nome_tabela: str, nome_coluna: str, definicao_sql: str) -> None:
        colunas = self._obter_colunas_tabela(nome_tabela)
        if nome_coluna in colunas:
            return
        self._banco.executar(f"ALTER TABLE {nome_tabela} ADD COLUMN {nome_coluna} {definicao_sql}")

    def _indice_existe(self, nome_tabela: str, nome_indice: str) -> bool:
        linha = self._banco.consultar_um(
            """
            SELECT 1
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND INDEX_NAME = %s
            LIMIT 1
            """,
            [nome_tabela, nome_indice],
        )
        return bool(linha)

    def _garantir_indice(self, nome_tabela: str, nome_indice: str, definicao_sql: str) -> None:
        if self._indice_existe(nome_tabela, nome_indice):
            return
        self._banco.executar(f"ALTER TABLE {nome_tabela} ADD INDEX {nome_indice} {definicao_sql}")

    def _garantir_colunas_pagamentos(self) -> None:
        self._garantir_coluna("Pagamentos", "referencia_inicio", "DATE NULL AFTER data_pagamento")
        self._garantir_coluna("Pagamentos", "referencia_fim", "DATE NULL AFTER referencia_inicio")
        self._garantir_coluna("Pagamentos", "travado_ate_data", "DATE NULL AFTER referencia_fim")

    def _garantir_colunas_declaracoes_dia_itens(self) -> None:
        self._garantir_coluna("declaracoes_dia_itens", "id_subtarefa", "BIGINT NULL AFTER id_atividade")
        self._garantir_coluna(
            "declaracoes_dia_itens", "canal_entrega", "VARCHAR(180) NULL AFTER o_que_fez"
        )

    def _garantir_colunas_subtarefas(self) -> None:
        self._garantir_coluna("atividades_subtarefas", "referencia_data", "DATE NULL AFTER user_id")
        self._garantir_coluna("atividades_subtarefas", "canal_entrega", "VARCHAR(180) NULL AFTER titulo")
        self._garantir_coluna("atividades_subtarefas", "segundos_gastos", "INT NOT NULL DEFAULT 0 AFTER concluida")
        self._garantir_coluna("atividades_subtarefas", "observacao", "VARCHAR(600) NULL AFTER segundos_gastos")
        self._garantir_coluna("atividades_subtarefas", "id_sessao", "BIGINT NULL AFTER observacao")
        self._garantir_coluna("atividades_subtarefas", "id_relatorio", "INT NULL AFTER id_sessao")
        self._garantir_coluna(
            "atividades_subtarefas",
            "bloqueada_pagamento",
            "TINYINT(1) NOT NULL DEFAULT 0 AFTER atualizada_em",
        )
        self._garantir_coluna("atividades_subtarefas", "id_pagamento", "INT NULL AFTER bloqueada_pagamento")
        self._garantir_coluna("atividades_subtarefas", "bloqueada_em", "DATETIME NULL AFTER id_pagamento")

    def _garantir_indices(self) -> None:
        self._garantir_indice(
            "atividades_subtarefas",
            "idx_subtarefas_user_data_atividade",
            "(user_id, referencia_data, id_atividade)",
        )
        self._garantir_indice("atividades_subtarefas", "idx_subtarefas_atividade", "(id_atividade)")
        self._garantir_indice("atividades_subtarefas", "idx_subtarefas_pagamento", "(id_pagamento)")
        self._garantir_indice("declaracoes_dia_itens", "idx_subtarefa", "(id_subtarefa)")

    # ==========================================================
    # Conversões
    # ==========================================================
    def _normalizar_user_id(self, user_id: str) -> str:
        return (user_id or "").strip()

    def _normalizar_texto(self, valor: str | None, *, tamanho_maximo: int) -> str:
        texto = (valor or "").strip()
        if len(texto) > tamanho_maximo:
            texto = texto[:tamanho_maximo].strip()
        return texto

    def _normalizar_data(self, valor: date | datetime | str | None) -> date | None:
        if valor is None:
            return None
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, date):
            return valor

        texto = str(valor).strip()
        if not texto:
            return None

        formatos = ("%Y-%m-%d", "%d/%m/%Y")
        for formato in formatos:
            try:
                return datetime.strptime(texto, formato).date()
            except ValueError:
                continue

        raise RuntimeError("Data inválida. Use YYYY-MM-DD ou DD/MM/AAAA.")

    def _normalizar_datetime(self, valor: datetime | str | None) -> datetime | None:
        if valor is None:
            return None
        if isinstance(valor, datetime):
            return valor
        texto = str(valor).strip()
        if not texto:
            return None

        formatos = (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        )
        for formato in formatos:
            try:
                return datetime.strptime(texto, formato)
            except ValueError:
                continue
        return None

    def _serializar_json(self, dados: dict[str, Any] | None) -> str | None:
        if not dados:
            return None
        return json.dumps(dados, ensure_ascii=False, default=str)

    # ==========================================================
    # Validações de cadastro
    # ==========================================================
    def _validar_usuario(self, user_id: str) -> None:
        user_id = self._normalizar_user_id(user_id)
        if not user_id:
            raise RuntimeError("Usuário inválido.")

        usuario = self._banco.consultar_um(
            "SELECT user_id FROM usuarios WHERE user_id = %s LIMIT 1",
            [user_id],
        )
        if not usuario:
            raise RuntimeError("Usuário não existe no cadastro.")

    def _validar_atividade_do_usuario(self, user_id: str, id_atividade: int) -> dict:
        self._validar_usuario(user_id)
        linha = self._banco.consultar_um(
            """
            SELECT
              a.id_atividade,
              a.titulo,
              a.status
            FROM usuarios u
            JOIN atividades_usuarios au ON au.id_usuario = u.id_usuario
            JOIN atividades a ON a.id_atividade = au.id_atividade
            WHERE u.user_id = %s
              AND a.id_atividade = %s
            LIMIT 1
            """,
            [self._normalizar_user_id(user_id), int(id_atividade)],
        )
        if not linha:
            raise RuntimeError("Atividade inválida para este usuário.")
        return linha

    def _validar_titulo_subtarefa(self, titulo: str) -> str:
        titulo_limpo = self._normalizar_texto(titulo, tamanho_maximo=255)
        if not titulo_limpo:
            raise RuntimeError("Informe a subtarefa.")
        return titulo_limpo

    def _validar_segundos(self, segundos: int | str | None) -> int:
        try:
            segundos_int = int(segundos or 0)
        except Exception as erro:
            raise RuntimeError("Tempo inválido para a subtarefa.") from erro
        if segundos_int < 0:
            raise RuntimeError("Tempo inválido para a subtarefa.")
        return segundos_int

    # ==========================================================
    # Pagamento / trava
    # ==========================================================
    def obter_data_travada_por_pagamento(self, user_id: str) -> date | None:
        self._garantir_estrutura()

        user_id = self._normalizar_user_id(user_id)
        if not user_id:
            return None

        linha = self._banco.consultar_um(
            """
            SELECT
                MAX(COALESCE(p.travado_ate_data, p.referencia_fim, p.data_pagamento)) AS travado_ate
            FROM Pagamentos p
            JOIN usuarios u ON u.id_usuario = p.id_usuario
            WHERE u.user_id = %s
            """,
            [user_id],
        )
        return self._normalizar_data(None if not linha else linha.get("travado_ate"))

    def obter_datetime_ultimo_pagamento(self, user_id: str) -> datetime | None:
        """Retorna o criado_em (datetime) do pagamento mais recente do usuário."""
        user_id = self._normalizar_user_id(user_id)
        if not user_id:
            return None
        linha = self._banco.consultar_um(
            """
            SELECT p.criado_em
            FROM Pagamentos p
            JOIN usuarios u ON u.id_usuario = p.id_usuario
            WHERE u.user_id = %s
            ORDER BY p.criado_em DESC
            LIMIT 1
            """,
            [user_id],
        )
        if not linha or not linha.get("criado_em"):
            return None
        val = linha["criado_em"]
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val)
            except (ValueError, TypeError):
                return None
        return None

    def _obter_pagamento_que_trava_data(self, user_id: str, referencia_data: date) -> dict | None:
        return self._banco.consultar_um(
            """
            SELECT
              p.id_pagamento,
              COALESCE(p.travado_ate_data, p.referencia_fim, p.data_pagamento) AS travado_ate
            FROM Pagamentos p
            JOIN usuarios u ON u.id_usuario = p.id_usuario
            WHERE u.user_id = %s
              AND COALESCE(p.travado_ate_data, p.referencia_fim, p.data_pagamento) >= %s
            ORDER BY COALESCE(p.travado_ate_data, p.referencia_fim, p.data_pagamento) ASC,
                     p.id_pagamento ASC
            LIMIT 1
            """,
            [self._normalizar_user_id(user_id), referencia_data],
        )

    def data_esta_travada(self, user_id: str, referencia_data: date | datetime | str | None) -> bool:
        """Retorna True se a data está ESTRITAMENTE antes do dia da trava.
        Para o dia exato da trava, retorna False — a trava individual é por subtarefa."""
        referencia = self._normalizar_data(referencia_data)
        if referencia is None:
            return False

        travado_ate = self.obter_data_travada_por_pagamento(user_id)
        if travado_ate is None:
            return False

        # Dias anteriores ao dia da trava: totalmente travados
        # Dia exato da trava: livre para novas subtarefas (as antigas já têm bloqueada_pagamento=1)
        return bool(referencia < travado_ate)

    def subtarefa_esta_travada(self, user_id: str, id_subtarefa: int) -> bool:
        """Verifica se uma subtarefa específica está travada (por data anterior OU por flag individual)."""
        linha = self._banco.consultar_um(
            """
            SELECT referencia_data, bloqueada_pagamento
            FROM atividades_subtarefas
            WHERE id_subtarefa = %s AND user_id = %s
            """,
            [int(id_subtarefa), self._normalizar_user_id(user_id)],
        )
        if not linha:
            return False

        # Se a flag individual está marcada, está travada
        if bool(linha.get("bloqueada_pagamento")):
            return True

        # Se a data é estritamente anterior à trava, está travada
        ref = self._normalizar_data(linha.get("referencia_data"))
        if ref is None:
            return False
        return self.data_esta_travada(user_id, ref)

    def _validar_periodo_editavel(self, user_id: str, referencia_data: date | None, id_subtarefa: int | None = None) -> None:
        if referencia_data is None:
            return
        # Se é uma subtarefa existente, verificar trava individual
        if id_subtarefa is not None:
            if self.subtarefa_esta_travada(user_id, id_subtarefa):
                raise RuntimeError(
                    "Esta subtarefa pertence a um período já pago e não pode mais ser alterada."
                )
            return
        # Para criação de novas subtarefas, só trava se a data for estritamente anterior
        if self.data_esta_travada(user_id, referencia_data):
            raise RuntimeError(
                "Esta subtarefa pertence a um período já pago e não pode mais ser alterada."
            )

    def atualizar_bloqueios_por_pagamento(self, user_id: str) -> int:
        self._garantir_estrutura()

        travado_ate = self.obter_data_travada_por_pagamento(user_id)
        if travado_ate is None:
            return 0

        pagamento = self._obter_pagamento_que_trava_data(user_id, travado_ate)
        id_pagamento = None if not pagamento else pagamento.get("id_pagamento")
        dt_pagamento = self.obter_datetime_ultimo_pagamento(user_id)

        # Dias estritamente anteriores: trava tudo
        self._banco.executar(
            """
            UPDATE atividades_subtarefas
            SET bloqueada_pagamento = 1,
                id_pagamento = COALESCE(%s, id_pagamento),
                bloqueada_em = COALESCE(bloqueada_em, NOW())
            WHERE user_id = %s
              AND referencia_data IS NOT NULL
              AND referencia_data < %s
              AND bloqueada_pagamento = 0
            """,
            [id_pagamento, self._normalizar_user_id(user_id), travado_ate],
        )

        # Dia exato da trava: só subtarefas criadas ANTES do horário do pagamento
        if dt_pagamento:
            self._banco.executar(
                """
                UPDATE atividades_subtarefas
                SET bloqueada_pagamento = 1,
                    id_pagamento = COALESCE(%s, id_pagamento),
                    bloqueada_em = COALESCE(bloqueada_em, NOW())
                WHERE user_id = %s
                  AND referencia_data = %s
                  AND criada_em <= %s
                  AND bloqueada_pagamento = 0
                """,
                [id_pagamento, self._normalizar_user_id(user_id), travado_ate, dt_pagamento],
            )

        linha = self._banco.consultar_um("SELECT ROW_COUNT() AS total")
        return int((linha or {}).get("total") or 0)

    # ==========================================================
    # Monitoramento / tempo
    # ==========================================================
    def obter_segundos_monitorados_do_dia(
        self,
        user_id: str,
        referencia_data: date | None = None,
        id_atividade: int = 0,
    ) -> int:
        self._garantir_estrutura()

        try:
            sql = """
                SELECT COALESCE(SUM(segundos_trabalhando), 0) AS total
                FROM cronometro_relatorios
                WHERE user_id = %s
                  AND id_atividade = %s
            """
            parametros: list[Any] = [self._normalizar_user_id(user_id), int(id_atividade)]
            if referencia_data is not None:
                sql += " AND DATE(criado_em) = %s"
                parametros.append(referencia_data)

            linha = self._banco.consultar_um(sql, parametros)
            return int((linha or {}).get("total") or 0)
        except Exception:
            return 0

    def obter_segundos_declarados_do_dia(
        self,
        user_id: str,
        referencia_data: date | None = None,
        id_atividade: int = 0,
        *,
        id_subtarefa_ignorar: int | None = None,
    ) -> int:
        self._garantir_estrutura()

        sql = """
            SELECT COALESCE(SUM(segundos_gastos), 0) AS total
            FROM atividades_subtarefas
            WHERE user_id = %s
              AND id_atividade = %s
              AND concluida = 1
        """
        parametros: list[Any] = [self._normalizar_user_id(user_id), int(id_atividade)]
        if referencia_data is not None:
            sql += " AND referencia_data = %s"
            parametros.append(referencia_data)
        if id_subtarefa_ignorar is not None:
            sql += " AND id_subtarefa <> %s"
            parametros.append(int(id_subtarefa_ignorar))

        linha = self._banco.consultar_um(sql, parametros)
        return int((linha or {}).get("total") or 0)

    def _validar_tempo_contra_monitoramento(
        self,
        user_id: str,
        referencia_data: date,
        id_atividade: int,
        segundos_novos: int,
        *,
        id_subtarefa_ignorar: int | None = None,
        segundos_monitorados_adicionais: int = 0,
    ) -> None:
        segundos_novos = self._validar_segundos(segundos_novos)
        monitorado = self.obter_segundos_monitorados_do_dia(user_id, referencia_data, id_atividade)
        monitorado += max(0, int(segundos_monitorados_adicionais or 0))
        if monitorado <= 0 and segundos_novos > 0:
            raise RuntimeError(
                "Não existe tempo monitorado no cronômetro para esta atividade nesta data."
            )

        ja_declarado = self.obter_segundos_declarados_do_dia(
            user_id,
            referencia_data,
            id_atividade,
            id_subtarefa_ignorar=id_subtarefa_ignorar,
        )
        total_resultante = ja_declarado + segundos_novos
        if total_resultante > monitorado:
            raise RuntimeError(
                f"Você está tentando declarar {formatar_hhmmss(total_resultante)}, mas o cronômetro possui {formatar_hhmmss(monitorado)} nesta atividade/data."
            )

    # ==========================================================
    # Histórico
    # ==========================================================
    def _registrar_historico_subtarefa(
        self,
        *,
        id_subtarefa: int,
        acao: str,
        user_id_alvo: str,
        user_id_executor: str,
        dados_antes: dict[str, Any] | None,
        dados_depois: dict[str, Any] | None,
    ) -> None:
        self._banco.executar(
            """
            INSERT INTO atividades_subtarefas_historico (
              id_subtarefa,
              acao,
              user_id_alvo,
              user_id_executor,
              dados_antes,
              dados_depois
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [
                int(id_subtarefa),
                self._normalizar_texto(acao, tamanho_maximo=40),
                self._normalizar_user_id(user_id_alvo),
                self._normalizar_user_id(user_id_executor),
                self._serializar_json(dados_antes),
                self._serializar_json(dados_depois),
            ],
        )

    # ==========================================================
    # Subtarefas
    # ==========================================================
    def _obter_subtarefa(self, user_id: str, id_subtarefa: int) -> dict:
        self._garantir_estrutura()

        linha = self._banco.consultar_um(
            """
            SELECT
              s.id_subtarefa,
              s.id_atividade,
              s.user_id,
              s.referencia_data,
              s.titulo,
              COALESCE(s.canal_entrega, '') AS canal_entrega,
              s.concluida,
              s.segundos_gastos,
              COALESCE(s.observacao, '') AS observacao,
              s.id_sessao,
              s.id_relatorio,
              s.concluida_em,
              s.criada_em,
              s.atualizada_em,
              s.bloqueada_pagamento,
              s.id_pagamento,
              s.bloqueada_em,
              a.titulo AS titulo_atividade
            FROM atividades_subtarefas s
            JOIN atividades a ON a.id_atividade = s.id_atividade
            WHERE s.id_subtarefa = %s
              AND s.user_id = %s
            LIMIT 1
            """,
            [int(id_subtarefa), self._normalizar_user_id(user_id)],
        )
        if not linha:
            raise RuntimeError("Subtarefa não encontrada para este usuário.")
        return linha

    def _mapear_subtarefa(self, linha: dict) -> SubtarefaDeclaracaoDia:
        return SubtarefaDeclaracaoDia(
            id_subtarefa=int(linha["id_subtarefa"]),
            id_atividade=int(linha["id_atividade"]),
            titulo_atividade=str(linha.get("titulo_atividade") or ""),
            user_id=str(linha.get("user_id") or ""),
            referencia_data=self._normalizar_data(linha.get("referencia_data")),
            titulo=str(linha.get("titulo") or ""),
            canal_entrega=str(linha.get("canal_entrega") or ""),
            concluida=bool(int(linha.get("concluida") or 0)),
            segundos_gastos=int(linha.get("segundos_gastos") or 0),
            observacao=str(linha.get("observacao") or ""),
            concluida_em=self._normalizar_datetime(linha.get("concluida_em")),
            criada_em=self._normalizar_datetime(linha.get("criada_em")),
            atualizada_em=self._normalizar_datetime(linha.get("atualizada_em")),
            bloqueada_pagamento=bool(int(linha.get("bloqueada_pagamento") or 0)),
            id_pagamento=(int(linha["id_pagamento"]) if linha.get("id_pagamento") is not None else None),
        )

    def listar_subtarefas_do_dia(
        self,
        user_id: str,
        referencia_data: date | None = None,
        id_atividade: int = 0,
    ) -> list[SubtarefaDeclaracaoDia]:
        self._garantir_estrutura()
        self._validar_atividade_do_usuario(user_id, int(id_atividade))

        condicoes = ["s.user_id = %s", "s.id_atividade = %s"]
        params: list = [self._normalizar_user_id(user_id), int(id_atividade)]

        if referencia_data is not None:
            condicoes.append("s.referencia_data = %s")
            params.append(referencia_data)

        where = " AND ".join(condicoes)

        linhas = self._banco.consultar_todos(
            f"""
            SELECT
              s.id_subtarefa,
              s.id_atividade,
              s.user_id,
              s.referencia_data,
              s.titulo,
              COALESCE(s.canal_entrega, '') AS canal_entrega,
              s.concluida,
              s.segundos_gastos,
              COALESCE(s.observacao, '') AS observacao,
              s.id_sessao,
              s.id_relatorio,
              s.concluida_em,
              s.criada_em,
              s.atualizada_em,
              s.bloqueada_pagamento,
              s.id_pagamento,
              s.bloqueada_em,
              a.titulo AS titulo_atividade
            FROM atividades_subtarefas s
            JOIN atividades a ON a.id_atividade = s.id_atividade
            WHERE {where}
            ORDER BY s.referencia_data DESC, s.concluida ASC, s.criada_em DESC, s.id_subtarefa DESC
            """,
            params,
        )
        return [self._mapear_subtarefa(linha) for linha in linhas]

    def criar_subtarefa(
        self,
        *,
        user_id: str,
        referencia_data: date | datetime | str | None,
        id_atividade: int,
        titulo: str,
        canal_entrega: str = "",
        observacao: str = "",
    ) -> int:
        self._garantir_estrutura()
        self._validar_atividade_do_usuario(user_id, int(id_atividade))

        referencia = self._normalizar_data(referencia_data)
        if referencia is None:
            referencia = date.today()
        self._validar_periodo_editavel(user_id, referencia)

        titulo_limpo = self._validar_titulo_subtarefa(titulo)
        canal_limpo = self._normalizar_texto(canal_entrega, tamanho_maximo=180) or None
        observacao_limpa = self._normalizar_texto(observacao, tamanho_maximo=600) or None

        id_subtarefa = int(
            self._banco.executar(
                """
                INSERT INTO atividades_subtarefas (
                  id_atividade,
                  user_id,
                  referencia_data,
                  titulo,
                  canal_entrega,
                  concluida,
                  segundos_gastos,
                  observacao
                )
                VALUES (%s, %s, %s, %s, %s, 0, 0, %s)
                """,
                [
                    int(id_atividade),
                    self._normalizar_user_id(user_id),
                    referencia,
                    titulo_limpo,
                    canal_limpo,
                    observacao_limpa,
                ],
            )
            or 0
        )
        if id_subtarefa <= 0:
            raise RuntimeError("Não foi possível criar a subtarefa.")

        self._registrar_historico_subtarefa(
            id_subtarefa=id_subtarefa,
            acao="criacao",
            user_id_alvo=user_id,
            user_id_executor=user_id,
            dados_antes=None,
            dados_depois={
                "id_atividade": int(id_atividade),
                "referencia_data": referencia,
                "titulo": titulo_limpo,
                "canal_entrega": canal_limpo,
                "observacao": observacao_limpa,
            },
        )
        return id_subtarefa

    def atualizar_subtarefa(
        self,
        *,
        user_id: str,
        id_subtarefa: int,
        titulo: str | None = None,
        canal_entrega: str | None = None,
        observacao: str | None = None,
        referencia_data: date | datetime | str | None = None,
        segundos_gastos: int | str | None = None,
        segundos_monitorados_adicionais: int = 0,
    ) -> None:
        self._garantir_estrutura()

        antes = self._obter_subtarefa(user_id, int(id_subtarefa))
        referencia_antiga = self._normalizar_data(antes.get("referencia_data"))
        self._validar_periodo_editavel(user_id, referencia_antiga, id_subtarefa=int(id_subtarefa))

        referencia_nova = referencia_antiga
        if referencia_data is not None:
            referencia_nova = self._normalizar_data(referencia_data)
            if referencia_nova is None:
                raise RuntimeError("Data de referência inválida.")
            self._validar_periodo_editavel(user_id, referencia_nova)

        campos_sql: list[str] = []
        parametros: list[Any] = []

        if titulo is not None:
            campos_sql.append("titulo = %s")
            parametros.append(self._validar_titulo_subtarefa(titulo))

        if canal_entrega is not None:
            campos_sql.append("canal_entrega = %s")
            parametros.append(self._normalizar_texto(canal_entrega, tamanho_maximo=180) or None)

        if observacao is not None:
            campos_sql.append("observacao = %s")
            parametros.append(self._normalizar_texto(observacao, tamanho_maximo=600) or None)

        if referencia_data is not None:
            campos_sql.append("referencia_data = %s")
            parametros.append(referencia_nova)

        if segundos_gastos is not None:
            segundos_int = self._validar_segundos(segundos_gastos)
            if bool(int(antes.get("concluida") or 0)):
                self._validar_tempo_contra_monitoramento(
                    user_id,
                    referencia_nova or date.today(),
                    int(antes["id_atividade"]),
                    segundos_int,
                    id_subtarefa_ignorar=int(id_subtarefa),
                    segundos_monitorados_adicionais=segundos_monitorados_adicionais,
                )
            campos_sql.append("segundos_gastos = %s")
            parametros.append(segundos_int)

        if not campos_sql:
            return

        parametros.append(int(id_subtarefa))
        self._banco.executar(
            f"""
            UPDATE atividades_subtarefas
            SET {', '.join(campos_sql)}
            WHERE id_subtarefa = %s
            """,
            parametros,
        )

        depois = self._obter_subtarefa(user_id, int(id_subtarefa))
        self._registrar_historico_subtarefa(
            id_subtarefa=int(id_subtarefa),
            acao="edicao",
            user_id_alvo=user_id,
            user_id_executor=user_id,
            dados_antes=dict(antes),
            dados_depois=dict(depois),
        )
        self._sincronizar_item_espelho_da_subtarefa(int(id_subtarefa), user_id)

    def concluir_subtarefa(
        self,
        *,
        user_id: str,
        id_subtarefa: int,
        segundos_gastos: int | str,
        referencia_data: date | datetime | str | None = None,
        canal_entrega: str | None = None,
        observacao: str | None = None,
        segundos_monitorados_adicionais: int = 0,
    ) -> None:
        self._garantir_estrutura()

        antes = self._obter_subtarefa(user_id, int(id_subtarefa))
        referencia = self._normalizar_data(referencia_data) or self._normalizar_data(antes.get("referencia_data"))
        if referencia is None:
            referencia = date.today()

        self._validar_periodo_editavel(user_id, referencia, id_subtarefa=int(id_subtarefa))
        self._validar_periodo_editavel(user_id, self._normalizar_data(antes.get("referencia_data")), id_subtarefa=int(id_subtarefa))

        segundos_int = self._validar_segundos(segundos_gastos)

        self._validar_tempo_contra_monitoramento(
            user_id,
            referencia,
            int(antes["id_atividade"]),
            segundos_int,
            id_subtarefa_ignorar=int(id_subtarefa),
            segundos_monitorados_adicionais=segundos_monitorados_adicionais,
        )

        canal_final = (
            self._normalizar_texto(canal_entrega, tamanho_maximo=180) if canal_entrega is not None else None
        )
        observacao_final = (
            self._normalizar_texto(observacao, tamanho_maximo=600) if observacao is not None else None
        )

        self._banco.executar(
            """
            UPDATE atividades_subtarefas
            SET referencia_data = %s,
                concluida = 1,
                segundos_gastos = %s,
                concluida_em = NOW(),
                canal_entrega = COALESCE(%s, canal_entrega),
                observacao = COALESCE(%s, observacao)
            WHERE id_subtarefa = %s
            """,
            [referencia, segundos_int, canal_final, observacao_final, int(id_subtarefa)],
        )

        pagamento = self._obter_pagamento_que_trava_data(user_id, referencia)
        if pagamento:
            # Só marca como paga se a subtarefa foi criada ANTES do pagamento
            dt_pagamento = self.obter_datetime_ultimo_pagamento(user_id)
            subtarefa_info = self._obter_subtarefa(user_id, int(id_subtarefa))
            criada_em = subtarefa_info.get("criada_em") if subtarefa_info else None
            marcar = False  # Não marcar por padrão — só se tiver certeza
            if dt_pagamento and criada_em:
                if isinstance(criada_em, str):
                    try:
                        criada_em = datetime.fromisoformat(criada_em)
                    except (ValueError, TypeError):
                        criada_em = None
                if isinstance(criada_em, datetime):
                    marcar = criada_em <= dt_pagamento  # Só marca se criada ANTES do pagamento
            elif dt_pagamento and not criada_em:
                marcar = False  # Sem data de criação — não pode confirmar, não trava
            if marcar:
                self._banco.executar(
                    """
                    UPDATE atividades_subtarefas
                    SET bloqueada_pagamento = 1,
                        id_pagamento = %s,
                        bloqueada_em = COALESCE(bloqueada_em, NOW())
                    WHERE id_subtarefa = %s
                    """,
                    [pagamento.get("id_pagamento"), int(id_subtarefa)],
                )

        depois = self._obter_subtarefa(user_id, int(id_subtarefa))
        self._registrar_historico_subtarefa(
            id_subtarefa=int(id_subtarefa),
            acao="conclusao",
            user_id_alvo=user_id,
            user_id_executor=user_id,
            dados_antes=dict(antes),
            dados_depois=dict(depois),
        )
        self._sincronizar_item_espelho_da_subtarefa(int(id_subtarefa), user_id)

    def reabrir_subtarefa(self, *, user_id: str, id_subtarefa: int) -> None:
        self._garantir_estrutura()

        antes = self._obter_subtarefa(user_id, int(id_subtarefa))
        referencia = self._normalizar_data(antes.get("referencia_data"))
        self._validar_periodo_editavel(user_id, referencia, id_subtarefa=int(id_subtarefa))

        self._banco.executar(
            """
            UPDATE atividades_subtarefas
            SET concluida = 0,
                segundos_gastos = 0,
                concluida_em = NULL,
                bloqueada_pagamento = 0,
                id_pagamento = NULL,
                bloqueada_em = NULL
            WHERE id_subtarefa = %s
            """,
            [int(id_subtarefa)],
        )

        depois = self._obter_subtarefa(user_id, int(id_subtarefa))
        self._registrar_historico_subtarefa(
            id_subtarefa=int(id_subtarefa),
            acao="reabertura",
            user_id_alvo=user_id,
            user_id_executor=user_id,
            dados_antes=dict(antes),
            dados_depois=dict(depois),
        )
        self._sincronizar_item_espelho_da_subtarefa(int(id_subtarefa), user_id)

    def excluir_subtarefa(self, *, user_id: str, id_subtarefa: int) -> None:
        self._garantir_estrutura()

        antes = self._obter_subtarefa(user_id, int(id_subtarefa))
        referencia = self._normalizar_data(antes.get("referencia_data"))
        self._validar_periodo_editavel(user_id, referencia, id_subtarefa=int(id_subtarefa))

        self._registrar_historico_subtarefa(
            id_subtarefa=int(id_subtarefa),
            acao="exclusao",
            user_id_alvo=user_id,
            user_id_executor=user_id,
            dados_antes=dict(antes),
            dados_depois=None,
        )
        self._banco.executar(
            "DELETE FROM declaracoes_dia_itens WHERE id_subtarefa = %s",
            [int(id_subtarefa)],
        )
        self._banco.executar(
            "DELETE FROM atividades_subtarefas WHERE id_subtarefa = %s",
            [int(id_subtarefa)],
        )

    # ==========================================================
    # Espelho em declaracoes_dia_itens
    # ==========================================================
    def _sincronizar_item_espelho_da_subtarefa(self, id_subtarefa: int, user_id: str) -> None:
        try:
            subtarefa = self._obter_subtarefa(user_id, int(id_subtarefa))
        except Exception:
            self._banco.executar(
                "DELETE FROM declaracoes_dia_itens WHERE id_subtarefa = %s",
                [int(id_subtarefa)],
            )
            return

        concluida = bool(int(subtarefa.get("concluida") or 0))
        referencia = self._normalizar_data(subtarefa.get("referencia_data"))
        segundos = int(subtarefa.get("segundos_gastos") or 0)

        if (not concluida) or referencia is None:
            self._banco.executar(
                "DELETE FROM declaracoes_dia_itens WHERE id_subtarefa = %s",
                [int(id_subtarefa)],
            )
            return

        existente = self._banco.consultar_um(
            "SELECT id_item FROM declaracoes_dia_itens WHERE id_subtarefa = %s LIMIT 1",
            [int(id_subtarefa)],
        )

        parametros_base = [
            self._normalizar_user_id(user_id),
            referencia,
            int(subtarefa["id_atividade"]),
            int(id_subtarefa),
            segundos,
            self._normalizar_texto(str(subtarefa.get("titulo") or ""), tamanho_maximo=255),
            self._normalizar_texto(str(subtarefa.get("canal_entrega") or ""), tamanho_maximo=180) or None,
            self._normalizar_texto(str(subtarefa.get("observacao") or ""), tamanho_maximo=600) or None,
        ]

        if existente:
            self._banco.executar(
                """
                UPDATE declaracoes_dia_itens
                SET user_id = %s,
                    referencia_data = %s,
                    id_atividade = %s,
                    id_subtarefa = %s,
                    segundos_declarados = %s,
                    o_que_fez = %s,
                    canal_entrega = %s,
                    observacao = %s
                WHERE id_item = %s
                """,
                parametros_base + [int(existente["id_item"])],
            )
            return

        self._banco.executar(
            """
            INSERT INTO declaracoes_dia_itens (
              user_id,
              referencia_data,
              id_atividade,
              id_subtarefa,
              segundos_declarados,
              o_que_fez,
              canal_entrega,
              observacao
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            parametros_base,
        )

    # ==========================================================
    # Compatibilidade com tela atual
    # ==========================================================
    def listar_itens_do_dia(
        self,
        user_id: str,
        referencia_data: date,
        id_atividade: int,
    ) -> list[ItemDeclaracaoDia]:
        self._garantir_estrutura()
        self._validar_atividade_do_usuario(user_id, int(id_atividade))

        linhas = self._banco.consultar_todos(
            """
            SELECT
              d.id_item,
              d.id_atividade,
              a.titulo AS titulo_atividade,
              d.id_subtarefa,
              d.segundos_declarados,
              d.o_que_fez,
              COALESCE(d.canal_entrega, '') AS canal_entrega,
              COALESCE(d.observacao, '') AS observacao,
              s.concluida_em
            FROM declaracoes_dia_itens d
            JOIN atividades a ON a.id_atividade = d.id_atividade
            LEFT JOIN atividades_subtarefas s ON s.id_subtarefa = d.id_subtarefa
            WHERE d.user_id = %s
              AND d.referencia_data = %s
              AND d.id_atividade = %s
            ORDER BY d.criado_em ASC, d.id_item ASC
            """,
            [self._normalizar_user_id(user_id), referencia_data, int(id_atividade)],
        )

        saida: list[ItemDeclaracaoDia] = []
        for linha in linhas:
            saida.append(
                ItemDeclaracaoDia(
                    id_item=int(linha["id_item"]),
                    id_atividade=int(linha["id_atividade"]),
                    titulo_atividade=str(linha.get("titulo_atividade") or ""),
                    segundos_declarados=int(linha.get("segundos_declarados") or 0),
                    o_que_fez=str(linha.get("o_que_fez") or ""),
                    observacao=str(linha.get("observacao") or ""),
                    id_subtarefa=(int(linha["id_subtarefa"]) if linha.get("id_subtarefa") is not None else None),
                    canal_entrega=str(linha.get("canal_entrega") or ""),
                    concluida_em=self._normalizar_datetime(linha.get("concluida_em")),
                )
            )
        return saida

    def salvar_itens_do_dia_em_lote(
        self,
        *,
        user_id: str,
        referencia_data: date,
        id_atividade: int,
        itens: list[dict],
        limite_monitorado_segundos: int | None = None,
    ) -> None:
        self._garantir_estrutura()
        self._validar_atividade_do_usuario(user_id, int(id_atividade))
        self._validar_periodo_editavel(user_id, referencia_data)

        itens = itens or []
        if not itens:
            raise RuntimeError("Nenhuma linha preenchida para salvar.")

        soma_segundos = 0
        itens_tratados: list[dict[str, Any]] = []

        for item in itens:
            segundos = self._validar_segundos(item.get("segundos_declarados"))
            titulo = self._validar_titulo_subtarefa(item.get("o_que_fez") or "")
            observacao = self._normalizar_texto(item.get("observacao"), tamanho_maximo=600)
            canal_entrega = self._normalizar_texto(
                item.get("canal_entrega") or item.get("canal") or "", tamanho_maximo=180
            )

            if segundos <= 0:
                raise RuntimeError("Existe uma linha com tempo menor ou igual a zero.")

            soma_segundos += segundos
            itens_tratados.append(
                {
                    "titulo": titulo,
                    "observacao": observacao,
                    "canal_entrega": canal_entrega,
                    "segundos": segundos,
                }
            )

        if limite_monitorado_segundos is not None:
            limite = max(0, int(limite_monitorado_segundos or 0))
            if limite <= 0 and soma_segundos > 0:
                raise RuntimeError(
                    "Não existe tempo monitorado suficiente no cronômetro para salvar estes lançamentos."
                )
            if soma_segundos > limite:
                raise RuntimeError(
                    f"Você declarou {formatar_hhmmss(soma_segundos)}, mas o cronômetro tem {formatar_hhmmss(limite)} hoje."
                )
        else:
            self._validar_tempo_contra_monitoramento(
                user_id,
                referencia_data,
                int(id_atividade),
                soma_segundos,
            )

        for item in itens_tratados:
            id_subtarefa = self.criar_subtarefa(
                user_id=user_id,
                referencia_data=referencia_data,
                id_atividade=int(id_atividade),
                titulo=item["titulo"],
                canal_entrega=item["canal_entrega"],
                observacao=item["observacao"],
            )
            self.concluir_subtarefa(
                user_id=user_id,
                id_subtarefa=id_subtarefa,
                segundos_gastos=item["segundos"],
                referencia_data=referencia_data,
                canal_entrega=item["canal_entrega"],
                observacao=item["observacao"],
            )

    # ==========================================================
    # Resumo para tela
    # ==========================================================
    def obter_resumo_do_dia(
        self,
        user_id: str,
        referencia_data: date | None = None,
        id_atividade: int = 0,
        *,
        segundos_monitorados_adicionais: int = 0,
    ) -> dict[str, Any]:
        self._garantir_estrutura()
        self._validar_atividade_do_usuario(user_id, int(id_atividade))

        monitorado = self.obter_segundos_monitorados_do_dia(user_id, referencia_data, int(id_atividade))
        monitorado += max(0, int(segundos_monitorados_adicionais or 0))
        declarado = self.obter_segundos_declarados_do_dia(user_id, referencia_data, int(id_atividade))
        saldo = max(0, monitorado - declarado)

        sql_contagem = """
            SELECT
              COUNT(*) AS total_subtarefas,
              SUM(CASE WHEN concluida = 1 THEN 1 ELSE 0 END) AS total_concluidas
            FROM atividades_subtarefas
            WHERE user_id = %s
              AND id_atividade = %s
        """
        params_contagem: list[Any] = [self._normalizar_user_id(user_id), int(id_atividade)]
        if referencia_data is not None:
            sql_contagem += " AND referencia_data = %s"
            params_contagem.append(referencia_data)

        linha = self._banco.consultar_um(sql_contagem, params_contagem)

        return {
            "monitorado_segundos": monitorado,
            "monitorado_hhmmss": formatar_hhmmss(monitorado),
            "declarado_segundos": declarado,
            "declarado_hhmmss": formatar_hhmmss(declarado),
            "saldo_segundos": saldo,
            "saldo_hhmmss": formatar_hhmmss(saldo),
            "total_subtarefas": int((linha or {}).get("total_subtarefas") or 0),
            "total_concluidas": int((linha or {}).get("total_concluidas") or 0),
            "periodo_travado": self.data_esta_travada(user_id, referencia_data) if referencia_data else False,
            "travado_ate": self.obter_data_travada_por_pagamento(user_id),
        }

    # ==========================================================
    # Pagamentos
    # ==========================================================
    def listar_pagamentos_do_usuario(self, user_id: str) -> list[dict[str, Any]]:
        """Retorna pagamentos do usuário ordenados por data desc."""
        linhas = self._banco.consultar_todos(
            """
            SELECT
              p.id_pagamento,
              p.data_pagamento,
              p.referencia_inicio,
              p.referencia_fim,
              p.valor,
              p.observacao,
              p.criado_em
            FROM Pagamentos p
            INNER JOIN usuarios u ON u.id_usuario = p.id_usuario
            WHERE u.user_id = %s
            ORDER BY p.data_pagamento DESC, p.id_pagamento DESC
            """,
            [self._normalizar_user_id(user_id)],
        )
        return linhas or []
