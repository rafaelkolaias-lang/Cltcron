"""Configurações globais, constantes e LogTecnico.

Tudo aqui é compartilhado pelos demais módulos do pacote `app/`.
"""
from __future__ import annotations

import json
import sys
import threading
from datetime import datetime
from pathlib import Path

# =========================
# MODO SCRIPT (dev) vs EXE (produção)
# =========================
# MODO_SCRIPT=True quando rodando via `python main.py` (não compilado).
# PyInstaller define sys.frozen=True no .exe final.
MODO_SCRIPT = not getattr(sys, "frozen", False)


class LogTecnico:
    """Log técnico em memória + arquivo. Thread-safe. Usado para depurar o cronômetro em modo script."""

    def __init__(self, caminho_arquivo: Path, max_memoria: int = 2000) -> None:
        self._caminho = caminho_arquivo
        self._max = max_memoria
        self._lock = threading.Lock()
        self._memoria: list[str] = []
        try:
            self._caminho.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def log(self, categoria: str, mensagem: str, detalhes: object = None) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        linha = f"[{ts}] [{categoria:14}] {mensagem}"
        if detalhes is not None:
            try:
                linha += f" :: {json.dumps(detalhes, ensure_ascii=False, default=str)}"
            except Exception:
                linha += f" :: {detalhes}"
        with self._lock:
            self._memoria.append(linha)
            if len(self._memoria) > self._max:
                del self._memoria[: len(self._memoria) - self._max]
            try:
                with open(self._caminho, "a", encoding="utf-8") as f:
                    f.write(linha + "\n")
            except Exception:
                pass

    def linhas(self) -> list[str]:
        with self._lock:
            return list(self._memoria)

    def limpar(self) -> None:
        with self._lock:
            self._memoria.clear()
        try:
            if self._caminho.exists():
                self._caminho.write_text("", encoding="utf-8")
        except Exception:
            pass


ARQUIVO_LOG_TECNICO = Path.home() / ".cronometro_leve_log_tecnico.txt"
LOG_TEC = LogTecnico(ARQUIVO_LOG_TECNICO)


# =========================
# Preferências locais do usuário (persistidas em arquivo simples)
# =========================
ARQUIVO_PREFS = Path.home() / ".cronometro_leve_prefs.json"
_PREFS_DEFAULTS: dict[str, object] = {
    "ocultar_tarefas_pagas": True,
}


def carregar_prefs() -> dict[str, object]:
    """Lê prefs do disco; em qualquer falha retorna defaults. Defaults também
    preenchem chaves novas em arquivos antigos."""
    prefs = dict(_PREFS_DEFAULTS)
    try:
        if ARQUIVO_PREFS.exists():
            data = json.loads(ARQUIVO_PREFS.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                prefs.update(data)
    except Exception:
        pass
    return prefs


def salvar_pref(chave: str, valor: object) -> None:
    """Atualiza uma chave de prefs em disco. Falha silenciosa — pref é
    cosmético, não pode quebrar fluxo principal."""
    try:
        prefs = carregar_prefs()
        prefs[chave] = valor
        ARQUIVO_PREFS.write_text(
            json.dumps(prefs, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


# =========================
# CONFIGURAÇÕES
# =========================
VERSAO_APLICACAO = "v3.1.6"

HISTORICO_VERSOES = [
    {
        "versao": "v3.1.6",
        "data": "13/05/2026",
        "notas": [
            "Auto-update não mostra mais o aviso 'Failed to remove temporary directory' do PyInstaller após atualizar — o novo exe agora abre alguns segundos depois, dando tempo do antigo se desligar limpo",
            "Falhas no swap do auto-update agora são registradas no log técnico em vez de sumirem em silêncio",
        ],
    },
    {
        "versao": "v3.1.5",
        "data": "13/05/2026",
        "notas": [
            "Uploads MEGA grandes não expiram mais por tempo fixo; o envio respeita apenas cancelamento manual",
            "Fluxo MEGA separado em seleção de arquivos e popup de envio em segundo plano, permitindo reenvio apenas dos campos pendentes",
        ],
    },
    {
        "versao": "v3.1.4",
        "data": "06/05/2026",
        "notas": [
            "Fix: era impossível salvar uma tarefa com o mesmo nome em canais diferentes (ex.: '03 - Como iremos para marte' no Sacani e em outro canal) — a validação de duplicidade agora considera o canal de destino",
        ],
    },
    {
        "versao": "v3.1.3",
        "data": "02/05/2026",
        "notas": [
            "Fix: 'Cronometradas' aparecia 00:00:00 no rodapé da janela 'Tarefas da Atividade' — query inválida em Pagamentos era silenciada por except e zerava o totalizador",
            "Cronômetro agora é neutro: você pode declarar suas horas em qualquer atividade onde tenha subtarefa, não importa em qual cronometrou (alinhado com o painel)",
        ],
    },
    {
        "versao": "v3.1.2",
        "data": "02/05/2026",
        "notas": [
            "Checkbox 'Ocultar tarefas pagas' na janela 'Tarefas da Atividade' — habilitado por padrão, esconde subtarefas já travadas por pagamento",
            "Canal sem upload MEGA configurado bloqueia declaração de tarefas novas: aviso vermelho + botão Salvar desativado",
            "Combo CANAL no formulário legado fica readonly: pra trocar de canal, fechar e selecionar pelo menu principal (combo era cosmético — nem mudava o id_atividade salvo)",
            "Campo CANAL movido pro topo do formulário 'Nova Tarefa' legado",
        ],
    },
    {
        "versao": "v3.1.1",
        "data": "01/05/2026",
        "notas": [
            "Botão de debug 'Atualizar MEGA' ao lado do botão 'Atualizar' em Tarefas da Atividade — força a sincronização das pastas MEGA na hora",
        ],
    },
    {
        "versao": "v3.1",
        "data": "01/05/2026",
        "notas": [
            "Configurar chave Pix pelo botão 'Configurar Pix' na janela 'Tarefas da Atividade' — aceita CNPJ, celular ou e-mail",
            "Cronometradas no rodapé agora reseta automaticamente a cada pagamento registrado",
        ],
    },
    {
        "versao": "v3.0",
        "data": "01/05/2026",
        "notas": [
            "Sincronização automática das pastas MEGA com o banco ao iniciar o cronômetro (5 s após Iniciar, em segundo plano, 1× ao dia)",
            "Botão 'Declarar Tarefa' fica como 'SINCRONIZANDO' enquanto a sincronização não termina; janela 'Tarefas da Atividade' mostra status no rodapé",
            "Recuperação automática: tarefas que ficaram pendentes por queda de energia ou fechamento abrupto agora viram tarefas ABERTAS na próxima abertura do app",
            "Fechamento do formulário MEGA com upload em andamento agora pergunta antes de cancelar e preserva o trabalho como tarefa aberta",
            "Auto-update: distribui mais rápido (checagem a cada 2 min, aplica sozinho), pausa a sessão em vez de zerar, toca um som ao reiniciar e tenta auto-login até 3× para cobrir instabilidade de rede",
        ],
    },
    {
        "versao": "v2.9.1",
        "data": "30/04/2026",
        "notas": [
            "Correção: endereço do servidor para a integração de upload do MEGA",
        ],
    },
    {
        "versao": "v2.9",
        "data": "30/04/2026",
        "notas": [
            "Upload de arquivos do vídeo direto pelo formulário de declaração (quando o canal estiver configurado pelo admin)",
            "Pasta lógica do vídeo: criar nova ou selecionar existente com nome padronizado (ex.: \"04 - Video sobre Jupiter\")",
            "Bloqueio de duplicidade: cada pasta lógica é única dentro do canal — se já existe, basta selecionar e complementar com seus arquivos",
            "Conclusão da tarefa só liberada após todos os arquivos obrigatórios subirem com sucesso",
            "Configuração por usuário + canal: cada um vê apenas os campos de upload definidos para ele (editor sobe vídeo, thumbmaker sobe thumb, etc.)",
            "Instalação automática do app de upload MEGA na primeira utilização — zero janela de configuração",
            "Canais sem upload obrigatório configurado seguem com o fluxo antigo (checkbox \"Declaro que subi os arquivos\") sem mudança",
            "Título da tarefa salva passa a ser exatamente o nome da pasta lógica escolhida — facilita encontrar o vídeo depois",
        ],
    },
    {
        "versao": "v2.5",
        "data": "18/04/2026",
        "notas": [
            "Contagem regressiva visual (ex.: jornada de 8h) com pausa automática e alerta obrigatório ao zerar",
            "Janela fixada mostra regressiva e cronômetro juntos; bug de abertura sem tempo corrigido",
            "Totais de trabalhado/ocioso/pausado aparecem no painel web quase em tempo real (atualização a cada 5 min e ao pausar)",
            "Gráficos do painel com Top Apps e barras foco/2.º plano precisos por dia (sem rateio proporcional)",
            "Exclusão automática de trechos ociosos nos gráficos de foco (trabalho líquido)",
            "Status 'TRABALHANDO' muda de cor: verde (online) / amarelo (offline)",
            "Mensagens de sincronização (fila re-enviada) aparecem em verde e somem sozinhas após 10s",
            "Reenvio offline robusto: itens de sessão inválida são descartados sem travar a fila",
            "Saneamento automático de registros pendurados ao iniciar/restaurar sessão",
            "Nome do usuário movido para o título da janela; botões do topo centralizados (Fixar / Regressiva / Sair)",
            "Log técnico detalhado com categorias de conexão (só modo desenvolvedor)",
        ],
    },
    {
        "versao": "v2.4",
        "data": "12/04/2026",
        "notas": [
            "Campo obrigatório Nº do Vídeo ao declarar tarefa",
            "Título salvo no formato: NUMERO - NOME DA TAREFA",
            "Campo aceita apenas números inteiros (zeros à esquerda removidos)",
            "Confirmação obrigatória de upload no Drive antes de salvar",
            "Ajuda contextual (?) nos campos Nº do Vídeo, Tarefa e Canal",
        ],
    },
    {
        "versao": "v2.3",
        "data": "08/04/2026",
        "notas": [
            "Tarefas de todas as datas na lista (não filtra mais por dia)",
            "Pagamentos aparecem na lista de tarefas",
            "Limite de 30h não declaradas (aviso a partir de 20h)",
            "Trava por hora: tarefas após pagamento ficam livres",
            "Ordenação por data e hora real (pagamentos na posição correta)",
            "Changelog acessível na tela de login",
            "Correções de travamento e estabilidade (9 bugs corrigidos)",
        ],
    },
    {
        "versao": "v2.2",
        "data": "08/04/2026",
        "notas": [
            "Versão exibida no título da janela",
            "Resiliência offline (fila de heartbeats)",
            "Notificações Windows ao perder/restaurar conexão",
            "Auto-login com credenciais salvas",
            "Fix deadlock no monitor (banco fora do lock)",
        ],
    },
]
URL_ATUALIZACAO = "https://raw.githubusercontent.com/rafaelkolaias-lang/Cltcron/main/painel/downloads/CronometroLeve.exe"

# =========================
# Integração HTTP com o painel (para módulo MEGA e futuros consumos)
# =========================
# URL pública do painel em produção. Sem barra final.
# Override via env var `CRONOMETRO_URL_PAINEL` (útil em dev local com XAMPP:
# `http://localhost/cronometro-web/painel`).
import os as _os  # local — evita poluir o namespace público

URL_PAINEL = _os.environ.get("CRONOMETRO_URL_PAINEL", "https://banco-painel.cpgdmb.easypanel.host").rstrip("/")

# Chave fixa usada pelo painel para recifrar credenciais entregues ao desktop
# (XSalsa20-Poly1305 / libsodium secretbox). Vem de `app/segredos.py`
# (gitignored). Em modo dev sem segredos locais, fica vazia — o módulo MEGA
# valida e falha cedo com mensagem clara.
try:
    from app import segredos as _segredos  # type: ignore
    APP_CLIENT_DECRYPT_KEY = getattr(_segredos, "APP_CLIENT_DECRYPT_KEY", "")
except Exception:
    APP_CLIENT_DECRYPT_KEY = ""

INTERVALO_LOOP_SEGUNDOS = 0.20
INTERVALO_UI_MILISSEGUNDOS = 80
INTERVALO_HEARTBEAT_SEGUNDOS = 60.0
INTERVALO_STATUS_BANCO_SEGUNDOS = 10.0

LIMITE_OCIOSO_SEGUNDOS = 5 * 60

LIMITE_HORAS_AVISO = 20 * 3600       # 20h — avisa o usuário
LIMITE_HORAS_MAXIMO = 30 * 3600      # 30h — para de computar

CAPTURAR_TITULO_JANELA = False

INTERVALO_SCAN_APPS_SEGUNDOS = 10.0

# Persistência parcial de cronometro_relatorios — grava/atualiza a cada N segundos
# na mesma linha (id_sessao, referencia_data), para o painel web enxergar totais
# quase em tempo real sem esperar o fechamento da sessão.
INTERVALO_UPSERT_RELATORIO_SEGUNDOS = 300.0  # 5 minutos

# Verificação periódica de atualização após o login (apenas avisa, não aplica).
# Só roda quando executado como .exe (PyInstaller). Se achar update, abre modal
# informativo; se o usuário ignorar, o aviso reaparece no próximo ciclo enquanto
# houver atualização disponível.
INTERVALO_VERIFICAR_UPDATE_MS = 2 * 60 * 1000  # 2 minutos (auto-aplica)

ARQUIVO_LOGIN_SALVO = Path.home() / ".cronometro_leve_login.json"
ARQUIVO_ESTADO_SESSAO = Path.home() / ".cronometro_leve_estado.json"
ARQUIVO_FILA_OFFLINE = Path.home() / ".cronometro_leve_fila_offline.json"
ARQUIVO_REGRESSIVA = Path.home() / ".cronometro_leve_regressiva.json"
ARQUIVO_MEGA_SYNC = Path.home() / ".cronometro_leve_mega_sync.json"

TOLERANCIA_VALIDACAO_SEGUNDOS = 1


# =========================
# Estado local da sincronização MEGA (Tarefa 2)
# =========================
# Sincroniza pastas lógicas do banco com o que de fato existe na raiz do canal
# no MEGA. Roda 1x/dia em background, agendada 5s após clicar Iniciar.
# Estados:
#   - "nao_sincronizado": ainda não rodou hoje. Bloqueia Declarar Tarefa.
#   - "sincronizando":    em andamento. Bloqueia Declarar Tarefa, label SINCRONIZANDO.
#   - "sincronizado":     terminou ok hoje. Libera Declarar Tarefa.
#   - "erro":             última tentativa falhou. Bloqueia Declarar Tarefa, mostra erro.
#
# Por user_id: o arquivo é compartilhado entre logins distintos no mesmo PC, então
# guardamos um dict {user_id: {...}} no JSON pra evitar contaminação entre contas.
def carregar_estado_mega_sync(user_id: str) -> dict:
    """Lê estado da sync MEGA do usuário. Retorna dict com chaves padrão
    quando não há nada salvo (status='nao_sincronizado')."""
    padrao = {
        "status": "nao_sincronizado",
        "ultima_sync_ok": None,        # ISO 8601 da última sync bem-sucedida
        "ultima_tentativa": None,      # ISO 8601 da última tentativa (sucesso OU erro)
        "mensagem_erro": "",
        "data_sync_ok": None,          # YYYY-MM-DD da última sync ok (controle 1x/dia)
    }
    try:
        if not ARQUIVO_MEGA_SYNC.exists():
            return padrao
        with open(ARQUIVO_MEGA_SYNC, encoding="utf-8") as f:
            todos = json.load(f)
        if not isinstance(todos, dict):
            return padrao
        st = todos.get(str(user_id))
        if not isinstance(st, dict):
            return padrao
        return {**padrao, **st}
    except Exception:
        return padrao


def salvar_estado_mega_sync(user_id: str, estado: dict) -> None:
    """Persiste estado da sync MEGA do usuário no JSON local. Best-effort —
    falha de I/O é silenciada (não trava o app)."""
    try:
        todos = {}
        if ARQUIVO_MEGA_SYNC.exists():
            try:
                with open(ARQUIVO_MEGA_SYNC, encoding="utf-8") as f:
                    todos = json.load(f)
                if not isinstance(todos, dict):
                    todos = {}
            except Exception:
                todos = {}
        todos[str(user_id)] = dict(estado)
        with open(ARQUIVO_MEGA_SYNC, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def precisa_sincronizar_mega_hoje(user_id: str) -> bool:
    """True se ainda não houve sync bem-sucedida hoje pra este user."""
    st = carregar_estado_mega_sync(user_id)
    hoje = datetime.now().strftime("%Y-%m-%d")
    return st.get("data_sync_ok") != hoje
