"""Validador de chave Pix — compartilhado conceitualmente com `painel/commands/_comum/pix.php`.

Aceita: CNPJ (14 dígitos com DV válido), celular BR (10 ou 11 dígitos com DDD),
e-mail (formato básico). Recusa explicitamente CPF (mensagem dedicada) e
qualquer outro formato (chave aleatória).

API:
    validar_pix(texto) -> (tipo, valor_normalizado)
        Levanta `ErroPixInvalido` em caso de falha.

Tipos retornados: "cnpj" | "celular" | "email".
"""

from __future__ import annotations

import re

__all__ = ["ErroPixInvalido", "validar_pix", "TIPOS_VALIDOS"]

TIPOS_VALIDOS = ("cnpj", "celular", "email")

_REGEX_EMAIL = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


class ErroPixInvalido(ValueError):
    """Chave Pix inválida — mensagem é exibida para o usuário final."""


def _so_digitos(texto: str) -> str:
    return re.sub(r"\D+", "", texto or "")


def _validar_cnpj(digitos: str) -> bool:
    if len(digitos) != 14 or digitos == digitos[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1
    soma = sum(int(d) * p for d, p in zip(digitos[:12], pesos1, strict=False))
    dv1 = 0 if soma % 11 < 2 else 11 - (soma % 11)
    if dv1 != int(digitos[12]):
        return False
    soma = sum(int(d) * p for d, p in zip(digitos[:13], pesos2, strict=False))
    dv2 = 0 if soma % 11 < 2 else 11 - (soma % 11)
    return dv2 == int(digitos[13])


def _validar_celular_br(digitos: str) -> bool:
    # 10 dígitos = DDD + fixo (8) — aceitamos como "celular" relaxando, comum no Pix
    # 11 dígitos = DDD + 9 + número (padrão atual). DDD 11..99.
    if len(digitos) not in (10, 11):
        return False
    ddd = int(digitos[:2])
    if ddd < 11 or ddd > 99:
        return False
    if len(digitos) == 11 and digitos[2] != "9":
        return False
    return True


def validar_pix(texto: str) -> tuple[str, str]:
    """Valida e normaliza uma chave Pix.

    Retorna `(tipo, valor_normalizado)` onde tipo ∈ {"cnpj","celular","email"}.
    Levanta `ErroPixInvalido` com mensagem amigável em caso de falha.
    """
    bruto = (texto or "").strip()
    if not bruto:
        raise ErroPixInvalido("Informe a chave Pix.")

    # Email — qualquer coisa com @ entra nesse caminho (não normaliza pra dígitos)
    if "@" in bruto:
        valor = bruto.lower()
        if not _REGEX_EMAIL.match(valor):
            raise ErroPixInvalido("E-mail inválido. Verifique o formato (ex: nome@dominio.com).")
        return "email", valor

    # Demais: tudo que sobrar tem que ser número (depois de limpar pontuação).
    digitos = _so_digitos(bruto)
    if not digitos:
        raise ErroPixInvalido("Chave inválida. Use CNPJ, celular ou e-mail.")

    if len(digitos) == 11 and not _validar_celular_br(digitos):
        # 11 dígitos sem padrão de celular válido → muito provável CPF
        raise ErroPixInvalido(
            "CPF não é aceito como chave Pix neste sistema. Use CNPJ, celular ou e-mail."
        )
    if len(digitos) == 11 and _validar_celular_br(digitos):
        return "celular", digitos
    if len(digitos) == 10 and _validar_celular_br(digitos):
        return "celular", digitos
    if len(digitos) == 14:
        if not _validar_cnpj(digitos):
            raise ErroPixInvalido("CNPJ inválido. Confira os dígitos.")
        return "cnpj", digitos

    raise ErroPixInvalido(
        "Chave inválida. Use CNPJ (14 dígitos), celular (10–11 dígitos) ou e-mail."
    )
