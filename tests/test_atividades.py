"""Testes de atividades.py — normalizacao, validacao, locks de pagamento."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from atividades import RepositorioAtividades


@pytest.fixture
def repo(banco_fake):
    r = RepositorioAtividades(banco_fake)
    r._estrutura_garantida = True
    return r


# ============================================================
# Normalizacao de inputs
# ============================================================

class TestNormalizacao:
    def test_normalizar_user_id_strip(self, repo):
        assert repo._normalizar_user_id("  lucas  ") == "lucas"

    def test_normalizar_user_id_vazio(self, repo):
        assert repo._normalizar_user_id("") == ""

    def test_normalizar_user_id_none(self, repo):
        assert repo._normalizar_user_id(None) == ""

    def test_normalizar_texto_trunca(self, repo):
        assert len(repo._normalizar_texto("a" * 200, tamanho_maximo=50)) == 50

    def test_normalizar_texto_strip(self, repo):
        assert repo._normalizar_texto("  teste  ", tamanho_maximo=100) == "teste"

    def test_normalizar_data_date(self, repo):
        d = date(2026, 4, 5)
        assert repo._normalizar_data(d) == d

    def test_normalizar_data_datetime(self, repo):
        dt = datetime(2026, 4, 5, 14, 30)
        assert repo._normalizar_data(dt) == date(2026, 4, 5)

    def test_normalizar_data_string_iso(self, repo):
        assert repo._normalizar_data("2026-04-05") == date(2026, 4, 5)

    def test_normalizar_data_string_br(self, repo):
        assert repo._normalizar_data("05/04/2026") == date(2026, 4, 5)

    def test_normalizar_data_none(self, repo):
        assert repo._normalizar_data(None) is None

    def test_normalizar_data_invalida(self, repo):
        with pytest.raises(ValueError, match="Data inválida"):
            repo._normalizar_data("nao-e-data")

    def test_normalizar_decimal_inteiro(self, repo):
        assert repo._normalizar_decimal(100) == Decimal("100.00")

    def test_normalizar_decimal_float(self, repo):
        assert repo._normalizar_decimal(25.5) == Decimal("25.50")

    def test_normalizar_decimal_string(self, repo):
        assert repo._normalizar_decimal("49.99") == Decimal("49.99")

    def test_normalizar_decimal_none(self, repo):
        assert repo._normalizar_decimal(None) == Decimal("0.00")

    def test_normalizar_decimal_vazio(self, repo):
        assert repo._normalizar_decimal("") == Decimal("0.00")

    def test_normalizar_decimal_invalido(self, repo):
        with pytest.raises(ValueError, match="Valor inválido"):
            repo._normalizar_decimal("abc")


# ============================================================
# Validacao de campos
# ============================================================

class TestValidacao:
    def test_titulo_atividade_valido(self, repo):
        assert repo._validar_titulo_atividade("Editar video") == "Editar video"

    def test_titulo_atividade_vazio_falha(self, repo):
        with pytest.raises(ValueError, match="Informe o título"):
            repo._validar_titulo_atividade("")

    def test_titulo_atividade_espacos_falha(self, repo):
        with pytest.raises(ValueError, match="Informe o título"):
            repo._validar_titulo_atividade("   ")

    def test_status_valido(self, repo):
        for s in ["aberta", "em_andamento", "concluida", "cancelada"]:
            assert repo._validar_status_atividade(s) == s

    def test_status_invalido(self, repo):
        with pytest.raises(ValueError, match="Status inválido"):
            repo._validar_status_atividade("desconhecido")

    def test_status_none_permitido(self, repo):
        assert repo._validar_status_atividade(None) is None

    def test_dificuldade_valida(self, repo):
        for d in ["facil", "media", "dificil", "critica"]:
            assert repo._validar_dificuldade(d) == d

    def test_dificuldade_invalida(self, repo):
        with pytest.raises(ValueError, match="Dificuldade inválida"):
            repo._validar_dificuldade("impossivel")


# ============================================================
# Lock de pagamento
# ============================================================

class TestLockPagamento:
    def test_data_travada_quando_dentro_periodo(self, repo, banco_fake):
        banco_fake.configurar_consultar_um({"travado_ate": date(2026, 4, 10)})
        assert repo.data_esta_travada("lucas", date(2026, 4, 5)) is True

    def test_data_travada_exatamente_no_limite(self, repo, banco_fake):
        banco_fake.configurar_consultar_um({"travado_ate": date(2026, 4, 5)})
        assert repo.data_esta_travada("lucas", date(2026, 4, 5)) is True

    def test_data_nao_travada_apos_periodo(self, repo, banco_fake):
        banco_fake.configurar_consultar_um({"travado_ate": date(2026, 4, 1)})
        assert repo.data_esta_travada("lucas", date(2026, 4, 5)) is False

    def test_data_nao_travada_sem_pagamento(self, repo, banco_fake):
        banco_fake.configurar_consultar_um({"travado_ate": None})
        assert repo.data_esta_travada("lucas", date(2026, 4, 5)) is False

    def test_data_nao_travada_referencia_none(self, repo, banco_fake):
        assert repo.data_esta_travada("lucas", None) is False
