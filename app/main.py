"""Entrypoint do pacote `app/`. Cria a janela e inicia o mainloop."""
from __future__ import annotations

from app.app_shell import App


def main() -> None:
    App().mainloop()


if __name__ == "__main__":
    main()
