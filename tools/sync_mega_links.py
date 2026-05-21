#!/usr/bin/env python3
"""sync_mega_links.py — Varre pastas do MEGA via MEGAcmd, gera links públicos
com `mega-export` e envia para o banco via API do painel.

Uso:
    python sync_mega_links.py --url URL_PAINEL --user USER_ID --chave CHAVE

Requisitos:
    - MEGAcmd instalado e logado na conta MEGA do sistema.
    - Credenciais de um usuário ativo no painel (user_id + chave).

O script:
    1. Puxa a lista de pastas lógicas ativas (GET pasta_logica_listar_para_sync.php).
    2. Filtra as que ainda não têm link_mega preenchido.
    3. Para cada uma, roda `mega-export -a /<nome_pasta_mega>/<nome_pasta>`.
    4. Captura o link e envia via POST pasta_logica_salvar_link.php.
"""

import argparse
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Contexto SSL que aceita certificado auto-assinado (servidor interno)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


# ──────────────────────────────────────────────────────────
# Localizar MEGAcmd
# ──────────────────────────────────────────────────────────
CAMINHOS_PADRAO_MEGACMD = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "MEGAcmd",
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "MEGAcmd",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "MEGAcmd",
]


def localizar_megacmd() -> Path:
    for d in CAMINHOS_PADRAO_MEGACMD:
        bat = d / "mega-export.bat"
        if bat.exists():
            return d
    print("[ERRO] MEGAcmd nao encontrado. Instale ou verifique o caminho.")
    sys.exit(1)


def run_mega(dir_megacmd: Path, comando: str, *args: str, timeout: float = 30.0) -> str:
    bat = dir_megacmd / f"{comando}.bat"
    cmd_line = subprocess.list2cmdline([str(bat), *args])
    cmd_str = f'cmd.exe /c "{cmd_line}"'

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0

    r = subprocess.run(
        cmd_str,
        capture_output=True,
        text=True,
        timeout=timeout,
        startupinfo=startupinfo,
    )
    return r.stdout.strip()


# ──────────────────────────────────────────────────────────
# API do painel
# ──────────────────────────────────────────────────────────
def api_get(url_base: str, endpoint: str, user_id: str, chave: str) -> list:
    url = f"{url_base}/commands/mega/{endpoint}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {user_id}:{chave}")
    with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
        raw = resp.read().decode("utf-8")
    if not raw.strip():
        print(f"[ERRO] {endpoint}: resposta vazia (URL final: {resp.url})")
        sys.exit(1)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"[ERRO] {endpoint}: resposta nao e JSON. Primeiros 500 chars:")
        print(raw[:500])
        sys.exit(1)
    if not data.get("ok"):
        print(f"[ERRO] {endpoint}: {data.get('mensagem', 'erro desconhecido')}")
        sys.exit(1)
    return data.get("dados", [])


def api_post(url_base: str, endpoint: str, user_id: str, chave: str, corpo: dict) -> dict:
    url = f"{url_base}/commands/mega/{endpoint}"
    payload = json.dumps(corpo).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {user_id}:{chave}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ──────────────────────────────────────────────────────────
# Lógica principal
# ──────────────────────────────────────────────────────────
def extrair_link(saida_export: str) -> str | None:
    """Extrai URL do output do mega-export (formato: 'Exported ... : https://mega.nz/...')."""
    match = re.search(r"https://mega\.nz/\S+", saida_export)
    return match.group(0) if match else None


def main():
    parser = argparse.ArgumentParser(description="Sincroniza links MEGA das pastas logicas.")
    parser.add_argument("--url", required=True, help="URL base do painel (ex: http://76.13.112.108/painel)")
    parser.add_argument("--user", required=True, help="user_id para autenticacao")
    parser.add_argument("--chave", required=True, help="chave do usuario")
    parser.add_argument("--force", action="store_true", help="Regerar links mesmo para pastas que ja possuem link")
    args = parser.parse_args()

    url_base = args.url.rstrip("/")
    print(f"[INFO] Conectando em {url_base}...")

    # 1. Localizar MEGAcmd
    dir_mega = localizar_megacmd()
    print(f"[INFO] MEGAcmd encontrado em: {dir_mega}")

    # 2. Verificar se está logado
    whoami = run_mega(dir_mega, "mega-whoami")
    if "not logged in" in whoami.lower() or not whoami:
        print("[ERRO] MEGAcmd nao esta logado. Faca login primeiro (mega-login).")
        sys.exit(1)
    print(f"[INFO] Logado como: {whoami}")

    # 3. Puxar lista de pastas do painel
    pastas = api_get(url_base, "pasta_logica_listar_para_sync.php", args.user, args.chave)
    print(f"[INFO] {len(pastas)} pastas logicas encontradas no banco.")

    # 4. Filtrar pastas sem link (ou todas se --force)
    if args.force:
        pendentes = pastas
    else:
        pendentes = [p for p in pastas if not p.get("link_mega")]
    print(f"[INFO] {len(pendentes)} pastas para processar.")

    if not pendentes:
        print("[OK] Nenhuma pasta pendente. Tudo sincronizado!")
        return

    # 5. Para cada pasta, gerar link
    ok_count = 0
    erro_count = 0

    for p in pendentes:
        nome_pasta_mega = p.get("nome_pasta_mega", "")
        nome_pasta = p.get("nome_pasta", "")
        id_pasta = p["id_pasta_logica"]

        if not nome_pasta_mega:
            print(f"  [SKIP] #{id_pasta} {nome_pasta} — canal sem pasta raiz configurada")
            continue

        caminho = f"/{nome_pasta_mega}/{nome_pasta}"
        print(f"  [EXPORT] #{id_pasta} {caminho}...", end=" ")

        try:
            saida = run_mega(dir_mega, "mega-export", "-a", caminho, timeout=15.0)
            link = extrair_link(saida)

            if not link:
                print(f"FALHA (saida: {saida[:100]})")
                erro_count += 1
                continue

            # Enviar link pro banco
            resp = api_post(url_base, "pasta_logica_salvar_link.php", args.user, args.chave, {
                "id_pasta_logica": id_pasta,
                "link_mega": link,
            })

            if resp.get("ok"):
                print(f"OK -> {link}")
                ok_count += 1
            else:
                print(f"ERRO API: {resp.get('mensagem', '?')}")
                erro_count += 1

        except subprocess.TimeoutExpired:
            print("TIMEOUT")
            erro_count += 1
        except Exception as e:
            print(f"ERRO: {e}")
            erro_count += 1

    print(f"\n[RESULTADO] {ok_count} links salvos, {erro_count} erros.")


if __name__ == "__main__":
    main()
