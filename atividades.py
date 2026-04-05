from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from banco import BancoDados


class RepositorioAtividades:
    def __init__(self, banco: BancoDados) -> None:
        self._banco = banco
        self._estrutura_garantida = False

    # ==========================================================
    # Infra / estrutura
    # ==========================================================
    def _garantir_estrutura(self) -> None:
        if self._estrutura_garantida:
            return

        self._garantir_colunas_pagamentos()
        self._estrutura_garantida = True

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

        self._banco.executar(
            f"ALTER TABLE {nome_tabela} ADD COLUMN {nome_coluna} {definicao_sql}"
        )

    def _garantir_colunas_pagamentos(self) -> None:
        self._garantir_coluna("Pagamentos", "referencia_inicio", "DATE NULL AFTER data_pagamento")
        self._garantir_coluna("Pagamentos", "referencia_fim", "DATE NULL AFTER referencia_inicio")
        self._garantir_coluna("Pagamentos", "travado_ate_data", "DATE NULL AFTER referencia_fim")

    # ==========================================================
    # Conversões / validações
    # ==========================================================
    def _normalizar_user_id(self, user_id: str) -> str:
        return (user_id or "").strip()

    def _normalizar_texto(self, valor: str, *, tamanho_maximo: int) -> str:
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

        raise ValueError("Data inválida. Use o formato YYYY-MM-DD ou DD/MM/AAAA.")

    def _normalizar_decimal(self, valor: Decimal | float | int | str | None) -> Decimal:
        if valor is None or str(valor).strip() == "":
            return Decimal("0.00")
        try:
            return Decimal(str(valor)).quantize(Decimal("0.01"))
        except Exception as erro:
            raise ValueError("Valor inválido para estimativa/valor monetário.") from erro

    def _validar_titulo_atividade(self, titulo: str) -> str:
        titulo_limpo = self._normalizar_texto(titulo, tamanho_maximo=160)
        if not titulo_limpo:
            raise ValueError("Informe o título da atividade.")
        return titulo_limpo

    def _validar_status_atividade(self, status: str | None) -> str | None:
        if status is None:
            return None
        status_limpo = self._normalizar_texto(status, tamanho_maximo=20)
        permitidos = {"aberta", "em_andamento", "concluida", "cancelada"}
        if status_limpo not in permitidos:
            raise ValueError("Status inválido para a atividade.")
        return status_limpo

    def _validar_dificuldade(self, dificuldade: str | None) -> str | None:
        if dificuldade is None:
            return None
        dificuldade_limpa = self._normalizar_texto(dificuldade, tamanho_maximo=20)
        permitidos = {"facil", "media", "dificil", "critica"}
        if dificuldade_limpa not in permitidos:
            raise ValueError("Dificuldade inválida para a atividade.")
        return dificuldade_limpa

    # ==========================================================
    # Usuário / vínculo
    # ==========================================================
    def _obter_usuario_por_user_id(self, user_id: str) -> dict:
        user_id = self._normalizar_user_id(user_id)
        if not user_id:
            raise ValueError("Usuário inválido.")

        usuario = self._banco.consultar_um(
            """
            SELECT id_usuario, user_id, nome_exibicao, status_conta
            FROM usuarios
            WHERE user_id = %s
            LIMIT 1
            """,
            [user_id],
        )
        if not usuario:
            raise ValueError("Usuário não encontrado.")
        return usuario

    def _obter_atividade_do_usuario(self, user_id: str, id_atividade: int) -> dict:
        user_id = self._normalizar_user_id(user_id)
        id_atividade = int(id_atividade or 0)
        if not user_id or id_atividade <= 0:
            raise ValueError("Atividade inválida.")

        linha = self._banco.consultar_um(
            """
            SELECT
                a.id_atividade,
                a.titulo,
                a.descricao,
                a.dificuldade,
                a.estimativa_horas,
                a.status,
                u.id_usuario,
                u.user_id,
                u.nome_exibicao
            FROM usuarios u
            JOIN atividades_usuarios au ON au.id_usuario = u.id_usuario
            JOIN atividades a ON a.id_atividade = au.id_atividade
            WHERE u.user_id = %s
              AND a.id_atividade = %s
            LIMIT 1
            """,
            [user_id, id_atividade],
        )
        if not linha:
            raise ValueError("Atividade não encontrada para este usuário.")
        return linha

    # ==========================================================
    # Pagamentos / trava
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

        valor = None if not linha else linha.get("travado_ate")
        return self._normalizar_data(valor)

    def data_esta_travada(self, user_id: str, referencia_data: date | datetime | str | None) -> bool:
        referencia = self._normalizar_data(referencia_data)
        if referencia is None:
            return False

        travado_ate = self.obter_data_travada_por_pagamento(user_id)
        if travado_ate is None:
            return False

        return bool(referencia <= travado_ate)

    def registrar_pagamento(
        self,
        user_id: str,
        data_pagamento: date | datetime | str,
        valor: Decimal | float | int | str,
        *,
        observacao: str = "",
        referencia_inicio: date | datetime | str | None = None,
        referencia_fim: date | datetime | str | None = None,
        travado_ate_data: date | datetime | str | None = None,
    ) -> int:
        self._garantir_estrutura()

        usuario = self._obter_usuario_por_user_id(user_id)
        id_usuario = int(usuario["id_usuario"])

        data_pagamento_norm = self._normalizar_data(data_pagamento)
        if data_pagamento_norm is None:
            raise ValueError("Informe a data do pagamento.")

        referencia_inicio_norm = self._normalizar_data(referencia_inicio)
        referencia_fim_norm = self._normalizar_data(referencia_fim)
        travado_ate_norm = self._normalizar_data(travado_ate_data)

        if travado_ate_norm is None:
            travado_ate_norm = referencia_fim_norm or data_pagamento_norm

        observacao_limpa = self._normalizar_texto(observacao, tamanho_maximo=255) or None
        valor_decimal = self._normalizar_decimal(valor)

        return int(
            self._banco.executar(
                """
                INSERT INTO Pagamentos (
                    id_usuario,
                    data_pagamento,
                    referencia_inicio,
                    referencia_fim,
                    travado_ate_data,
                    valor,
                    observacao
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    id_usuario,
                    data_pagamento_norm,
                    referencia_inicio_norm,
                    referencia_fim_norm,
                    travado_ate_norm,
                    valor_decimal,
                    observacao_limpa,
                ],
            )
            or 0
        )

    # ==========================================================
    # Autenticação / listagem
    # ==========================================================
    def autenticar_usuario(self, user_id: str, chave: str) -> dict | None:
        user_id = self._normalizar_user_id(user_id)
        chave = self._normalizar_texto(chave, tamanho_maximo=120)

        if not user_id or not chave:
            return None

        usuario = self._banco.consultar_um(
            """
            SELECT user_id, nome_exibicao
            FROM usuarios
            WHERE user_id = %s
              AND chave = %s
              AND status_conta = 'ativa'
            LIMIT 1
            """,
            [user_id, chave],
        )
        if not usuario:
            return None

        return {
            "user_id": str(usuario["user_id"]),
            "nome_exibicao": str(usuario["nome_exibicao"] or usuario["user_id"]),
        }

    def listar_atividades_do_usuario(self, user_id: str) -> list[dict]:
        self._garantir_estrutura()

        user_id = self._normalizar_user_id(user_id)
        if not user_id:
            return []

        travado_ate = self.obter_data_travada_por_pagamento(user_id)

        linhas = self._banco.consultar_todos(
            """
            SELECT
                a.id_atividade,
                a.titulo,
                a.descricao,
                a.dificuldade,
                a.estimativa_horas,
                a.status,
                a.criado_em,
                a.atualizado_em
            FROM usuarios u
            JOIN atividades_usuarios au ON au.id_usuario = u.id_usuario
            JOIN atividades a ON a.id_atividade = au.id_atividade
            WHERE u.user_id = %s
              AND a.status IN ('aberta', 'em_andamento')
            ORDER BY a.atualizado_em DESC, a.id_atividade DESC
            """,
            [user_id],
        )

        resultado: list[dict] = []
        for linha in linhas:
            item = dict(linha)
            item["travado_ate_pagamento"] = travado_ate
            item["possui_periodo_pago"] = bool(travado_ate is not None)
            resultado.append(item)

        return resultado

    # ==========================================================
    # Cadastro / edição / exclusão de atividade
    # ==========================================================
    def criar_atividade(
        self,
        user_id: str,
        titulo: str,
        *,
        descricao: str = "",
        dificuldade: str = "media",
        estimativa_horas: Decimal | float | int | str = 0,
        status: str = "aberta",
    ) -> int:
        self._garantir_estrutura()

        usuario = self._obter_usuario_por_user_id(user_id)
        id_usuario = int(usuario["id_usuario"])
        if str(usuario.get("status_conta") or "") != "ativa":
            raise ValueError("O usuário precisa estar com a conta ativa para receber atividades.")

        titulo_limpo = self._validar_titulo_atividade(titulo)
        descricao_limpa = self._normalizar_texto(descricao, tamanho_maximo=5000) or None
        dificuldade_limpa = self._validar_dificuldade(dificuldade) or "media"
        status_limpo = self._validar_status_atividade(status) or "aberta"
        estimativa_decimal = self._normalizar_decimal(estimativa_horas)

        id_atividade = int(
            self._banco.executar(
                """
                INSERT INTO atividades (
                    titulo,
                    descricao,
                    dificuldade,
                    estimativa_horas,
                    status
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    titulo_limpo,
                    descricao_limpa,
                    dificuldade_limpa,
                    estimativa_decimal,
                    status_limpo,
                ],
            )
            or 0
        )

        if id_atividade <= 0:
            raise RuntimeError("Não foi possível criar a atividade.")

        self._banco.executar(
            """
            INSERT INTO atividades_usuarios (id_atividade, id_usuario)
            VALUES (%s, %s)
            """,
            [id_atividade, id_usuario],
        )

        return id_atividade

    def atualizar_atividade(
        self,
        user_id: str,
        id_atividade: int,
        *,
        titulo: str | None = None,
        descricao: str | None = None,
        dificuldade: str | None = None,
        estimativa_horas: Decimal | float | int | str | None = None,
        status: str | None = None,
    ) -> None:
        self._garantir_estrutura()

        atividade = self._obter_atividade_do_usuario(user_id, id_atividade)
        self._validar_edicao_atividade(user_id, int(id_atividade))

        campos_sql: list[str] = []
        parametros: list[object] = []

        if titulo is not None:
            campos_sql.append("titulo = %s")
            parametros.append(self._validar_titulo_atividade(titulo))

        if descricao is not None:
            campos_sql.append("descricao = %s")
            parametros.append(self._normalizar_texto(descricao, tamanho_maximo=5000) or None)

        if dificuldade is not None:
            campos_sql.append("dificuldade = %s")
            parametros.append(self._validar_dificuldade(dificuldade) or atividade["dificuldade"])

        if estimativa_horas is not None:
            campos_sql.append("estimativa_horas = %s")
            parametros.append(self._normalizar_decimal(estimativa_horas))

        if status is not None:
            campos_sql.append("status = %s")
            parametros.append(self._validar_status_atividade(status) or atividade["status"])

        if not campos_sql:
            return

        parametros.append(int(id_atividade))
        self._banco.executar(
            f"""
            UPDATE atividades
            SET {', '.join(campos_sql)}
            WHERE id_atividade = %s
            """,
            parametros,
        )

    def excluir_atividade(self, user_id: str, id_atividade: int) -> None:
        self._garantir_estrutura()

        atividade = self._obter_atividade_do_usuario(user_id, id_atividade)
        _ = atividade  # deixa explícito que a validação acima é intencional
        self._validar_exclusao_atividade(user_id, int(id_atividade))

        quantidade_vinculos = self._banco.consultar_um(
            """
            SELECT COUNT(*) AS total
            FROM atividades_usuarios
            WHERE id_atividade = %s
            """,
            [int(id_atividade)],
        )
        total_vinculos = int((quantidade_vinculos or {}).get("total") or 0)

        if self._atividade_tem_movimentacao(int(id_atividade), user_id):
            self._banco.executar(
                """
                UPDATE atividades
                SET status = 'cancelada'
                WHERE id_atividade = %s
                """,
                [int(id_atividade)],
            )
            return

        usuario = self._obter_usuario_por_user_id(user_id)
        id_usuario = int(usuario["id_usuario"])

        self._banco.executar(
            """
            DELETE FROM atividades_usuarios
            WHERE id_atividade = %s
              AND id_usuario = %s
            """,
            [int(id_atividade), id_usuario],
        )

        if total_vinculos <= 1:
            self._banco.executar(
                """
                DELETE FROM atividades
                WHERE id_atividade = %s
                """,
                [int(id_atividade)],
            )

    # ==========================================================
    # Regras de trava
    # ==========================================================
    def _atividade_tem_movimentacao(self, id_atividade: int, user_id: str) -> bool:
        consultas = [
            (
                """
                SELECT 1
                FROM cronometro_relatorios
                WHERE id_atividade = %s
                  AND user_id = %s
                LIMIT 1
                """,
                [int(id_atividade), self._normalizar_user_id(user_id)],
            ),
            (
                """
                SELECT 1
                FROM declaracoes_dia_itens
                WHERE id_atividade = %s
                  AND user_id = %s
                LIMIT 1
                """,
                [int(id_atividade), self._normalizar_user_id(user_id)],
            ),
            (
                """
                SELECT 1
                FROM atividades_subtarefas
                WHERE id_atividade = %s
                  AND user_id = %s
                LIMIT 1
                """,
                [int(id_atividade), self._normalizar_user_id(user_id)],
            ),
        ]

        for sql, parametros in consultas:
            linha = self._banco.consultar_um(sql, parametros)
            if linha:
                return True
        return False

    def _atividade_tem_movimentacao_em_periodo_travado(self, user_id: str, id_atividade: int) -> bool:
        travado_ate = self.obter_data_travada_por_pagamento(user_id)
        if travado_ate is None:
            return False

        user_id_limpo = self._normalizar_user_id(user_id)
        id_atividade_int = int(id_atividade)

        consultas = [
            (
                """
                SELECT 1
                FROM cronometro_relatorios
                WHERE user_id = %s
                  AND id_atividade = %s
                  AND DATE(criado_em) <= %s
                LIMIT 1
                """,
                [user_id_limpo, id_atividade_int, travado_ate],
            ),
            (
                """
                SELECT 1
                FROM declaracoes_dia_itens
                WHERE user_id = %s
                  AND id_atividade = %s
                  AND referencia_data <= %s
                LIMIT 1
                """,
                [user_id_limpo, id_atividade_int, travado_ate],
            ),
            (
                """
                SELECT 1
                FROM atividades_subtarefas
                WHERE user_id = %s
                  AND id_atividade = %s
                  AND DATE(COALESCE(concluida_em, criada_em)) <= %s
                LIMIT 1
                """,
                [user_id_limpo, id_atividade_int, travado_ate],
            ),
        ]

        for sql, parametros in consultas:
            linha = self._banco.consultar_um(sql, parametros)
            if linha:
                return True
        return False

    def _validar_edicao_atividade(self, user_id: str, id_atividade: int) -> None:
        if self._atividade_tem_movimentacao_em_periodo_travado(user_id, id_atividade):
            raise ValueError(
                "Esta atividade possui lançamentos em período já pago e não pode mais ser alterada."
            )

    def _validar_exclusao_atividade(self, user_id: str, id_atividade: int) -> None:
        if self._atividade_tem_movimentacao_em_periodo_travado(user_id, id_atividade):
            raise ValueError(
                "Esta atividade possui lançamentos em período já pago e não pode ser excluída."
            )

    # ==========================================================
    # Apoio para tela / fluxo futuro
    # ==========================================================
    def obter_atividade(self, user_id: str, id_atividade: int) -> dict:
        self._garantir_estrutura()
        return dict(self._obter_atividade_do_usuario(user_id, id_atividade))
