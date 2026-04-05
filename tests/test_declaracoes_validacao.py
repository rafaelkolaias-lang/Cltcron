"""Testes da validacao anti-fraude — declaracoes_dia.py.

Este e o teste mais critico do sistema. A funcao _validar_tempo_contra_monitoramento()
impede que editores declarem mais horas do que realmente trabalharam.
"""
from __future__ import annotations

from datetime import date

import pytest

from declaracoes_dia import RepositorioDeclaracoesDia


@pytest.fixture
def repo(banco_fake):
    """Repositorio com banco fake, estrutura ja garantida."""
    r = RepositorioDeclaracoesDia(banco_fake)
    r._estrutura_garantida = True
    return r


# ============================================================
# obter_segundos_monitorados_do_dia
# ============================================================

class TestSegundosMonitorados:
    def test_retorna_total_do_banco(self, repo, banco_fake):
        banco_fake.configurar_consultar_um({"total": 3600})
        resultado = repo.obter_segundos_monitorados_do_dia("lucas", date(2026, 4, 5), 1)
        assert resultado == 3600

    def test_retorna_zero_quando_nulo(self, repo, banco_fake):
        banco_fake.configurar_consultar_um({"total": None})
        resultado = repo.obter_segundos_monitorados_do_dia("lucas", date(2026, 4, 5), 1)
        assert resultado == 0

    def test_retorna_zero_quando_sem_dados(self, repo, banco_fake):
        banco_fake.configurar_consultar_um(None)
        resultado = repo.obter_segundos_monitorados_do_dia("lucas", date(2026, 4, 5), 1)
        assert resultado == 0


# ============================================================
# obter_segundos_declarados_do_dia
# ============================================================

class TestSegundosDeclarados:
    def test_retorna_total_do_banco(self, repo, banco_fake):
        banco_fake.configurar_consultar_um({"total": 1800})
        resultado = repo.obter_segundos_declarados_do_dia("lucas", date(2026, 4, 5), 1)
        assert resultado == 1800

    def test_retorna_zero_sem_dados(self, repo, banco_fake):
        banco_fake.configurar_consultar_um(None)
        resultado = repo.obter_segundos_declarados_do_dia("lucas", date(2026, 4, 5), 1)
        assert resultado == 0


# ============================================================
# _validar_tempo_contra_monitoramento (CORE ANTI-FRAUDE)
# ============================================================

class TestValidacaoAntiFragude:
    """Testes da funcao mais critica do sistema."""

    def _montar_respostas(self, banco_fake, monitorado: int, ja_declarado: int):
        """Helper: configura o banco pra retornar monitorado e ja_declarado em sequencia."""
        respostas = [{"total": monitorado}, {"total": ja_declarado}]
        self._idx = 0

        def consultar_sequencial(sql, params=None):
            if self._idx < len(respostas):
                ret = respostas[self._idx]
                self._idx += 1
                return ret
            return None

        banco_fake.consultar_um = consultar_sequencial

    def test_declarar_zero_sempre_passa(self, repo, banco_fake):
        """Declarar 0 segundos deve sempre passar."""
        self._montar_respostas(banco_fake, monitorado=0, ja_declarado=0)
        # Nao deve lancar excecao
        repo._validar_tempo_contra_monitoramento("lucas", date(2026, 4, 5), 1, 0)

    def test_declarar_sem_monitoramento_falha(self, repo, banco_fake):
        """Se nao tem tempo monitorado, nao pode declarar."""
        self._montar_respostas(banco_fake, monitorado=0, ja_declarado=0)
        with pytest.raises(RuntimeError, match="Não existe tempo monitorado"):
            repo._validar_tempo_contra_monitoramento("lucas", date(2026, 4, 5), 1, 100)

    def test_declarar_exatamente_monitorado_passa(self, repo, banco_fake):
        """Declarar exatamente o tempo monitorado deve passar."""
        self._montar_respostas(banco_fake, monitorado=3600, ja_declarado=0)
        repo._validar_tempo_contra_monitoramento("lucas", date(2026, 4, 5), 1, 3600)

    def test_declarar_acima_monitorado_falha(self, repo, banco_fake):
        """Declarar mais que o monitorado deve falhar."""
        self._montar_respostas(banco_fake, monitorado=3600, ja_declarado=0)
        with pytest.raises(RuntimeError, match="Você está tentando declarar"):
            repo._validar_tempo_contra_monitoramento("lucas", date(2026, 4, 5), 1, 3601)

    def test_declarar_com_parcial_ja_declarado_no_limite(self, repo, banco_fake):
        """Ja declarou 1800s, tenta mais 1800s com monitorado=3600 — deve passar."""
        self._montar_respostas(banco_fake, monitorado=3600, ja_declarado=1800)
        repo._validar_tempo_contra_monitoramento("lucas", date(2026, 4, 5), 1, 1800)

    def test_declarar_com_parcial_ja_declarado_estoura(self, repo, banco_fake):
        """Ja declarou 1800s, tenta mais 1801s com monitorado=3600 — deve falhar."""
        self._montar_respostas(banco_fake, monitorado=3600, ja_declarado=1800)
        with pytest.raises(RuntimeError, match="Você está tentando declarar"):
            repo._validar_tempo_contra_monitoramento("lucas", date(2026, 4, 5), 1, 1801)

    def test_segundos_adicionais_expande_limite(self, repo, banco_fake):
        """segundos_monitorados_adicionais permite declarar mais."""
        self._montar_respostas(banco_fake, monitorado=100, ja_declarado=0)
        # Sem adicional: 200 > 100 falharia. Com adicional 100: 200 <= 200 passa.
        repo._validar_tempo_contra_monitoramento(
            "lucas", date(2026, 4, 5), 1, 200,
            segundos_monitorados_adicionais=100,
        )

    def test_segundos_negativos_lanca_erro(self, repo, banco_fake):
        """Segundos negativos devem ser rejeitados."""
        self._montar_respostas(banco_fake, monitorado=100, ja_declarado=0)
        with pytest.raises(RuntimeError, match="Tempo"):
            repo._validar_tempo_contra_monitoramento("lucas", date(2026, 4, 5), 1, -10)
