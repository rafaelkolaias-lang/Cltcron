# Cronometro - Sistema de Controle de Horas e Atividades

Sistema completo de **rastreamento de tempo, gestao de tarefas e controle de pagamentos**, composto por um aplicativo desktop Windows e um painel web administrativo, conectados a um banco de dados MySQL compartilhado.

---

## Arquitetura Geral

```
┌─────────────────────────────────────┐
│   App Desktop (CronometroLeve.exe)  │
│   Python 3.12 + Tkinter            │
│   Monitoramento em tempo real       │
└────────────┬────────────────────────┘
             │ PyMySQL (TCP 3306)
             ▼
┌─────────────────────────────────────┐
│      MySQL / MariaDB (remoto)       │
│      Database: "dados"              │
│      16 tabelas InnoDB              │
└────────┬────────────────────┬───────┘
         │                    │
    Inserts/Updates        Queries
         │                    │
         ▼                    ▼
┌─────────────────────────────────────┐
│   Painel Web (PHP 8.1 + Apache)    │
│   Bootstrap 5 + JS vanilla         │
│   Gestao, relatorios, graficos     │
└─────────────────────────────────────┘
```

---

## Stack Tecnologica

| Camada | Tecnologia |
|--------|-----------|
| **Desktop** | Python 3.12, Tkinter, PyMySQL, psutil, ctypes (Windows API) |
| **Web** | PHP 8.1, Apache 2.4, Bootstrap 5, JavaScript vanilla |
| **Banco** | MySQL 5.7+ / MariaDB 9.6+, charset utf8mb4, InnoDB |
| **Build** | PyInstaller (gera `.exe` standalone para Windows) |
| **Deploy Web** | Docker (`php:8.1-apache`) ou XAMPP local |

---

## Estrutura de Arquivos

```
Cronometro/
├── app.py                    # App desktop principal (~1950 linhas)
├── banco.py                  # Modulo de conexao MySQL (thread-safe)
├── atividades.py             # Logica de atividades, pagamentos e locks
├── declaracoes_dia.py        # Subtarefas e declaracoes diarias
├── dados.sql                 # Schema completo do banco de dados
├── Dockerfile                # Container do painel web
├── CronometroLeve.spec       # Config do PyInstaller
├── atualizar_build.bat       # Script de build do .exe
├── .gitignore
│
└── painel/                   # Painel web administrativo
    ├── index.php             # Interface principal (SPA com abas)
    ├── baixar_app.php        # Download do .exe pelo navegador
    ├── css/
    │   └── painel.css        # Tema dark personalizado
    ├── js/
    │   ├── painel.js         # Nucleo: fetch, alerts, dashboard
    │   ├── aba-usuarios.js   # CRUD de usuarios + pagamentos
    │   ├── aba-atividades.js # CRUD de atividades
    │   ├── aba-relatorio.js  # Relatorios de horas + export CSV
    │   ├── aba-graficos.js   # Graficos de produtividade
    │   └── aba-timeline.js   # Timeline de eventos/sessoes
    ├── commands/
    │   ├── conexao/
    │   │   ├── conexao.php   # Conexao PDO com o banco
    │   │   └── testar.php    # Teste de conectividade
    │   ├── _comum/
    │   │   └── resposta.php  # Helper de respostas JSON padronizadas
    │   ├── usuarios/         # Endpoints de usuarios (6 arquivos)
    │   ├── atividades/       # Endpoints de atividades (5 arquivos)
    │   ├── pagamentos/       # Endpoints de pagamentos (2 arquivos)
    │   ├── status/           # Endpoints de monitoramento (3 arquivos)
    │   ├── relatorio/        # Endpoint de relatorio de horas
    │   └── graficos/         # Endpoint de dados para graficos
    └── downloads/
        └── CronometroLeve.exe  # Binario distribuido via web
```

---

## Banco de Dados

### Tabelas Principais (16 total)

#### Usuarios e Atividades

| Tabela | Descricao |
|--------|-----------|
| `usuarios` | Contas de usuario (user_id, nome, nivel, valor_hora, chave, status_conta) |
| `atividades` | Tarefas/projetos (titulo, descricao, dificuldade, estimativa_horas, status) |
| `atividades_usuarios` | Vinculo N:N entre usuarios e atividades |
| `atividades_subtarefas` | Subtarefas diarias de uma atividade (titulo, canal_entrega, segundos_gastos) |
| `atividades_subtarefas_historico` | Trilha de auditoria de todas as alteracoes em subtarefas (JSON antes/depois) |

#### Monitoramento de Sessao

| Tabela | Descricao |
|--------|-----------|
| `cronometro_sessoes` | Sessoes de monitoramento (token, maquina, sistema, versao_app, inicio/fim) |
| `cronometro_relatorios` | Relatorios finais de sessao (segundos total/trabalhando/ocioso/pausado) |
| `cronometro_eventos_status` | Eventos: inicio, pausa, retorno, finalizar, ocioso_inicio, ocioso_fim, heartbeat |
| `cronometro_foco_janela` | Rastreamento de janela em foco (nome do app, intervalo de tempo) |
| `cronometro_apps_intervalos` | Intervalos de uso de cada aplicativo (segundos em foco / segundo plano) |
| `usuarios_status_atual` | Status em tempo real do usuario (situacao, atividade, apps_json) |

#### Tempo e Pagamentos

| Tabela | Descricao |
|--------|-----------|
| `declaracoes_dia_itens` | Declaracoes de tempo diarias por atividade |
| `Pagamentos` | Registro de pagamentos com periodo de referencia e data de travamento |
| `registros_tempo` | Registros historicos de tempo (legado) |

#### Legado

| Tabela | Descricao |
|--------|-----------|
| `cronometro_finalizacoes` | Finalizacoes antigas (descontinuado) |
| `cronometro_finalizacoes_subtarefas` | Detalhes de finalizacoes antigas (descontinuado) |

### Diagrama de Relacionamentos

```
usuarios (1) ──── (N) atividades_usuarios (N) ──── (1) atividades
    │                                                      │
    │                                                      │
    ├── (N) cronometro_sessoes                             │
    │         │                                            │
    │         ├── (N) cronometro_eventos_status             │
    │         ├── (N) cronometro_foco_janela                │
    │         ├── (N) cronometro_apps_intervalos            │
    │         └── (1) cronometro_relatorios ───────────────┘
    │                                                      │
    ├── (1) usuarios_status_atual                          │
    │                                                      │
    ├── (N) atividades_subtarefas ─────────────────────────┘
    │         └── (N) atividades_subtarefas_historico
    │
    ├── (N) declaracoes_dia_itens
    │
    └── (N) Pagamentos
```

---

## App Desktop (app.py)

### Funcionalidades

- **Login** com user_id + chave (senha), com persistencia local em `~/.cronometro_leve_login.json`
- **Selecao de atividade** via combobox (mostra ID + titulo + status)
- **Cronometro visual** grande no formato HH:MM:SS
- **Deteccao de ociosidade** via Windows API (`GetLastInputInfo`) - limite de 5 minutos
- **Rastreamento de apps** em foco (nome do processo, sem captura de titulo por privacidade)
- **Enumeracao de apps** visiveis a cada 15 segundos
- **Sincronizacao com banco** a cada 5 segundos (status atual)
- **Heartbeat** a cada 60 segundos (evento no banco)
- **Restauracao de sessao** ao reiniciar (estado salvo em `~/.cronometro_leve_estado.json`)
- **Janela flutuante** ("Fixar") - mini timer always-on-top
- **Gestao de subtarefas** diarias com tempo, canal de entrega e observacoes
- **Finalizacao com relatorio** - abre tela de subtarefas para registrar o trabalho feito
- **Trava de pagamento** - impede edicao de periodos ja pagos

### Classes Principais

| Classe | Responsabilidade |
|--------|-----------------|
| `MonitorDeUso` | Loop de monitoramento (200ms), sincronizacao com banco, deteccao de ociosidade |
| `JanelaSubtarefas` | Modal de gestao de subtarefas diarias |
| `App` | Janela principal: login, cronometro, controles |
| `EstadoMonitor` | Dataclass com estado atual (rodando, situacao, segundos) |

### Constantes Importantes

```python
VERSAO_APLICACAO = "v2.1"
INTERVALO_LOOP_SEGUNDOS = 0.20           # Loop de monitoramento: 200ms
INTERVALO_UI_MILISSEGUNDOS = 80          # Refresh da UI: 80ms
INTERVALO_HEARTBEAT_SEGUNDOS = 60.0      # Heartbeat: 60s
INTERVALO_STATUS_BANCO_SEGUNDOS = 5.0    # Sync com banco: 5s
LIMITE_OCIOSO_SEGUNDOS = 300             # Limite de ociosidade: 5 min
INTERVALO_SCAN_APPS_SEGUNDOS = 15.0      # Scan de apps: 15s
CAPTURAR_TITULO_JANELA = False           # Privacidade: nao captura titulo
```

---

## Painel Web (painel/)

### Interface

- **SPA com abas** (Bootstrap 5 + JS vanilla): Dashboard, Atividades, Usuarios, Relatorios, Timeline
- **Tema dark** customizado (fundo `#0b1220`, cards translucidos com `backdrop-filter`)
- **Comunicacao AJAX** com endpoints PHP que retornam JSON padronizado

### Formato de Resposta da API

```json
{
  "ok": true,
  "mensagem": "Operacao realizada com sucesso",
  "dados": { ... }
}
```

### Endpoints PHP (21 total)

| Grupo | Endpoint | Metodo | Descricao |
|-------|---------|--------|-----------|
| **Usuarios** | `usuarios/listar.php` | GET | Lista todos os usuarios |
| | `usuarios/listar_ativos.php` | GET | Lista apenas usuarios ativos |
| | `usuarios/criar.php` | POST | Cria novo usuario |
| | `usuarios/editar.php` | POST | Edita usuario existente |
| | `usuarios/excluir.php` | POST | Exclui usuario |
| | `usuarios/atualizar_status.php` | POST | Altera status da conta |
| **Atividades** | `atividades/listar.php` | GET | Lista atividades com usuarios vinculados |
| | `atividades/criar.php` | POST | Cria nova atividade |
| | `atividades/editar.php` | POST | Edita atividade |
| | `atividades/excluir.php` | POST | Exclui atividade |
| | `atividades/alterar_status.php` | POST | Altera status da atividade |
| **Pagamentos** | `pagamentos/criar.php` | POST | Registra pagamento (com trava de periodo) |
| | `pagamentos/listar_por_usuario.php` | GET | Lista pagamentos de um usuario |
| **Status** | `status/listar.php` | GET | Status em tempo real de todos os usuarios |
| | `status/atualizar.php` | POST | Atualiza status de usuario |
| | `status/horas_mes.php` | GET | Resumo de horas do mes |
| **Relatorio** | `relatorio/tempo_trabalhado.php` | POST | Relatorio de horas trabalhadas (com valor) |
| **Graficos** | `graficos/graficos.php` | GET | Dados para graficos de produtividade |
| **Conexao** | `conexao/testar.php` | GET | Testa conectividade com o banco |

---

## Sistema de Trava de Pagamento

Um dos recursos mais importantes do sistema. Ao registrar um pagamento:

1. Define-se `referencia_inicio`, `referencia_fim` e `travado_ate_data`
2. Todas as subtarefas e declaracoes dentro do periodo sao **bloqueadas**
3. Tentativas de editar/excluir dados em periodos travados sao recusadas
4. Alteracoes sao registradas na tabela de historico para auditoria

**Fluxo:**
```
Registrar Pagamento → Definir travado_ate_data → Bloquear edicoes retroativas
                                                        ↓
                                         Trilha de auditoria (historico JSON)
```

---

## Como Rodar

### Pre-requisitos

- **Python 3.8+** (recomendado 3.12)
- **MySQL 5.7+** ou MariaDB
- **XAMPP** ou **Docker** (para o painel web)

### 1. Configurar o Banco de Dados

```bash
# Importar o schema
mysql -u root -p < dados.sql
```

> **Importante:** Ajuste as credenciais de conexao em:
> - `banco.py` (linhas 13-17) — app desktop
> - `painel/commands/conexao/conexao.php` — painel web
>
> Ou defina as variaveis de ambiente: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS`

### 2. Rodar o App Desktop

```bash
# Instalar dependencias
pip install pymysql psutil

# Executar
python app.py
```

Ou usar o executavel compilado: `dist/CronometroLeve.exe`

### 3. Rodar o Painel Web

**Opcao A: XAMPP**
- Copie a pasta `painel/` para `htdocs/dashboard/Cronometro/painel/`
- Acesse: `http://localhost/dashboard/Cronometro/painel/`

**Opcao B: Docker**
```bash
docker build -t cronometro-painel .
docker run -d -p 8080:80 cronometro-painel
# Acesse: http://localhost:8080
```

### 4. Compilar o .exe (Build)

```bash
# Instalar PyInstaller
pip install pyinstaller

# Gerar o executavel
python -m PyInstaller --clean --noconfirm CronometroLeve.spec

# Ou usar o script automatizado:
atualizar_build.bat
```

O `.exe` sera gerado em `dist/CronometroLeve.exe` e copiado para `painel/downloads/`.

---

## Dependencias Python

| Pacote | Uso |
|--------|-----|
| `pymysql` | Conexao com MySQL/MariaDB |
| `psutil` | Monitoramento de processos (nomes de apps) |
| `tkinter` | Interface grafica (incluso no Python) |
| `pyinstaller` | Compilacao para .exe (apenas dev) |

```bash
pip install pymysql psutil pyinstaller
```

---

## Variaveis de Ambiente (Painel Web)

| Variavel | Descricao | Padrao |
|----------|-----------|--------|
| `DB_HOST` | Host do banco MySQL | `76.13.112.108` |
| `DB_PORT` | Porta do MySQL | `3306` |
| `DB_NAME` | Nome do banco | `dados` |
| `DB_USER` | Usuario do banco | - |
| `DB_PASS` | Senha do banco | - |
| `APP_DEBUG` | Modo debug (1 = ativado) | `0` |

---

## Fluxo de Trabalho do Usuario

```
1. Abrir CronometroLeve.exe
2. Fazer login (user_id + chave)
3. Selecionar atividade no combobox
4. Clicar "Iniciar" → cronometro comeca
5. Trabalhar normalmente (sistema monitora apps em foco)
6. Se ficar 5min parado → status muda para "ocioso" automaticamente
7. Pode clicar "Pausar" manualmente para intervalos
8. Clicar "Tarefas" para registrar subtarefas do dia
9. Ao terminar: "Finalizar" → abre tela de subtarefas
10. Preencher o que foi feito + tempo → "Encerrar e Enviar Relatorio"
```

```
Admin no Painel Web:
1. Acompanha status em tempo real no Dashboard
2. Gerencia usuarios, atividades e vinculos
3. Gera relatorios de horas trabalhadas por periodo
4. Registra pagamentos (trava periodo contra edicao)
5. Visualiza timeline de eventos e graficos
```

---

## Notas para o Proximo Dev

### Pontos de Atencao

1. **Credenciais hardcoded** — `banco.py` e `conexao.php` tem host/user/senha fixos. Idealmente migrar para `.env` ou variaveis de ambiente em ambos os lados.

2. **App e desktop only Windows** — Usa `ctypes` + Windows API (`user32.dll`, `kernel32.dll`) para deteccao de ociosidade e janela ativa. Nao funciona em Linux/macOS.

3. **Sem autenticacao no painel web** — Qualquer pessoa com acesso a URL consegue usar o painel. Recomendado adicionar login/auth.

4. **Auto-migration** — `atividades.py` e `declaracoes_dia.py` fazem migrations automaticas (ALTER TABLE, CREATE TABLE) na inicializacao. Se adicionar colunas novas, siga o mesmo padrao.

5. **Thread-safety** — `banco.py` usa `threading.local()` para uma conexao por thread. Nao compartilhe objetos de conexao entre threads.

6. **Tabelas legado** — `cronometro_finalizacoes` e `cronometro_finalizacoes_subtarefas` estao descontinuadas, podem ser removidas futuramente.

7. **Formato de data** — O sistema usa `referencia_data` (DATE) para agrupar subtarefas por dia. O fuso horario e o do servidor MySQL.

### Melhorias Sugeridas

- [ ] Migrar credenciais para `.env` / variaveis de ambiente
- [ ] Adicionar autenticacao no painel web (login admin)
- [ ] Criar `requirements.txt` com versoes fixas
- [ ] Adicionar testes automatizados
- [ ] Implementar HTTPS para conexao com banco
- [ ] Adicionar suporte a notificacoes (lembrete de pausas, etc.)
- [ ] Dashboard com graficos mais ricos (Chart.js ja esta parcialmente integrado)

---

## Versao

**App Desktop:** v2.1  
**Painel Web:** Sem versionamento formal  
**Banco:** Schema em `dados.sql`

---

## Licenca

Projeto proprietario - uso interno.
