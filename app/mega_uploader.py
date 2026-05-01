"""
app/mega_uploader.py — Integração com MEGAcmd para upload automático.

Encapsula tudo que envolve a conta MEGA dedicada do sistema:

  1. `garantir_instalado()` — localiza MEGAcmd; se faltar, baixa e instala
     silenciosamente (instalador NSIS oficial, flag /S, sem console visível).
  2. `garantir_logado()` — busca `mega_email` e `mega_password` na API do
     painel (`credenciais/api/obter.php`), decifra com `APP_CLIENT_DECRYPT_KEY`
     (libsodium secretbox) e roda `mega-login`.
  3. `criar_pasta(remoto)` — `mega-mkdir -p`.
  4. `upload_arquivo(local, remoto, on_progress=None)` — `mega-put`.
  5. `listar(remoto)` — `mega-ls`.

Sem GUI. Pensado pra rodar em background thread (`_executar_em_background`).
Erros viram exceções da hierarquia `ErroMega`. Auto-retry (1x) em sessão
expirada — relogin transparente.

Dependências:
  - `pynacl` (libsodium binding) — único pacote externo novo. Stdlib pro resto.

Pré-requisitos de runtime:
  - `app/segredos.py` populado com `APP_CLIENT_DECRYPT_KEY` (a chave fixa).
  - Modelos `mega_email` e `mega_password` cadastrados na aba Credenciais
    do painel, em modo global (`aplicar_todos=true`), pelo admin.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


# =============================================================
# Exceções
# =============================================================
class ErroMega(Exception):
    """Base de erros do módulo MEGA."""


class ErroInstalacaoMega(ErroMega):
    """Falha ao localizar ou instalar o MEGAcmd."""


class ErroLoginMega(ErroMega):
    """Falha ao autenticar na conta dedicada do MEGA."""


class ErroCredencialFaltando(ErroLoginMega):
    """`mega_email` ou `mega_password` ausentes/revogados no painel."""


class ErroSessaoExpiradaMega(ErroMega):
    """Sessão MEGA caiu — caller deve relogar e tentar de novo."""


class ErroUploadMega(ErroMega):
    """Falha em mkdir/put/ls do MEGA."""


class ErroUploadCancelado(ErroUploadMega):
    """Upload cancelado pelo usuário via cancel_event."""


class ErroPastaMegaInexistente(ErroUploadMega):
    """Pasta lógica do banco não existe (mais) no MEGA — sincronia rompida.
    Geralmente significa que o admin apagou a pasta manualmente no app web."""


# =============================================================
# Constantes
# =============================================================
URL_INSTALADOR_MEGA_64 = "https://mega.nz/MEGAcmdSetup64.exe"
URL_INSTALADOR_MEGA_32 = "https://mega.nz/MEGAcmdSetup.exe"

CAMINHOS_PADRAO_MEGACMD = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "MEGAcmd",                       # user-install (default)
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "MEGAcmd",      # admin-install
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "MEGAcmd",
]

TIMEOUT_INSTALL_SEG = 180.0
TIMEOUT_COMANDO_PADRAO_SEG = 30.0
TIMEOUT_UPLOAD_PADRAO_SEG = 60 * 60.0   # 1h por arquivo (uploads grandes)


# =============================================================
# Subprocess sem console visível (Windows)
# =============================================================
def _flags_sem_console() -> tuple[int, "subprocess.STARTUPINFO | None"]:
    """Retorna `(creationflags, startupinfo)` que escondem qualquer janela."""
    if sys.platform != "win32":
        return 0, None
    flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    si = subprocess.STARTUPINFO()         # type: ignore[attr-defined]
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # type: ignore[attr-defined]
    si.wShowWindow = 0  # SW_HIDE
    return flags, si


def _executar_silencioso(
    comando: list[str],
    *,
    timeout: float = TIMEOUT_COMANDO_PADRAO_SEG,
    cwd: Path | None = None,
    capturar_saida: bool = True,
) -> subprocess.CompletedProcess:
    # IMPORTANTE: NÃO usar `capture_output=True` (PIPE) com MEGAcmd no Windows.
    # `mega-*.bat` invoca `MEGAcmdShell.exe` que pode spawn `MEGAcmdServer.exe`
    # como daemon. O daemon herda os fds dos pipes do PIPE original. Como
    # `subprocess.run` lê os pipes via `Popen.communicate()` que espera todos
    # os escritores fecharem, o read NUNCA termina (server fica vivo segurando
    # o fd). Resultado: trava infinita mesmo após o cmd.exe principal sair.
    # Solução: redirecionar stdout/stderr pra arquivos temporários — daemons
    # podem herdar mas `subprocess.run` retorna quando o processo principal
    # termina, sem esperar os pipes fecharem.
    flags, si = _flags_sem_console()
    if not capturar_saida:
        return subprocess.run(
            comando,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            creationflags=flags,
            startupinfo=si,
            shell=False,
        )

    f_out = tempfile.NamedTemporaryFile(prefix="mega_out_", suffix=".log", delete=False)
    f_err = tempfile.NamedTemporaryFile(prefix="mega_err_", suffix=".log", delete=False)
    out_path, err_path = f_out.name, f_err.name
    f_out.close()
    f_err.close()
    try:
        with open(out_path, "wb") as fo, open(err_path, "wb") as fe:
            try:
                proc = subprocess.run(
                    comando,
                    cwd=str(cwd) if cwd else None,
                    stdout=fo,
                    stderr=fe,
                    timeout=timeout,
                    creationflags=flags,
                    startupinfo=si,
                    shell=False,
                )
            except subprocess.TimeoutExpired as e:
                # Re-empacota com a saída parcial dos arquivos pra debugging
                fo.flush(); fe.flush()
                raise

        with open(out_path, "r", encoding="utf-8", errors="replace") as f:
            stdout = f.read()
        with open(err_path, "r", encoding="utf-8", errors="replace") as f:
            stderr = f.read()
        # subprocess.CompletedProcess permite atribuição direta dos campos
        proc.stdout = stdout
        proc.stderr = stderr
        return proc
    finally:
        # MEGAcmdServer pode estar segurando o handle (daemon herdou) — silenciar
        # PermissionError; o arquivo será limpo na próxima execução do TEMP cleanup.
        for p in (out_path, err_path):
            try:
                os.unlink(p)
            except OSError:
                pass


# =============================================================
# Localização / instalação do MEGAcmd
# =============================================================
def _localizar_megacmd() -> Path | None:
    """Retorna o diretório de instalação do MEGAcmd ou None."""
    for base in CAMINHOS_PADRAO_MEGACMD:
        if base.exists() and (base / "MEGAclient.exe").exists():
            return base
    return None


def _instalar_megacmd_silenciosamente(timeout: float = TIMEOUT_INSTALL_SEG) -> Path:
    """Baixa e roda o instalador oficial. Retorna o diretório instalado."""
    if sys.platform != "win32":
        raise ErroInstalacaoMega("auto-instalação suportada apenas no Windows")

    url = URL_INSTALADOR_MEGA_64
    destino = Path(tempfile.gettempdir()) / "MEGAcmdSetup64.exe"

    logger.info("MEGAcmd não localizado — baixando instalador de %s", url)
    try:
        urllib.request.urlretrieve(url, str(destino))
    except Exception as e:
        # Fallback pra versão 32-bit (URL alternativa)
        try:
            urllib.request.urlretrieve(URL_INSTALADOR_MEGA_32, str(destino))
        except Exception as e2:
            raise ErroInstalacaoMega(
                f"falha ao baixar instalador do MEGAcmd: {e!s} | {e2!s}"
            ) from e2

    if destino.stat().st_size < 1_000_000:
        raise ErroInstalacaoMega(
            f"instalador parece corrompido (tamanho {destino.stat().st_size} bytes)"
        )

    logger.info("Rodando instalador silencioso (/S) — pode levar 1-2 min...")
    try:
        # Flag /S = silent (NSIS). /D=path opcionalmente sobrescreve o destino.
        proc = _executar_silencioso(
            [str(destino), "/S"],
            timeout=timeout,
            capturar_saida=False,
        )
    except subprocess.TimeoutExpired as e:
        raise ErroInstalacaoMega("instalação do MEGAcmd demorou demais") from e

    if proc.returncode != 0:
        raise ErroInstalacaoMega(f"instalador retornou código {proc.returncode}")

    # Pequena pausa: alguns sistemas precisam de tempo pra registrar arquivos.
    time.sleep(2.0)

    diretorio = _localizar_megacmd()
    if diretorio is None:
        raise ErroInstalacaoMega(
            "MEGAcmd instalado mas binário não foi encontrado nos caminhos padrão"
        )

    try:
        destino.unlink(missing_ok=True)
    except Exception:
        pass

    logger.info("MEGAcmd instalado em %s", diretorio)
    return diretorio


# =============================================================
# Cliente HTTP minimalista para o painel
# =============================================================
class ErroPainelHTTP(ErroMega):
    """Falha HTTP/JSON ao falar com o painel."""

    def __init__(self, mensagem: str, codigo_http: int | None = None) -> None:
        super().__init__(mensagem)
        self.codigo_http = codigo_http


def _request_painel(
    url: str,
    headers: dict[str, str],
    *,
    metodo: str = "GET",
    corpo: dict | None = None,
    timeout: float = 15.0,
) -> dict:
    """GET/POST → JSON parseado. Levanta `ErroPainelHTTP` em qualquer falha.

    Mensagens de erro do servidor são propagadas via `ErroPainelHTTP.args[0]`.
    `codigo_http` no atributo facilita decisões do caller (404 ⇒ não existe).
    """
    dados = None
    if corpo is not None:
        dados = json.dumps(corpo).encode("utf-8")
        headers = {**headers, "Content-Type": "application/json"}

    req = urllib.request.Request(url, data=dados, headers=headers, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            corpo_resp = resp.read().decode("utf-8", errors="replace")
            codigo = resp.getcode()
    except urllib.error.HTTPError as e:
        try:
            corpo_erro = e.read().decode("utf-8", errors="replace")
            payload = json.loads(corpo_erro)
            msg = payload.get("mensagem") or f"HTTP {e.code}"
        except Exception:
            msg = f"HTTP {e.code}"
        raise ErroPainelHTTP(f"painel respondeu erro: {msg}", codigo_http=e.code) from e
    except urllib.error.URLError as e:
        raise ErroPainelHTTP(f"falha de rede ao falar com o painel: {e!s}") from e

    try:
        payload = json.loads(corpo_resp)
    except json.JSONDecodeError as e:
        raise ErroPainelHTTP(f"resposta não-JSON do painel: {corpo_resp[:200]}") from e

    if not payload.get("ok"):
        raise ErroPainelHTTP(payload.get("mensagem", "erro desconhecido"), codigo_http=codigo)
    return payload


def _request_painel_get(url: str, headers: dict[str, str], timeout: float = 15.0) -> dict:
    """Mantido por compatibilidade interna (login)."""
    try:
        return _request_painel(url, headers, metodo="GET", timeout=timeout)
    except ErroPainelHTTP as e:
        raise ErroLoginMega(str(e)) from e


def _construir_headers_auth(user_id: str, chave: str) -> dict[str, str]:
    # Apache+PHP-FPM em alguns hosts (incluindo o EasyPanel atual) strippa
    # `Authorization` antes de chegar no PHP — `_auth_cliente.php` então recebe
    # user/chave vazios e responde 401. Mandamos os 3 formatos aceitos pelo
    # `_auth_cliente.php`; o servidor usa o primeiro que estiver presente.
    return {
        "Authorization": f"Bearer {user_id}:{chave}",
        "X-User-Id": user_id,
        "X-User-Chave": chave,
        "Accept": "application/json",
    }


# =============================================================
# Cliente para painel/commands/mega/* (consumido pelo desktop)
# =============================================================
class PainelMegaApi:
    """Cliente HTTP minimalista pros endpoints `commands/mega/desktop_*`.

    Auth: header `Authorization: Bearer <user_id>:<chave>`. Mesma identificação
    usada por `_auth_cliente.php` (módulo Credenciais).
    """

    def __init__(self, url_painel: str, user_id: str, chave_user: str) -> None:
        self.url_painel = url_painel.rstrip("/")
        self.user_id = user_id
        self.chave_user = chave_user

    def _headers(self) -> dict[str, str]:
        return _construir_headers_auth(self.user_id, self.chave_user)

    def obter_config_canal(self, id_atividade: int, timeout: float = 8.0) -> dict:
        """GET desktop_obter_config.php → dict com upload_ativo, pasta_raiz_mega,
        campos_exigidos[], pastas_logicas[].
        """
        url = (
            f"{self.url_painel}/commands/mega/desktop_obter_config.php"
            f"?id_atividade={int(id_atividade)}"
        )
        payload = _request_painel(url, self._headers(), timeout=timeout)
        return payload.get("dados") or {}

    def criar_pasta_logica(
        self, id_atividade: int, numero_video: str, titulo_video: str, timeout: float = 10.0
    ) -> dict:
        """POST desktop_criar_pasta.php → dict com id_pasta_logica, nome_pasta.

        Em caso de duplicidade (HTTP 409), levanta `ErroPainelHTTP` com
        `codigo_http=409` — o caller pode inspecionar.
        """
        url = f"{self.url_painel}/commands/mega/desktop_criar_pasta.php"
        payload = _request_painel(
            url,
            self._headers(),
            metodo="POST",
            corpo={
                "id_atividade": int(id_atividade),
                "numero_video": str(numero_video),
                "titulo_video": str(titulo_video),
            },
            timeout=timeout,
        )
        return payload.get("dados") or {}

    def obter_dados_subtarefa(self, id_subtarefa: int, timeout: float = 8.0) -> dict:
        """GET desktop_obter_dados_subtarefa.php → dict com pasta_raiz_mega,
        pasta_logica, arquivos[], outras_subtarefas_na_pasta. Usado pelo
        desktop antes de excluir uma subtarefa pra saber o que limpar no MEGA.
        """
        url = (
            f"{self.url_painel}/commands/mega/desktop_obter_dados_subtarefa.php"
            f"?id_subtarefa={int(id_subtarefa)}"
        )
        payload = _request_painel(url, self._headers(), timeout=timeout)
        return payload.get("dados") or {}

    def marcar_pasta_logica_inativa(self, id_pasta_logica: int, timeout: float = 8.0) -> dict:
        """POST desktop_marcar_pasta_logica_inativa.php → soft-delete da pasta
        lógica. Idempotente.
        """
        url = f"{self.url_painel}/commands/mega/desktop_marcar_pasta_logica_inativa.php"
        payload = _request_painel(
            url,
            self._headers(),
            metodo="POST",
            corpo={"id_pasta_logica": int(id_pasta_logica)},
            timeout=timeout,
        )
        return payload.get("dados") or {}

    def registrar_upload(
        self,
        *,
        id_pasta_logica: int,
        nome_campo: str,
        nome_arquivo: str,
        status_upload: str = "pendente",
        id_subtarefa: int | None = None,
        tamanho_bytes: int | None = None,
        mensagem_erro: str | None = None,
        id_upload: int = 0,
        timeout: float = 10.0,
    ) -> dict:
        """POST desktop_registrar_upload.php → dict com id_upload, status_upload."""
        url = f"{self.url_painel}/commands/mega/desktop_registrar_upload.php"
        corpo = {
            "id_upload": int(id_upload),
            "id_pasta_logica": int(id_pasta_logica),
            "nome_campo": str(nome_campo),
            "nome_arquivo": str(nome_arquivo),
            "status_upload": str(status_upload),
        }
        if id_subtarefa is not None:
            corpo["id_subtarefa"] = int(id_subtarefa)
        if tamanho_bytes is not None:
            corpo["tamanho_bytes"] = int(tamanho_bytes)
        if mensagem_erro is not None:
            corpo["mensagem_erro"] = str(mensagem_erro)

        payload = _request_painel(url, self._headers(), metodo="POST", corpo=corpo, timeout=timeout)
        return payload.get("dados") or {}


def _decifrar_secretbox(cipher_b64: str, nonce_b64: str, chave_b64: str) -> str:
    """Decifra payload XSalsa20-Poly1305 usado pelo painel."""
    try:
        from nacl.secret import SecretBox  # type: ignore
    except ImportError as e:
        raise ErroLoginMega(
            "biblioteca pynacl ausente — adicionar `pynacl` em requirements.txt"
        ) from e

    try:
        chave = base64.b64decode(chave_b64)
        cipher = base64.b64decode(cipher_b64)
        nonce = base64.b64decode(nonce_b64)
    except Exception as e:
        raise ErroLoginMega(f"base64 inválido nos dados de credencial: {e!s}") from e

    if len(chave) != 32:
        raise ErroLoginMega(
            f"APP_CLIENT_DECRYPT_KEY tem {len(chave)} bytes, esperado 32"
        )
    if len(nonce) != 24:
        raise ErroLoginMega(f"nonce tem {len(nonce)} bytes, esperado 24")

    try:
        return SecretBox(chave).decrypt(cipher, nonce).decode("utf-8")
    except Exception as e:
        raise ErroLoginMega(f"falha ao decifrar credencial (MAC inválido?): {e!s}") from e


# =============================================================
# Classe principal
# =============================================================
class MegaUploader:
    """Encapsula tudo que envolve a conta MEGA dedicada.

    Reuso: instancie uma vez por usuário logado e mantenha viva — login só
    acontece na primeira chamada que precisa de sessão.
    """

    def __init__(
        self,
        url_painel: str,
        user_id: str,
        chave_user: str,
        client_decrypt_key_b64: str,
    ) -> None:
        self.url_painel = url_painel.rstrip("/")
        self.user_id = user_id
        self.chave_user = chave_user
        self.client_key = client_decrypt_key_b64
        self._dir_megacmd: Path | None = None
        self._logado = False

    # ----------------- Helpers internos -----------------
    def _bat(self, nome_comando: str) -> Path:
        """Caminho do .bat wrapper de um comando MEGAcmd."""
        if not self._dir_megacmd:
            raise ErroInstalacaoMega("MEGAcmd ainda não localizado — chame garantir_instalado()")
        return self._dir_megacmd / f"{nome_comando}.bat"

    def _run_mega(
        self,
        nome_comando: str,
        *args: str,
        timeout: float = TIMEOUT_COMANDO_PADRAO_SEG,
    ) -> subprocess.CompletedProcess:
        """Executa `mega-<comando>.bat <args>` silenciosamente."""
        bat = self._bat(nome_comando)
        if not bat.exists():
            raise ErroInstalacaoMega(f"comando não encontrado: {bat}")

        # .bat precisa de cmd.exe — usamos cmd /c, mantendo creationflags pra
        # esconder a janela.
        comando = ["cmd.exe", "/c", str(bat), *args]
        return _executar_silencioso(comando, timeout=timeout)

    def _buscar_segredo(self, identificador: str) -> str:
        """GET /credenciais/api/obter.php?identificador=X → texto puro."""
        url = (
            f"{self.url_painel}/commands/credenciais/api/obter.php"
            f"?identificador={urllib.parse.quote(identificador)}"
        )
        headers = _construir_headers_auth(self.user_id, self.chave_user)
        payload = _request_painel_get(url, headers)
        if not payload.get("ok"):
            msg = payload.get("mensagem", "erro desconhecido")
            if "não preenchida" in msg.lower():
                raise ErroCredencialFaltando(
                    f"credencial '{identificador}' não cadastrada no painel"
                )
            raise ErroLoginMega(f"painel: {msg}")

        dados = payload.get("dados") or {}
        cipher = dados.get("cipher")
        nonce = dados.get("nonce")
        if not cipher or not nonce:
            raise ErroLoginMega(f"resposta do painel sem cipher/nonce: {dados!r}")

        return _decifrar_secretbox(cipher, nonce, self.client_key)

    # ----------------- API pública -----------------
    def garantir_instalado(self) -> Path:
        """Localiza ou instala o MEGAcmd. Retorna o diretório."""
        if self._dir_megacmd and self._dir_megacmd.exists():
            return self._dir_megacmd
        diretorio = _localizar_megacmd()
        if diretorio is None:
            diretorio = _instalar_megacmd_silenciosamente()
        self._dir_megacmd = diretorio
        return diretorio

    def garantir_logado(self) -> bool:
        """Garante que existe sessão ativa no MEGA."""
        self.garantir_instalado()

        # mega-whoami: se logado, retorna o e-mail; senão, mensagem de erro.
        try:
            r = self._run_mega("mega-whoami", timeout=10.0)
            saida = (r.stdout or "") + (r.stderr or "")
            if "@" in saida and r.returncode == 0:
                self._logado = True
                return True
        except subprocess.TimeoutExpired:
            pass  # cai no login

        if not self.client_key:
            raise ErroLoginMega(
                "APP_CLIENT_DECRYPT_KEY vazia — configure app/segredos.py antes de usar"
            )

        email = self._buscar_segredo("mega_email").strip()
        senha = self._buscar_segredo("mega_password").strip()
        if not email or not senha:
            raise ErroCredencialFaltando("mega_email ou mega_password vazios após decifragem")

        # mega-login. Senha no argv NÃO É IDEAL pra produtividade segura, mas
        # MEGAcmd não oferece stdin auth não-interativo. Mitigação:
        #   - argv só visível por outros processos do mesmo usuário Windows;
        #   - flags ocultam janela;
        #   - logger nunca escreve a senha.
        # MEGAcmd 2.5.2+ não emite mais "Login complete" — imprime só o progresso
        # de "Fetching nodes" e termina com rc=0. Critério canônico de sucesso é
        # o exit code: rc=0 (login feito) ou rc=54 ("already logged in").
        r = self._run_mega("mega-login", email, senha, timeout=60.0)
        if r.returncode not in (0, 54):
            saida = (r.stdout or "") + (r.stderr or "")
            saida_limpa = saida.replace(senha, "***")
            raise ErroLoginMega(f"mega-login falhou (rc={r.returncode}): {saida_limpa[:200]}")

        self._logado = True
        return True

    def criar_pasta(self, caminho_remoto: str) -> bool:
        """`mega-mkdir -p <caminho>`. Idempotente."""
        if not caminho_remoto.startswith("/"):
            caminho_remoto = "/" + caminho_remoto
        self.garantir_logado()
        r = self._run_mega("mega-mkdir", "-p", caminho_remoto, timeout=30.0)
        # mkdir -p retorna 0 mesmo se existir; se falhar, propaga.
        if r.returncode != 0:
            saida = (r.stdout or "") + (r.stderr or "")
            if self._eh_sessao_expirada(saida):
                self._logado = False
                self.garantir_logado()
                return self.criar_pasta(caminho_remoto)
            raise ErroUploadMega(f"mkdir falhou: {saida[:200]}")
        return True

    def upload_arquivo(
        self,
        arquivo_local: Path | str,
        pasta_remota: str,
        on_progress: Callable[[float], None] | None = None,
        cancel_event: threading.Event | None = None,
        timeout: float = TIMEOUT_UPLOAD_PADRAO_SEG,
    ) -> bool:
        """`mega-put <local> <pasta_remota>/`. Sobrescreve se já existir.

        - `on_progress(pct)` é chamado de uma thread daemon a cada update do
          MEGAcmd (campo "X.XX %" em stderr). NÃO é thread-safe na UI — o caller
          precisa marshalling (ex: tk `widget.after(0, ...)`).
        - `cancel_event` permite abortar o upload mid-way; quando set, o
          processo é morto via `taskkill /F /T` (mata árvore inteira).
        """
        arquivo = Path(arquivo_local)
        if not arquivo.exists():
            raise ErroUploadMega(f"arquivo local não encontrado: {arquivo}")
        if not pasta_remota.startswith("/"):
            pasta_remota = "/" + pasta_remota
        if not pasta_remota.endswith("/"):
            pasta_remota += "/"

        self.garantir_logado()
        if on_progress:
            try:
                on_progress(0.0)
            except Exception:
                pass

        rc, saida = self._executar_mega_put_streaming(
            arquivo, pasta_remota, on_progress, cancel_event, timeout
        )
        if rc != 0:
            if self._eh_sessao_expirada(saida):
                self._logado = False
                self.garantir_logado()
                return self.upload_arquivo(arquivo, pasta_remota, on_progress, cancel_event, timeout)
            raise ErroUploadMega(f"upload falhou (rc={rc}): {saida[:200]}")

        if on_progress:
            try:
                on_progress(100.0)
            except Exception:
                pass
        return True

    # Regex que pega o "XX.XX %" no progresso do MEGAcmd. Match em stderr:
    #   TRANSFERRING ||########.................||(2/10 MB:  20.00 %)
    _REGEX_PROGRESSO = re.compile(r"\(\s*\d+(?:\.\d+)?/\d+(?:\.\d+)?\s*[KMGT]?B:\s*(\d+(?:\.\d+)?)\s*%\s*\)")

    def _executar_mega_put_streaming(
        self,
        arquivo: Path,
        pasta_remota: str,
        on_progress: Callable[[float], None] | None,
        cancel_event: threading.Event | None,
        timeout: float,
    ) -> tuple[int, str]:
        """Roda `mega-put -c` com Popen, lendo stderr em paralelo pra extrair
        progresso. Retorna `(returncode, stderr_completa)`. Em cancelamento via
        `cancel_event`, mata a árvore com `taskkill /F /T` e levanta
        `ErroUploadCancelado`.
        """
        bat = self._bat("mega-put")
        if not bat.exists():
            raise ErroInstalacaoMega(f"comando não encontrado: {bat}")
        comando = ["cmd.exe", "/c", str(bat), "-c", str(arquivo), pasta_remota]

        flags, si = _flags_sem_console()
        # Arquivo temp pra stderr — ler em paralelo via tail. Evita o bug do
        # PIPE + daemon herdeiro descrito em `_executar_silencioso`.
        f_err = tempfile.NamedTemporaryFile(prefix="mega_put_err_", suffix=".log", delete=False)
        err_path = f_err.name
        f_err.close()

        proc: subprocess.Popen | None = None
        cancelado = False
        try:
            with open(err_path, "wb") as fe:
                proc = subprocess.Popen(
                    comando,
                    stdout=subprocess.DEVNULL,
                    stderr=fe,
                    creationflags=flags,
                    startupinfo=si,
                    shell=False,
                )

            def _tail() -> None:
                """Tail do err_path, parseia progresso e dispara on_progress."""
                ultimo_pct = -1.0
                with open(err_path, "rb") as f:
                    while True:
                        if proc is not None and proc.poll() is not None:
                            # Drena resto e sai
                            resto = f.read().decode("utf-8", errors="replace")
                            self._extrair_e_emitir_progresso(resto, on_progress, ultimo_pct)
                            return
                        bloco = f.read(4096)
                        if not bloco:
                            time.sleep(0.15)
                            continue
                        texto = bloco.decode("utf-8", errors="replace")
                        ultimo_pct = self._extrair_e_emitir_progresso(texto, on_progress, ultimo_pct)

            t_tail = threading.Thread(target=_tail, daemon=True, name="mega-put-tail")
            t_tail.start()

            # Aguarda o processo, polling cancel_event a cada 200ms.
            inicio = time.monotonic()
            while True:
                rc = proc.poll()
                if rc is not None:
                    break
                if cancel_event is not None and cancel_event.is_set():
                    cancelado = True
                    self._matar_arvore(proc.pid)
                    break
                if (time.monotonic() - inicio) > timeout:
                    self._matar_arvore(proc.pid)
                    raise subprocess.TimeoutExpired(comando, timeout)
                time.sleep(0.2)

            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._matar_arvore(proc.pid)
                proc.wait(timeout=2.0)

            t_tail.join(timeout=2.0)

            with open(err_path, "r", encoding="utf-8", errors="replace") as f:
                stderr = f.read()

            if cancelado:
                raise ErroUploadCancelado("upload cancelado pelo usuário")

            return (proc.returncode or 0), stderr
        finally:
            try:
                os.unlink(err_path)
            except OSError:
                pass

    def _extrair_e_emitir_progresso(
        self,
        texto: str,
        on_progress: Callable[[float], None] | None,
        ultimo_pct: float,
    ) -> float:
        """Encontra o último match de progresso no texto e dispara callback se
        mudou (>= 0.5% diferença evita flooding da UI). Retorna o último pct.
        """
        if not on_progress or not texto:
            return ultimo_pct
        ultimo = ultimo_pct
        for m in self._REGEX_PROGRESSO.finditer(texto):
            try:
                pct = float(m.group(1))
            except (TypeError, ValueError):
                continue
            if pct - ultimo >= 0.5 or pct == 100.0:
                try:
                    on_progress(pct)
                except Exception:
                    pass
                ultimo = pct
        return ultimo

    @staticmethod
    def _matar_arvore(pid: int) -> None:
        """Mata o processo e todos os filhos (Windows). `taskkill /F /T` cobre
        cmd.exe → MEGAcmdShell.exe → ... mas NÃO mata o MEGAcmdServer (daemon)
        de propósito — ele continua útil pra próxima sessão."""
        if sys.platform != "win32":
            return
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5.0,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass

    def remover_pasta_recursiva(self, caminho_remoto: str) -> bool:
        """`mega-rm -rf <caminho>`. Apaga a pasta inteira (incluindo arquivos
        dentro). Idempotente: ignora silenciosamente se a pasta não existe.

        Retorna True se removeu, False se a pasta não existia. Erros reais
        propagam como `ErroUploadMega`.
        """
        if not caminho_remoto.startswith("/"):
            caminho_remoto = "/" + caminho_remoto
        # mega-rm não aceita path com '/' final em alguns builds — tira.
        caminho_remoto = caminho_remoto.rstrip("/") or "/"
        self.garantir_logado()
        r = self._run_mega("mega-rm", "-r", "-f", caminho_remoto, timeout=60.0)
        saida = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            return True
        if self._eh_sessao_expirada(saida):
            self._logado = False
            self.garantir_logado()
            return self.remover_pasta_recursiva(caminho_remoto)
        if "not found" in saida.lower() or "no such file" in saida.lower():
            return False
        raise ErroUploadMega(f"rm -r falhou: {saida[:200]}")

    def pasta_existe(self, caminho_remoto: str) -> bool:
        """Retorna True se a pasta remota existe no MEGA. Usado para detectar
        sincronia rompida (admin apagou a pasta manualmente no app web).

        Implementação: roda `mega-ls <caminho>` e classifica:
          - rc=0 → existe.
          - rc!=0 com "not found" / "no such file" → não existe.
          - outros erros → propaga como `ErroUploadMega`.
        """
        if not caminho_remoto.startswith("/"):
            caminho_remoto = "/" + caminho_remoto
        caminho_remoto = caminho_remoto.rstrip("/") or "/"
        self.garantir_logado()
        r = self._run_mega("mega-ls", caminho_remoto, timeout=15.0)
        saida = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            return True
        if self._eh_sessao_expirada(saida):
            self._logado = False
            self.garantir_logado()
            return self.pasta_existe(caminho_remoto)
        if "not found" in saida.lower() or "no such file" in saida.lower():
            return False
        raise ErroUploadMega(f"ls falhou: {saida[:200]}")

    def remover_arquivo(self, caminho_remoto: str) -> bool:
        """`mega-rm <caminho>`. Idempotente: ignora silenciosamente se o
        caminho não existe (caso comum quando o arquivo já foi limpo
        manualmente no MEGA, ou quando estamos sobrescrevendo um upload que
        nunca chegou a concluir).

        Retorna True se removeu, False se o caminho não existia. Erros reais
        (sessão expirada, permissão, etc.) propagam como `ErroUploadMega`.
        """
        if not caminho_remoto.startswith("/"):
            caminho_remoto = "/" + caminho_remoto
        self.garantir_logado()
        r = self._run_mega("mega-rm", "-f", caminho_remoto, timeout=20.0)
        saida = (r.stdout or "") + (r.stderr or "")
        if r.returncode == 0:
            return True
        if self._eh_sessao_expirada(saida):
            self._logado = False
            self.garantir_logado()
            return self.remover_arquivo(caminho_remoto)
        if "not found" in saida.lower() or "no such file" in saida.lower():
            return False
        raise ErroUploadMega(f"rm falhou: {saida[:200]}")

    def listar(self, caminho_remoto: str) -> list[str]:
        """`mega-ls <caminho>` → lista de nomes (não recursivo)."""
        if not caminho_remoto.startswith("/"):
            caminho_remoto = "/" + caminho_remoto
        self.garantir_logado()
        r = self._run_mega("mega-ls", caminho_remoto, timeout=20.0)
        saida = (r.stdout or "") + (r.stderr or "")
        if r.returncode != 0:
            if self._eh_sessao_expirada(saida):
                self._logado = False
                self.garantir_logado()
                return self.listar(caminho_remoto)
            # `mega-ls /pasta_inexistente` retorna != 0 — devolve lista vazia
            # se for "not found", erro real propaga.
            if "not found" in saida.lower() or "no such file" in saida.lower():
                return []
            raise ErroUploadMega(f"ls falhou: {saida[:200]}")
        return [linha.strip() for linha in (r.stdout or "").splitlines() if linha.strip()]

    @staticmethod
    def _eh_sessao_expirada(saida: str) -> bool:
        s = saida.lower()
        return any(t in s for t in ("not logged in", "session expired", "login required"))
