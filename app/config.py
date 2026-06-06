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


# =========================
# CERTIFICADOS HTTPS (certifi embutido)
# =========================
# Força TODAS as conexões HTTPS (urllib) a validarem contra o bundle de
# certificados-raiz do `certifi`, em vez do repositório do Windows de cada
# usuário. Motivo: PCs antigos/desatualizados não têm os roots novos da
# Let's Encrypt (ISRG Root X1/X2) e o OpenSSL acabava seguindo o "DST Root
# CA X3" (vencido em 30/09/2021), quebrando a sync MEGA com
# "certificate has expired" mesmo com a hora certa. O navegador funcionava
# porque baixa esses roots sozinho; o app não. Com certifi embutido, o app
# carrega os roots corretos consigo e funciona em qualquer PC.
# Importante: definir no import de `config` garante que roda antes de
# qualquer chamada de rede (config é importado por todos os módulos).
try:
    import ssl as _ssl
    import certifi as _certifi

    def _contexto_https_certifi(*_args, **_kwargs):
        return _ssl.create_default_context(cafile=_certifi.where())

    # urllib.request.urlopen sem `context` usa este hook global.
    _ssl._create_default_https_context = _contexto_https_certifi
except Exception:
    # Sem certifi (ambiente de dev incompleto): mantém o comportamento
    # padrão (repositório do SO). Não pode quebrar o import de config.
    pass


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
VERSAO_APLICACAO = "v4.0.4"

HISTORICO_VERSOES = [
    {
        "versao": "v4.0.4",
        "data": "06/06/2026",
        "notas": [
            "Corrigido: pastas de vídeo já criadas sumiam da lista 'Selecionar existente' ao declarar tarefa. Acontecia quando o título tinha '?', aspas ou terminava em ponto (ex.: '...buraco negro?' ou '...Einstein.') — a sincronização as marcava como inexistentes por engano. Agora elas continuam aparecendo normalmente.",
            "Corrigido: ao baixar um arquivo de uma pasta antiga ou com caractere especial no nome, o download falhava com erro 'não foi possível baixar / não encontrado'. Agora o app tenta automaticamente os caminhos alternativos e baixa do jeito certo.",
            "Melhoria: a geração do link público da pasta no MEGA passou a funcionar também em pastas com '?'/aspas no nome.",
            "Melhoria interna: caracteres que podiam quebrar comandos no Windows (%, &, ^) agora são tratados no nome das pastas.",
        ],
    },
    {
        "versao": "v4.0.3",
        "data": "04/06/2026",
        "notas": [
            "Fix: em alguns computadores (geralmente Windows desatualizado) a sincronização das pastas MEGA falhava com erro de 'certificado expirado', mesmo com a data e a hora corretas, porque o computador não tinha os certificados de segurança mais novos. Agora o app já vem com esses certificados embutidos e funciona em qualquer computador, sem depender das atualizações do Windows.",
        ],
    },
    {
        "versao": "v4.0.2",
        "data": "04/06/2026",
        "notas": [
            "Quando a sincronização das pastas MEGA falha, agora aparece um botão 'Copiar erro' que copia a mensagem completa do erro (antes a tela mostrava só um trecho cortado).",
            "Quando a falha de sincronização é causada pela data/hora do computador desatualizada, o app passa a mostrar um aviso claro pedindo para ajustar a data e a hora do Windows, em vez de um erro técnico difícil de entender.",
        ],
    },
    {
        "versao": "v4.0.1",
        "data": "21/05/2026",
        "notas": [
            "Fix: validação de horas disponíveis contava subtarefas já pagas, bloqueando declarações indevidamente após pagamento.",
            "Fix: restauração de sessão offline não descartava sessão válida quando o banco estava temporariamente inalcançável.",
        ],
    },
    {
        "versao": "v4.0",
        "data": "20/05/2026",
        "notas": [
            "Fix: vídeos com aspas ou caracteres especiais no título (ex.: 'evidências de \"vida\" em Encélado') falhavam no upload MEGA com rc=53. Agora aspas são convertidas para apóstrofo e caracteres proibidos são removidos automaticamente do nome da pasta.",
            "Fix: se a pasta do vídeo não existia mais no MEGA (apagada ou nunca criada), o reenvio falhava com rc=12. Agora o app recria a pasta automaticamente antes de enviar.",
            "Fix: erro interno ao concluir envio de arquivos pelo popup (janela já destruída). Corrigido.",
            "Melhoria: botão 'Cancelar' no popup de envio agora aparece legível (antes ficava espremido como um traço vermelho).",
            "Melhoria: botão do formulário de declaração agora mostra 'Enviar Arquivos' desde o início (antes mostrava 'Salvar e Concluir' até criar a pasta lógica).",
            "Segurança: formulário legado (sem upload MEGA) agora bloqueia qualquer declaração — toda tarefa deve passar pelo fluxo com 'Enviar Arquivos'.",
        ],
    },
    {
        "versao": "v3.1.11",
        "data": "17/05/2026",
        "notas": [
            "Cronômetro fixado (janela pequena que fica sempre por cima) ganhou visual mais discreto: o fundo da janela some completamente e fica visível apenas uma caixinha preta envolvendo o número do tempo. Em uso normal a caixinha fica em 80% de opacidade — sem tampar totalmente o que está embaixo, mas com o tempo bem legível. Quando você passa o mouse sobre ela, fica quase invisível (10%) para liberar a visualização do que estiver atrás — e volta ao normal assim que o cursor sai. A caixinha aparece no canto superior direito da tela e os cliques do mouse atravessam ela para chegar na janela que estiver atrás. Para fechar/abrir o fixado, continue usando o botão 'Fixar' na janela principal do app.",
        ],
    },
    {
        "versao": "v3.1.10",
        "data": "17/05/2026",
        "notas": [
            "Fix crítico: 'Enviar Arquivos' falhava em uma pasta existente quando ainda não havia tarefa pessoal naquela pasta — o app mostrava 'Não foi possível registrar a tarefa no servidor / verifique sua conexão com a internet' mesmo com a internet 100% OK, e nenhum arquivo subia. A causa nem chegava a tocar o servidor: ao selecionar a pasta, o app marcava internamente o estado como 'já resolvido com id 0', e na hora do envio devolvia esse 0 como se fosse uma falha de rede. Agora, ao selecionar uma pasta sem tarefa sua dentro, o estado fica realmente vazio — o envio segue normalmente e cria a tarefa antes do upload, como esperado. Bug existia desde a v3.1.6.",
        ],
    },
    {
        "versao": "v3.1.9",
        "data": "17/05/2026",
        "notas": [
            "Fix: erro 'Failed to load Python DLL' que aparecia após o auto-update — o Windows marcava o exe baixado como 'arquivo da internet' (Zone.Identifier) e o antivírus bloqueava a carga das DLLs internas, impedindo o app de abrir sozinho depois de atualizar. Agora a marca é removida logo após o download; o exe novo abre tratado como arquivo local. (Obs.: para sair definitivamente dessa atualização, pode ainda aparecer o erro UMA última vez ao atualizar para esta versão — basta fechar e abrir o app manualmente; das próximas em diante o problema some.)",
        ],
    },
    {
        "versao": "v3.1.8",
        "data": "17/05/2026",
        "notas": [
            "Fix crítico: tarefa enviada via 'Enviar Arquivos' às vezes não era declarada — o arquivo subia no MEGA mas a subtarefa ficava órfã (recuperada como 'aberta' só ao reabrir o app). Agora a subtarefa é registrada no servidor ANTES de qualquer upload começar; se a comunicação falhar, nenhum arquivo sobe e o usuário vê o erro na hora",
            "Arquivos enviados em pasta existente agora ficam isolados em uma subpasta com o nome do próprio usuário (ex.: '/Pasta_Raiz/04 - Artemis/usuario_x/'). Cada usuário tem seu espaço — sem colisões de nome com colegas e a exclusão da tarefa apaga só a subpasta do dono, sem tocar nos arquivos dos outros",
            "Popup 'Envio de Arquivos MEGA' ganhou mais largura — 'Tempo restante' não corta mais o texto ('calculando...', 'concluído', etc.)",
            "Falhas silenciosas ao criar a subtarefa durante o upload agora vão pro log técnico (~/.cronometro_leve_log_tecnico.txt) — facilita diagnóstico se voltar a acontecer",
        ],
    },
    {
        "versao": "v3.1.7",
        "data": "17/05/2026",
        "notas": [
            "Lista de canais agora é atualizada ao abrir 'Tarefas da Atividade' e ao clicar em 'Declarar Tarefa' — vínculos e desvínculos feitos no painel passam a refletir imediatamente, sem precisar relogar no app",
            "Combo CANAL no formulário 'Nova Tarefa' (legado) agora é selecionável — trocar de canal re-despacha automaticamente pro formulário correto (legado ou MEGA) conforme a configuração do canal escolhido",
            "Trocar pra um canal sem upload obrigatório dentro do formulário MEGA agora abre o formulário legado automaticamente em vez de mostrar aviso",
            "Tooltips e mensagens deixam de mencionar 'menu principal' inexistente — a seleção de canal acontece na própria janela 'Declarar Tarefa'",
        ],
    },
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
