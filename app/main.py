"""Entrypoint do pacote `app/`. Cria a janela e inicia o mainloop."""
from __future__ import annotations

import sys
from pathlib import Path

from app.app_shell import App


def _limpar_bak_residuais() -> None:
    """Apaga arquivos .bak da pasta do .exe na inicialização.

    O auto-update ([app/app_shell.py] _baixar) renomeia o exe atual pra .bak
    antes do swap. Se sobrar .bak de um update anterior e o `unlink()` falhar
    (AV com handle aberto, lock transitório), o swap aborta silenciosamente e
    o usuário fica preso na versão antiga. Limpar na abertura de cada sessão
    garante que a pasta esteja pronta pro próximo update.

    Só roda quando frozen (.exe) — em modo script não há .bak pra limpar.
    Falhas são silenciosas: deletar .bak é cosmético, não pode quebrar o app.
    """
    if not getattr(sys, "frozen", False):
        return
    try:
        pasta = Path(sys.executable).resolve().parent
        for arquivo in pasta.glob("*.bak"):
            try:
                arquivo.unlink()
            except Exception:
                pass
    except Exception:
        pass


def main() -> None:
    _limpar_bak_residuais()
    App().mainloop()


if __name__ == "__main__":
    main()
