# Cronometro

**Sistema de controle de produtividade para equipes remotas.**

Monitora em tempo real quais aplicativos o editor esta usando, quanto tempo ficou em cada um, detecta ociosidade automaticamente e impede que horas nao trabalhadas sejam declaradas.

---

## Visao Geral

```
  App Desktop (Windows)              Painel Web (Admin)
  ┌────────────────────┐             ┌────────────────────┐
  │  Python + Tkinter  │             │  PHP + Bootstrap 5 │
  │                    │             │  + ECharts         │
  │  Captura app foco  │             │                    │
  │  Detecta ocioso    │   MySQL     │  Graficos tempo    │
  │  Tracked 200ms     ├────────────►│  real de apps      │
  │  Heartbeat 60s     │             │  Timeline dia/dia  │
  │  Status sync 5s    │             │  Status ao vivo    │
  └────────────────────┘             └────────────────────┘
```

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Desktop | Python 3.12, Tkinter, PyMySQL, psutil, Windows API |
| Web | PHP 8.1, Bootstrap 5, JavaScript vanilla, ECharts 5 |
| Banco | MySQL 5.7+ / MariaDB 9.6+, InnoDB, utf8mb4 |
| Build | PyInstaller (.exe standalone) |
| Deploy | Docker (php:8.1-apache) ou XAMPP |

---

## O Que o Sistema Faz

### App Desktop (editor)

- Captura o app em primeiro plano a cada **200ms**
- Detecta ociosidade via Windows API (5 min sem mouse/teclado)
- Escaneia todos os apps visiveis a cada **15 segundos**
- Registra tempo exato de foco por app (inicio/fim)
- Envia heartbeat a cada 60s e sync de status a cada 5s
- Restaura sessao automaticamente apos queda/reinicio
- Janela flutuante mini-timer (always-on-top)
- Gestao de subtarefas diarias com declaracao de tempo

### Painel Web (admin)

- **Dashboard** com status em tempo real de todos os editores
- **Graficos ECharts**: donut de apps, ranking foco vs 2o plano, timeline dia a dia
- **Tabela de editores** com colunas Trabalhado (verde) e Ocioso (amarelo)
- **Relatorios** de horas com calculo de valor (R$/hora)
- **Pagamentos** com trava de periodo (bloqueia edicao retroativa)
- **Gestao** de usuarios e atividades

### Seguranca Anti-Fraude

- Editor **nao pode pausar** enquanto estiver ocioso (tempo ocioso fica registrado)
- Declaracao de horas validada contra `segundos_trabalhando` (sem ocioso, sem pausado)
- Tempo ocioso aparece separado no painel (amarelo) para o admin comparar
- Timeline mostra exatamente qual app estava em foco e em que horario

---

## Estrutura

```
Cronometro/
├── app.py                    # App desktop (~2000 linhas)
├── banco.py                  # Conexao MySQL thread-safe
├── atividades.py             # Logica de atividades e pagamentos
├── declaracoes_dia.py        # Subtarefas e declaracoes diarias
├── dados.sql                 # Schema completo (16 tabelas)
├── Dockerfile                # Container do painel web
├── CronometroLeve.spec       # Config do PyInstaller
├── atualizar_build.bat       # Script de build
│
└── painel/
    ├── index.php             # Interface SPA
    ├── css/painel.css        # Tema dark
    ├── js/
    │   ├── painel.js         # Nucleo + dashboard
    │   ├── aba-usuarios.js   # CRUD usuarios + pagamentos
    │   ├── aba-atividades.js # CRUD atividades
    │   ├── aba-graficos.js   # Graficos ECharts + timeline
    │   ├── aba-relatorio.js  # Relatorios de horas
    │   └── aba-timeline.js   # Timeline de eventos
    └── commands/
        ├── conexao/          # Conexao PDO
        ├── usuarios/         # 6 endpoints
        ├── atividades/       # 5 endpoints
        ├── pagamentos/       # 2 endpoints
        ├── status/           # 3 endpoints
        ├── relatorio/        # 1 endpoint
        └── graficos/         # 1 endpoint
```

---

## Banco de Dados (16 tabelas)

### Monitoramento
| Tabela | Descricao |
|--------|-----------|
| `cronometro_sessoes` | Sessoes com token, maquina, inicio/fim |
| `cronometro_relatorios` | Totais: trabalhando / ocioso / pausado |
| `cronometro_eventos_status` | Eventos: inicio, pausa, ocioso_inicio, heartbeat... |
| `cronometro_foco_janela` | Periodos exatos de foco por app |
| `cronometro_apps_intervalos` | Tempo em foco vs 2o plano por app |
| `usuarios_status_atual` | Status em tempo real |

### Negocio
| Tabela | Descricao |
|--------|-----------|
| `usuarios` | Contas (user_id, nome, nivel, valor_hora) |
| `atividades` | Projetos/tarefas |
| `atividades_usuarios` | Vinculo N:N |
| `atividades_subtarefas` | Declaracoes diarias de trabalho |
| `atividades_subtarefas_historico` | Auditoria (JSON antes/depois) |
| `declaracoes_dia_itens` | Itens de declaracao por dia |
| `Pagamentos` | Pagamentos com trava de periodo |

---

## Como Rodar

### 1. Banco de Dados

```bash
mysql -u root -p < dados.sql
```

### 2. App Desktop

```bash
pip install pymysql psutil
python app.py
```

Ou use o .exe compilado: `dist/CronometroLeve.exe`

### 3. Painel Web

**XAMPP:**
```
Copie painel/ para htdocs/dashboard/Cronometro/painel/
Acesse: http://localhost/dashboard/Cronometro/painel/
```

**Docker:**
```bash
docker build -t cronometro-painel .
docker run -d -p 8080:80 cronometro-painel
```

### 4. Build do .exe

```bash
pip install pyinstaller
python -m PyInstaller --clean --noconfirm CronometroLeve.spec
```

---

## Variaveis de Ambiente

| Variavel | Descricao | Padrao |
|----------|-----------|--------|
| `DB_HOST` | Host MySQL | `76.13.112.108` |
| `DB_PORT` | Porta | `3306` |
| `DB_NAME` | Database | `dados` |
| `DB_USER` | Usuario | - |
| `DB_PASS` | Senha | - |

---

## Changelog

### v2.2 (2026-04-05)

**Performance**
- Save local debounced de 200ms para 10s (95% menos I/O disco)
- Batch updates de apps com `executar_muitos` (~99% menos queries)
- UPSERT com `ON DUPLICATE KEY UPDATE` no status
- Cache de processos psutil com TTL 60s
- Ping do banco reduzido para cada 60s
- Getters otimizados (sem snapshot completo a cada 80ms)
- Debounce 300ms em todas as buscas JS
- Event delegation no lugar de listeners repetidos
- Timers pausam quando aba do navegador fica oculta
- Indice composto em `cronometro_relatorios`

**Graficos (redesign completo)**
- ECharts 5: donut de apps, barras ranking, timeline dia a dia
- Navegacao por dia com botoes esquerda/direita na timeline
- Cards de status em tempo real (trabalhando/ocioso/pausado)
- Perfil do editor com avatar, status, apps abertos como pills
- Colunas "Trabalhado" (verde) e "Ocioso" (amarelo) na tabela
- Layout dark theme elegante com paleta azul-violeta

**Seguranca**
- Pausa bloqueada durante estado ocioso
- Tempo ocioso visivel separadamente no painel
- PHP retorna `segundos_trabalhando_total` e `segundos_ocioso_total` por usuario

### v2.1 (commit inicial)

- Sistema completo: app desktop + painel web + banco de dados
- Monitoramento de apps, sessoes, eventos, subtarefas
- Sistema de pagamentos com trava de periodo

---

## Licenca

Projeto proprietario — uso interno.
