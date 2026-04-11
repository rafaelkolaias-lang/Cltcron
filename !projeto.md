# Cronômetro - Sistema de Controle de Produtividade

Este documento fornece uma descrição detalhada do projeto **Cronômetro**, um sistema robusto desenvolvido para monitoramento de produtividade e gestão de equipes remotas (especialmente editores de vídeo).

## 🚀 Objetivo do Projeto

O sistema visa garantir que o tempo declarado pelos colaboradores corresponda ao tempo real de trabalho efetivo, utilizando monitoramento em tempo real, detecção automática de ociosidade e relatórios detalhados de uso de aplicativos.

---

## 🏗️ Arquitetura do Sistema

O projeto é dividido em uma arquitetura Cliente-Servidor:

1.  **Aplicação Desktop (Editor):**
    *   Desenvolvida em **Python** com interface **Tkinter**.
    *   Roda em segundo plano no Windows.
    *   Captura o aplicativo em foco a cada **200ms**.
    *   Detecta inatividade (mouse/teclado) via **Windows API**.
    *   Sincroniza dados com o banco de dados via **heartbeats** e **status updates**.

2.  **Painel Web (Admin):**
    *   Desenvolvido em **PHP 8.1** com **Bootstrap 5**.
    *   Utiliza **ECharts 5** para visualização de dados complexos.
    *   Interface SPA (Single Page Application) com JavaScript Vanilla.
    *   Permite aos administradores monitorar o status "Ao Vivo" dos editores.

3.  **Banco de Dados:**
    *   **MySQL/MariaDB** centralizado.
    *   Contém 16 tabelas que gerenciam desde sessões de monitoramento até fluxos de pagamento.

---

## 🛠️ Stack Tecnológica

### Desktop (Cliente)
- **Linguagem:** Python 3.12
- **Interface:** Tkinter (Customized)
- **Integração OS:** Windows API (via `ctypes`), `psutil`
- **Banco de Dados:** `PyMySQL` (Thread-safe)
- **Distribuição:** PyInstaller (Gera `.exe` standalone)

### Web (Administração)
- **Backend:** PHP 8.1 / PDO
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla), Bootstrap 5
- **Gráficos:** Apache ECharts 5
- **Containerização:** Docker (php:8.1-apache)

---

## 💎 Funcionalidades Principais

### Para o Membro (Desktop)
- **Monitoramento de Foco:** Registro automático de qual Janela/App está sendo usado (scan a cada 200ms).
- **Detecção de Ociosidade:** Se o usuário ficar 5 minutos sem interagir (mouse/teclado via Windows API), o sistema entra em modo "Ocioso" e para de contar tempo.
- **Gestão de Tarefas:** Declaração de atividades com máscara de tempo inteligente (dígitos entram pela direita, estilo calculadora) e Canal pré-selecionado com a atividade atual via Combobox.
- **Botão Dinâmico:** Único botão de controle que alterna entre Iniciar / Pausar / Retomar conforme o estado da sessão.
- **Zerar Cronômetro:** Para e fecha a sessão atual com confirmação — horas de heartbeat preservadas no banco, sem criar relatório prematuro.
- **Mini-Timer:** Janela flutuante "Sempre no Topo" para acompanhamento do tempo atual.
- **Auto-Login:** credenciais salvas em `~/.cronometro_leve_login.json` — na próxima abertura o login é feito automaticamente sem mostrar o formulário; formulário só aparece se offline ou credenciais inválidas.
- **Resiliência offline:** heartbeats e eventos de ocioso perdidos durante queda de conexão são salvos em `~/.cronometro_leve_fila_offline.json` com timestamp original e re-enviados automaticamente quando o banco volta. Botão "Tarefas" desabilitado offline com aviso amarelo na tela.
- **Notificações Windows:** popup `MessageBoxW` ao frente de todas as janelas quando a conexão cai (1x) e ao reconectar (com quantidade de eventos re-enviados).
- **Restauração de sessão:** estado salvo em `~/.cronometro_leve_estado.json` — sessão restaurada automaticamente após quedas de internet ou reinicializações.
- **Auto-Update:** ao fazer login, verifica automaticamente se há nova versão do `.exe` no servidor; se houver, baixa, substitui e reinicia. Ignorado ao rodar como `.py` (modo dev via `getattr(sys, "frozen", False)`).
- **Limite de 30h não declaradas:** o sistema para de acumular tempo trabalhado ao atingir 30h sem declaração. A partir de 20h, avisos são exibidos ao clicar em qualquer botão orientando o usuário a declarar horas.
- **Pagamentos na lista de tarefas:** pagamentos aparecem intercalados na lista de tarefas do app desktop (linha verde), ordenados por data com pagamentos acima das subtarefas do mesmo dia.

### Para o Administrador (Web)
- **Dashboard Unificado:** Cards de status em tempo real (Trabalhando/Ocioso/Pausado) + "Visão Geral da Equipe" com status ao vivo, app em foco, conta (Ativa/Inativa), R$/hora, horas trabalhadas/ociosas e botão Gestão — tudo numa tela só, sem aba separada de gráficos.
- **Ações Rápidas:** Botões "+ Adicionar Usuário" e "+ Nova Atividade" no topo do Dashboard.
- **Timeout de Zumbi:** Membros sem heartbeat há mais de 3 minutos são automaticamente marcados como "Pausado" na API — sem fantasmas "trabalhando" no painel.
- **Timelines Detalhadas:** Gantt por membro — "Em Foco" (apps que tiveram foco) e "Todos os Apps Abertos" (foco + 2.º plano), com navegação dia a dia e eixo X adaptado ao intervalo real dos dados.
- **Top Apps:** Gráfico de rosca com distribuição de uso por software; filtro interativo por clique nas fatias ou na legenda lateral; cores persistidas no `localStorage`.
- **Visão da Equipe:** Timeline multi-membro, comparativo de horas (Trabalhado/Ocioso/Pausado) e top apps agregados.
- **Relatório de Horas:** Filtros por data e membro; colunas Trabalhado (monitorado) vs Declarado; status de pagamento (Pago/Pendente); indicador de divergência (⚠ quando declarado > trabalhado+10%); agrupamento por usuário ou dia; **export CSV** com separador `;` e BOM UTF-8.
- **Gestão de Membros:** CRUD completo — níveis (`iniciante/intermediário/avançado`), `valor_hora`, status de conta (`ativa/inativa/bloqueada`), chave de acesso auto-gerada. Resumo para pagamento com horas não pagas e valor a pagar.
- **Gestão de Atividades:** CRUD com dificuldade, estimativa de horas, vínculo a múltiplos membros.
- **Gerenciar Tarefas:** Painel para visualizar e editar todas as declarações (`atividades_subtarefas`) de todos os membros; filtros por data, usuário, atividade e canal; painel de horas (Trabalhado/Declarado/Disponível acumulado); validação impede declarar mais que o trabalhado; integração com trava de pagamento.
- **Pagamentos com Trava:** Registra pagamento e bloqueia automaticamente todas as subtarefas do período — impede edição/exclusão retroativa. Histórico de bloqueio registrado em auditoria. Trava por hora: no dia do pagamento, subtarefas criadas após o horário ficam livres.
- **Editar/Excluir Pagamentos:** Botões de edição e exclusão por linha no histórico de pagamentos. Exclusão destrava automaticamente subtarefas vinculadas.
- **Limpeza de horas no pagamento:** Ao registrar pagamento, remove `registros_tempo` anteriores à última declaração do usuário — elimina "ruído" de horas não declaradas acumuladas.
- **Gestão de Usuário em Página:** Modal convertido em página completa (seção SPA) com layout em 2 colunas: dados + resumo à esquerda, pagamentos + tarefas declaradas à direita. Botão Editar nas tarefas abre o mesmo modal de Gerenciar Tarefas.
- **Auditoria Completa:** Toda criação/edição/exclusão/conclusão/bloqueio de subtarefa gera registro JSON com estado antes e depois.

---

## 🔒 Segurança e Anti-Fraude

### Anti-Fraude (Desktop)
- **Bloqueio de Pausa Ociosa:** O editor não pode pausar o cronômetro enquanto o sistema detecta ociosidade.
- **Validação de Horas:** Declarações de subtarefas são validadas contra o tempo real monitorado (`segundos_trabalhando`).
- **Visibilidade Total:** O administrador vê o tempo ocioso separado (em amarelo) no painel.

### Segurança do Painel Web
- **Autenticação obrigatória:** Login com bcrypt hash — 18 endpoints protegidos via `verificar_sessao_painel()`.
- **Sessão + "Permanecer logado":** Sessão PHP com `session_regenerate_id(true)` no login; cookie de 30 dias via token aleatório de 64 caracteres.
- **Tokens protegidos:** `.tokens.json` bloqueado via `.htaccess` (`FilesMatch` para `.json`, `.bak`, `.old`, `.env`).
- **Logs protegidos:** Pasta `logs/` com `.htaccess` (`Require all denied`).
- **Debug restrito:** `debug_ativo()` aceita apenas `APP_DEBUG=1` via variável de ambiente — sem querystring ou header.
- **Endpoints públicos (app desktop):** Apenas `status/atualizar.php`, `status/listar.php`, `status/horas_mes.php` e `baixar_app.php`.

---

## 📁 Estrutura de Arquivos

```text
/
├── app.py                    # Core do App Desktop (Monitoramento e UI)
├── banco.py                  # Camada de persistência MySQL (thread-safe)
├── atividades.py             # Regras de negócio: projetos, tarefas, pagamentos
├── declaracoes_dia.py        # Submissão de horas + subtarefas + auditoria
├── dados.sql                 # DDL completo do banco + dados iniciais
├── logo.png                  # Ícone RK Produções (636×636 RGBA) usado no app desktop
├── Dockerfile                # Build do painel web (php:8.1-apache)
├── atualizar_build.bat       # Script para gerar CronometroLeve.exe via PyInstaller
├── requirements.txt          # pymysql, psutil
├── requirements-dev.txt      # ruff, mypy, pytest, bandit (dev)
├── pyproject.toml            # Configuração de ferramentas Python
├── painel/
│   ├── index.php             # Entry point SPA (requer autenticação)
│   ├── login.php             # Tela de login (dark card, RK Produções)
│   ├── logout.php            # Destrói sessão/cookie e redireciona para login
│   ├── baixar_app.php        # Serve CronometroLeve.exe para auto-update
│   ├── downloads/
│   │   └── CronometroLeve.exe # Executável para auto-update via GitHub raw
│   ├── img/
│   │   └── favicon.svg       # Ícone play vermelho + "RK"
│   ├── logs/
│   │   └── .htaccess         # Require all denied (protege logs)
│   ├── js/
│   │   ├── painel.js         # Core: dashboard, status ao vivo, navegação
│   │   ├── aba-graficos.js   # ECharts: timelines, donuts, barras, filtros
│   │   ├── aba-relatorio.js  # Relatório detalhado + export CSV
│   │   ├── aba-atividades.js # CRUD de atividades com multi-select de usuários
│   │   ├── aba-usuarios.js   # CRUD de usuários + histórico de pagamentos
│   │   ├── aba-timeline.js   # Placeholder (aba futura)
│   │   └── aba-gerenciar-tarefas.js # Visualização e edição de declarações (subtarefas)
│   ├── css/painel.css        # Tema RK Produções (dark premium)
│   └── commands/             # API REST em PHP
│       ├── _comum/
│       │   ├── resposta.php  # JSON padronizado, debug (só ENV), error handler
│       │   ├── auth.php      # Autenticação: bcrypt, sessão, tokens "lembrar"
│       │   └── .htaccess     # Bloqueia .json/.bak/.old/.env via HTTP
│       ├── conexao/
│       │   ├── conexao.php   # PDO MySQL (credenciais via ENV com fallback)
│       │   └── testar.php    # Health check (requer auth)
│       ├── graficos/graficos.php
│       ├── relatorio/tempo_trabalhado.php
│       ├── status/           # Públicos (usados pelo app desktop)
│       │   ├── atualizar.php # UPSERT de status (heartbeat)
│       │   ├── listar.php    # Status ao vivo de todos os membros
│       │   └── horas_mes.php # Total de horas por membro no mês
│       ├── atividades/       # listar, criar, editar, excluir, alterar_status
│       ├── atividades_subtarefas/ # listar, editar (aba Gerenciar Tarefas)
│       ├── usuarios/         # listar, criar, editar, excluir, atualizar_status, listar_ativos
│       └── pagamentos/       # criar, editar, excluir, listar_por_usuario
├── tests/                    # pytest (banco, atividades, declarações, tempo)
└── .github/workflows/ci.yml  # Pipeline CI (lint, typecheck, test, security)
```

---

## 🗄️ Banco de Dados — Principais Tabelas

| Tabela | Propósito |
|--------|-----------|
| `usuarios` | Cadastro: user_id, nome_exibicao, nivel, valor_hora, chave, status_conta |
| `atividades` | Projetos/tarefas: titulo, dificuldade, estimativa_horas, status |
| `atividades_usuarios` | Vínculo N:N entre atividades e usuários |
| `atividades_subtarefas` | Declarações de horas: referencia_data, titulo, canal_entrega, segundos_gastos, concluida, bloqueada_pagamento |
| `atividades_subtarefas_historico` | Auditoria JSON completa (ação + dados_antes + dados_depois) |
| `usuarios_status_atual` | Estado em tempo real: situacao, atividade, apps_json, ultimo_em |
| `cronometro_apps_intervalos` | Intervalos rastreados por app: inicio_em, fim_em, segundos_em_foco, segundos_segundo_plano |
| `cronometro_foco_janela` | Períodos de foco (janela ativa) — base das timelines individuais |
| `cronometro_relatorios` | Relatórios finalizados de sessão (inclui "Sessão zerada") |
| `registros_tempo` | Heartbeats por sessão: situacao, segundos acumulados |
| `Pagamentos` | Histórico de pagamentos com trava: referencia_inicio, referencia_fim, travado_ate_data |
| `declaracoes_dia_itens` | Itens simples de declaração diária |

---

## 🔌 API Endpoints (painel/commands/)

> **Auth** = requer `verificar_sessao_painel()` · **Público** = acessível sem login (usado pelo app desktop)

| Endpoint | Método | Auth | Descrição |
|----------|--------|:----:|-----------|
| `status/atualizar.php` | POST | Público | UPSERT de status do membro (heartbeat do app.py) |
| `status/listar.php` | GET | Público | Status ao vivo de todos os membros |
| `status/horas_mes.php` | GET | Público | Total de horas por membro no mês |
| `graficos/graficos.php` | POST | Auth | Dados para todos os gráficos ECharts (timelines, donuts, comparativos) |
| `relatorio/tempo_trabalhado.php` | POST | Auth | Relatório detalhado com filtros multi-dimensionais |
| `atividades/listar.php` | GET | Auth | Lista atividades com vínculos de usuários |
| `atividades/criar.php` | POST | Auth | Cria atividade com validação de dificuldade e estimativa |
| `atividades/editar.php` | POST | Auth | Edição parcial + re-atribuição de usuários |
| `atividades/excluir.php` | POST | Auth | Exclui atividade (respeita trava de pagamento) |
| `atividades/alterar_status.php` | POST | Auth | Altera status da atividade (ativa/concluída/arquivada) |
| `atividades_subtarefas/listar.php` | GET | Auth | Lista todas as declarações com filtros de data/usuário |
| `atividades_subtarefas/editar.php` | POST | Auth | Edita declaração existente (respeita trava de pagamento) |
| `usuarios/listar.php` | GET | Auth | Lista membros com valor_hora e status_conta |
| `usuarios/listar_ativos.php` | GET | Auth | Lista apenas membros com conta ativa |
| `usuarios/criar.php` | POST | Auth | Cria membro com chave auto-gerada (`rk_XXXXX`) |
| `usuarios/editar.php` | POST | Auth | Edita dados do membro |
| `usuarios/excluir.php` | POST | Auth | Exclui membro |
| `usuarios/atualizar_status.php` | POST | Auth | Altera status da conta (ativa/inativa/bloqueada) |
| `pagamentos/criar.php` | POST | Auth | Registra pagamento, trava período e limpa registros_tempo |
| `pagamentos/editar.php` | POST | Auth | Edita pagamento existente (data, valor, observação) |
| `pagamentos/excluir.php` | POST | Auth | Exclui pagamento e destrava subtarefas vinculadas |
| `pagamentos/listar_por_usuario.php` | GET | Auth | Histórico de pagamentos por membro |
| `conexao/testar.php` | GET | Auth | Health check da conexão com o banco |

---

## 💳 Sistema de Trava de Pagamento

Mecanismo crítico que garante imutabilidade retroativa após pagamento:

1. **Registrar pagamento:** insere em `Pagamentos` com `data_pagamento`, `valor` e `observacao`. `travado_ate_data` é automaticamente a data do pagamento.
2. **Travamento automático:** `atualizar_bloqueios_por_pagamento()` percorre subtarefas do período e marca `bloqueada_pagamento=1` + `id_pagamento`. No dia exato do pagamento, só trava subtarefas criadas antes do horário do pagamento.
3. **Limpeza de horas:** ao registrar pagamento, remove `registros_tempo` com `criado_em` anterior ao `concluida_em` da última declaração — elimina ruído de horas não declaradas.
4. **Proteção na edição:** `_atividade_tem_movimentacao_em_periodo_travado()` impede editar/excluir atividades com registros em período travado (verifica 3 tabelas: `cronometro_relatorios`, `declaracoes_dia_itens`, `atividades_subtarefas`).
5. **Validação individual:** `_validar_periodo_editavel()` verifica trava por data (dias anteriores) e por subtarefa individual (`bloqueada_pagamento`). `subtarefa_esta_travada()` verifica a flag individual.
6. **Editar/Excluir pagamentos:** admin pode editar ou excluir pagamentos — exclusão destrava automaticamente todas as subtarefas vinculadas.

---

## 📋 Auditoria e Historicidade

Toda alteração em subtarefas é registrada em `atividades_subtarefas_historico`:

- **Ações rastreadas:** `criacao`, `edicao`, `exclusao`, `conclusao`, `reabertura`, `bloqueio_pagamento`
- **Payload JSON:** `dados_antes` + `dados_depois` + `user_id_executor` + `user_id_alvo` + timestamp
- Subtarefas excluídas com histórico são marcadas como deletadas (não removidas fisicamente)

---

## 🔁 CI/CD e Qualidade de Código

Pipeline GitHub Actions (`.github/workflows/ci.yml`) executado em push/PR para `main`:

| Etapa | Ferramenta | Escopo |
|-------|-----------|--------|
| **lint** | `ruff check` | Todo o Python (Python 3.12) |
| **typecheck** | `mypy` | `banco.py`, `atividades.py`, `declaracoes_dia.py` |
| **test** | `pytest` + coverage | `tests/` |
| **security** | `bandit -r` | Todo o Python (exceto tests/build/dist) |

---

## 📈 Evolução do Projeto

> **Legenda:** `[Desktop]` = app.py / Python &nbsp;·&nbsp; `[Web]` = painel PHP/JS &nbsp;·&nbsp; `[App+Web]` = ambos

---

### v7.8 — Fix resumo de pagamento no dashboard `[Web]` (2026-04-11)
- **Card "Pagamento Pendente" corrigido:** agora calcula apenas a soma das linhas com `pago === false`, em vez de usar `total_geral_valor` (que incluía linhas já pagas).
- **`listar_por_usuario.php` mais robusto:** aceita `user_id` via GET, POST ou JSON body (antes lia apenas `$_GET`).

---

### v7.7 — Fix gráficos: períodos fantasma inflavam horas + limpar filtro `[Web]` (2026-04-10)
- **Fix 48h em um dia (períodos fantasma sobrepostos):** `periodos_foco` de apps diferentes com `fim_em = NOW()` se sobrepunham ao serem clipados no dia — somava 3×16h = 48h. Nova função `_segundosFocoMesclados()` mescla intervalos sobrepostos antes de somar (foco é exclusivo: só 1 janela por vez).
- **Fix limpar filtro com membro:** ao clicar "Limpar data", `limparFiltros()` agora reseta imediatamente `_modoTotalPeriodo`, `_teamTimelineIdxDia` e limpa os inputs de data, atualizando o label do timeline antes mesmo do backend responder.

---

### v7.6 — Tempo Declarado 30 dias fixos + coluna Pago `[Web]` (2026-04-09)
- **Tempo Declarado sempre 30 dias:** seção não segue filtro de data — mostra sempre os últimos 30 dias independente do período selecionado nos gráficos.
- **"Valor estimado" → "Pagamento Pendente":** card renomeado com cor amarela para indicar valor pendente.
- **Nova coluna "Pago":** card verde mostrando o total de pagamentos registrados nos últimos 30 dias (soma de todos os usuários).
- **Setas de navegação corrigidas:** sem filtro manual, backend recebe últimos 7 dias (permitindo navegação por seta) enquanto gráficos iniciam no dia de hoje.

### v7.5 — Fix gráficos duplicados, períodos fantasma, consistência de filtros `[Web]` (2026-04-09)
- **Fix "Resumo detalhado por app" duplicado:** `insertAdjacentHTML` adicionava nova seção a cada filtro — agora usa container com ID que é removido e recriado.
- **Períodos fantasma (fim_em NULL):** server-side, `graficos.php` agora usa `usuarios_status_atual.ultimo_em` como fim quando heartbeat > 5 minutos (PC desligou/crash). Não altera dados no banco — compatível com fila offline.
- **Limpeza de fantasmas no JS:** `_limparPeriodosFantasma()` mantém apenas o período aberto mais recente por app — aplicado em todos os 6 gráficos como defesa extra.
- **Fix donut Top Apps 29h:** clipagem correta em todos os cenários (com/sem filtro manual).
- **Fix Foco vs 2.º Plano:** calcula a partir de `periodos_abertos` clipados no dia/período (antes usava `apps_resumo` bruto do backend).
- **Consistência sem filtro = hoje:** ao carregar ou limpar, envia hoje/hoje ao backend (não mais vazio que retornava 7 dias).
- **Fix LIMIT 5000:** query de `cronometro_foco_janela` cortava membros — aumentado para 50000.

### v7.4 — Fix filtros de data, timeline e gráficos `[Web]` (2026-04-09)
- **Padrão mostra dia atual:** sem filtro manual, envia hoje/hoje ao backend.
- **Filtro por período:** ao aplicar datas diferentes, timelines mostram o TOTAL acumulado do período inteiro. Label mostra "DD/MM → DD/MM".
- **Setas bloqueadas com filtro:** navegação dia a dia desabilitada quando há filtro de período ativo. Seta não permite avançar além de hoje.
- **Dias contíguos na navegação:** dias sem atividade aparecem na navegação (sem pular). Gera range do mais antigo até hoje.
- **Linhas de meia-noite:** no modo período, riscos tracejados verticais a cada 00:00 com label DD/MM para separar dias.
- **Limpar mantém campos:** botão "Limpar data" só desativa o filtro — datas e membro permanecem nos campos.
- **Botões reorganizados:** "Aplicar data" e "Limpar data" posicionados junto aos campos de data.
- **Fix timeline travada em ontem:** períodos de foco que cruzam dias agora aparecem em ambos os dias com clipping em 00:00–23:59 (máximo 24h por dia).
- **Todos os gráficos respeitam dia/período:** Tempo por Membro, Top Apps da Equipe e Foco vs 2.º Plano agora calculam a partir dos períodos clipados no dia selecionado (não mais totais brutos do backend).
- **Setas atualizam todos os gráficos:** ao navegar por dia, Tempo por Membro, Top Apps e Foco vs 2.º Plano recarregam junto com as timelines.
- **Fix LIMIT 5000:** query de `cronometro_foco_janela` cortava membros alfabeticamente posteriores — aumentado para 50000.
- **Fix resumo pagamento:** `segundos_declarados_total` agora filtra `bloqueada_pagamento = 0` (antes somava pagas + não pagas).
- **Fix case-sensitive:** tabela `Usuarios` → `usuarios` em `editar.php` e `atualizar_status.php` (MySQL Linux é case-sensitive).
- **Alertas como popup modal:** substituiu banners no topo por modal centralizado com cor por tipo (sucesso/erro/aviso).

### v7.3 — App v2.3: changelog, ordenação datetime, fixes `[Desktop]` (2026-04-08)
- **Versão do app atualizada para v2.3** (título da janela: "Cronômetro v2.3").
- **Changelog na tela de login:** link "v2.3 — ver novidades" na parte inferior abre popup scrollável com histórico completo de versões. Estrutura `HISTORICO_VERSOES` permite adicionar futuras versões facilmente.
- **Ordenação por datetime real:** lista de tarefas e pagamentos agora ordena por `criada_em`/`criado_em` (hora exata), não apenas por data. Pagamentos aparecem na posição cronológica correta entre as subtarefas.
- **Fix erro ao sair:** `_tick_ui` tentava configurar `_btn_tarefas` após destruição dos widgets — adicionado `winfo_exists()` + try/catch.

### v7.2 — Auditoria e correção de 9 bugs `[App+Web]` (2026-04-08)
- **Fix `_finalizar()` (Desktop):** agora bloqueia quando limite de 30h é atingido (antes ignorava o retorno de `_verificar_limite_horas`).
- **Fix `_abrir_tarefas_do_dia()` (Desktop):** avisa sobre limite mas permite abrir (usuário precisa declarar para resolver).
- **Fix ALTER TABLE em transação (Web):** `criar.php` movia o `ALTER TABLE registros_tempo ADD COLUMN id_pagamento` para antes do `beginTransaction()` — MySQL faz commit implícito em DDL, quebrando a atomicidade da transação.
- **Fix registros_tempo reversível (Web):** pagamento agora marca horas com `id_pagamento` via UPDATE em vez de DELETE. Ao excluir pagamento, horas são restauradas (`id_pagamento = NULL`).
- **Fix `in_array` com tipos mistos (Web):** `excluir.php` e `editar.php` usavam comparação loose entre int e string — corrigido com `intval` + `strict=true`.
- **Limite de 2 últimos pagamentos (Web):** apenas os 2 pagamentos mais recentes de cada usuário podem ser editados/excluídos. Pagamentos mais antigos mostram 🔒 na interface.
- **Fallback coluna `id_pagamento` (Web):** 4 queries PHP que filtram `AND id_pagamento IS NULL` agora têm fallback gracioso (try/catch) para bancos antigos sem a coluna.
- **Fix `concluir_subtarefa` (Desktop):** não marca mais como paga quando `criada_em` é NULL — antes assumia `marcar=True` por padrão, agora só marca se `criada_em <= dt_pagamento`.
- **Queries filtram horas pagas (Web):** `listar.php`, `editar.php`, `tempo_trabalhado.php` e `horas_mes.php` excluem registros com `id_pagamento IS NOT NULL` do total trabalhado.

### v7.1 — Gestão em página, limite 30h, limpeza no pagamento `[App+Web]` (2026-04-08)
- **Gestão de usuário em página completa:** modal substituído por seção SPA com layout em 2 colunas — dados do usuário e resumo à esquerda, pagamentos e tarefas declaradas à direita. Botão "← Voltar" retorna à lista de usuários.
- **Tabela de tarefas declaradas na gestão:** lista todas as subtarefas do usuário com botão "Editar" que abre o mesmo modal de Gerenciar Tarefas. Tarefas bloqueadas por pagamento têm botão desabilitado. Recarrega automaticamente após edição.
- **Formulário de pagamento simplificado:** removidos campos "Referência início", "Referência fim" e "Travado até". Ficaram apenas: Data do pagamento, Valor e Observação.
- **Tabela de pagamentos simplificada:** removidas colunas "Referência" e "Travado até" — ficaram Data, Valor, Obs e Ações.
- **Limite de 30h não declaradas (Desktop):** acima de 20h, aviso ao clicar em qualquer botão; ao atingir 30h, para de acumular e bloqueia ações até declarar. Constantes `LIMITE_HORAS_AVISO` (20h) e `LIMITE_HORAS_MAXIMO` (30h).
- **Limpeza de `registros_tempo` no pagamento:** `criar.php` remove registros anteriores ao `concluida_em` da última subtarefa declarada — elimina ruído de horas não declaradas.
- **Cache-buster `?v=7`:** adicionado a todos os assets JS e CSS para evitar cache do navegador.
- **Fix aspas Unicode:** aspas tipográficas (`"` `"`) no HTML substituídas por ASCII — corrigiu section invisível no DOM.

### v7.0 — Tarefas sem filtro de data, pagamentos na lista, trava por hora `[App+Web]` (2026-04-08)
- **Listagem de tarefas sem filtro de data:** `listar_subtarefas_do_dia` agora aceita `referencia_data=None` — mostra todas as tarefas da atividade em vez de só as do dia.
- **Resumo acumulado:** `obter_resumo_do_dia` e `obter_segundos_declarados_do_dia` também aceitam `referencia_data=None` — Trabalhado/Declarado somam todas as datas.
- **Pagamentos na lista de tarefas (Desktop):** pagamentos aparecem como linhas verdes intercaladas por data, com valor formatado em R$. Ordenação: data desc, pagamentos acima de subtarefas no mesmo dia.
- **Coluna "Pagamento":** renomeada de "Bloqueio" — mostra "Pago" ou vazio.
- **Trava por hora:** `data_esta_travada` agora usa `<` (estritamente anterior) — no dia exato do pagamento, novas subtarefas ficam livres. `subtarefa_esta_travada` verifica flag individual `bloqueada_pagamento`. `concluir_subtarefa` compara `criada_em` com `criado_em` do pagamento antes de travar.
- **Editar/Excluir pagamentos (Web):** novos endpoints `editar.php` e `excluir.php`. Exclusão destrava subtarefas vinculadas. Botões na tabela de histórico.
- **Ordenação de tarefas:** mais recentes no topo (`referencia_data DESC, criada_em DESC`).

### v6.9 — Fix deadlock loop monitor: banco fora do lock `[Desktop]` (2026-04-08)
- **Raiz do travamento ao Pausar/Retomar:** o loop interno do `MonitorDeUso` executava todas as operações de banco (`_atualizar_status_atual_locked`, `_inserir_evento`, `_fechar_foco`, `_abrir_foco`, `_atualizar_intervalos_apps_locked`, `_tentar_flush_fila_offline`) dentro do `with self._trava:`. Qualquer query lenta (reconexão após queda, flush da fila offline) bloqueava o lock por segundos — Pausar/Retomar ficavam presos esperando.
- **Correção:** o `with self._trava:` agora só atualiza estado em memória e marca flags. Todas as queries de banco executam **após** o lock ser liberado. Lock liberado em microssegundos; banco nunca bloqueia a UI.

### v6.8 — Auto-login + tela de login corrigida `[Desktop]` (2026-04-08)
- **Auto-login:** na inicialização, se há credenciais salvas, o formulário de login é exibido com campos preenchidos e o login é disparado automaticamente em background — usuário vai direto à tela principal sem digitar nada.
- **Falha no auto-login:** se offline ou credenciais inválidas, o formulário permanece visível com mensagem de erro amigável ("Sem conexão com o servidor." em vermelho).
- **Sair:** mantém os campos preenchidos para facilitar re-login manual.
- **Erro de conexão no login:** mensagem raw do pymysql substituída por "Sem conexão com o servidor." — sem texto cortado ou técnico na tela.

### v6.7 — Botão Tarefas desabilitado offline + aviso amarelo `[Desktop]` (2026-04-08)
- **Botão "Tarefas" desabilitado:** quando `_offline_notificado = True`, o botão é desabilitado automaticamente pelo `_tick_ui` (a cada 80ms) e reabilitado quando a conexão volta.
- **Guard em `_abrir_tarefas_do_dia`:** mesmo com botão desabilitado, clique programático exibe popup "Você precisa estar conectado à internet para acessar as tarefas."
- **Aviso amarelo âmbar:** substituiu o texto vermelho com erro raw — quando offline mostra "⚠ Perdemos a conexão com o servidor, provavelmente você está sem internet." com `wraplength=380`; some automaticamente ao reconectar.

### v6.6 — Fila offline + notificações Windows de conexão `[Desktop]` (2026-04-08)
- **Fila offline (`~/.cronometro_leve_fila_offline.json`):** heartbeats e eventos de ocioso que falham por queda de conexão são salvos localmente com timestamp original. Re-enviados em ordem quando o banco volta (a cada 60s no heartbeat).
- **Detecção de queda/retorno a cada 5s:** `_atualizar_status_atual_locked` detecta falha → `_offline_notificado = True`; detecta sucesso → `_offline_notificado = False`. Botão e aviso respondem em até 5s.
- **Popup Windows ao cair:** `ctypes.MessageBoxW` com `MB_SETFOREGROUND` abre à frente de todas as janelas — 1 vez ao cair, não repete enquanto offline.
- **Popup Windows ao reconectar:** exibe quantidade de eventos re-enviados da fila.

### v6.5 — Fix travamento GUI Desktop + modo debug `[Desktop]` (2026-04-07)
- **Iniciar/Pausar/Retomar/Zerar movidos para thread background:** antes, clicar nos botões executava INSERT/UPDATE no banco direto na thread principal do Tkinter — se o banco estivesse lento, a janela congelava. Método `_rodar_em_background()` criado na classe `App` (separado de `_executar_em_background()` que pertence a `MonitorDeUso`) usa `threading.Thread(daemon=True)` + `self.after(0, ...)` para retornar resultado na thread principal.
- **Modo desenvolvimento (debug):** `_verificar_atualizacao()` agora tem guard `if not getattr(sys, "frozen", False): return` — ao rodar via `python app.py` o auto-update é ignorado; só executa quando compilado como `.exe` pelo PyInstaller.

### v6.4 — Fix visual selects + unificação Dashboard + melhorias Relatório `[Web]` (2026-04-07)
- **Fix dropdown options:** regra CSS global `select option { background-color: #1a1f2e; color: #e2e8f0 }` aplicada a todos os `<select>` do painel — antes o fundo branco com texto branco tornava as opções ilegíveis em Relatório, Gerenciar Tarefas e modais.

### v6.3 — Melhorias na aba Relatório `[Web]` (2026-04-07)
- **Filtro por membro:** select com todos os membros ativos; backend aceita `user_id` para filtrar um membro específico.
- **Coluna "Trabalhado":** horas reais monitoradas pelo app (de `registros_tempo`) exibidas ao lado do declarado — permite comparar visualmente.
- **Coluna "Status":** badge **Pago** (verde) ou **Pendente** (amarelo) por dia/membro — baseado em `bloqueada_pagamento` das `atividades_subtarefas`.
- **Indicador de divergência:** badge ⚠ vermelho quando declarado excede trabalhado em mais de 10% — linha com fundo vermelho sutil para facilitar identificação.
- **Export CSV:** botão "CSV" exporta todas as linhas com separador `;` e BOM UTF-8 (compatível com Excel). Colunas: data, membro, trabalhado, declarado, declarações, pago, divergente, R$/hora, valor.
- **Fix `listar.php` (atividades):** substituído `JSON_ARRAYAGG` (inexistente no MariaDB 10.4) por `GROUP_CONCAT` — aba Atividades voltou a funcionar.

### v6.2 — Unificação Dashboard + Gráficos `[Web]` (2026-04-07)
- **Dashboard unificado:** abas Dashboard e Gráficos fundidas em uma única tela — tabela "Usuários (resumo)" removida, conteúdo dos gráficos (ECharts) renderizado diretamente no Dashboard.
- **Tabela "Visão Geral da Equipe" enriquecida:** adicionadas colunas "Conta" (Ativa/Inativa), "R$/hora" e botão "Gestão" (abre modal de gestão do membro).
- **Botões de ação rápida:** "+ Adicionar Usuário" e "+ Nova Atividade" no topo do Dashboard.
- **Navbar simplificada:** link "Gráficos" removido (5 abas em vez de 6).
- **Modal Nova Atividade:** movido para fora do `<main>` (antes de `</body>`) para evitar conflito de z-index.
- **`valor_hora` no backend:** campo adicionado à query de `graficos.php` e ao mapa de usuários.

### v6.1 — Fix editar tarefa, trava pagamento, painel de horas `[Web]` (2026-04-07)
- **Fix "Falha ao editar tarefa":** FK violation corrigida — `user_id_executor` usa o dono da tarefa em vez de `'painel_adm'`.
- **Trava de pagamento funcional:** `criar.php` agora executa `UPDATE bloqueada_pagamento=1` em todas as subtarefas com `referencia_data <= travado_ate_data`. Histórico de bloqueio registrado em `atividades_subtarefas_historico`.
- **Painel de horas no modal edição:** exibe Total trabalhado / Declarado / Disponível (acumulado todas as datas) ao editar uma declaração.
- **Validação de horas:** backend recusa tempo que exceda o total trabalhado acumulado — retorna mensagem com horas disponíveis.
- **Resumo para pagamento:** card na gestão do usuário mostrando Trabalhado / Declarado / Não declarado / A pagar (horas não pagas × R$/hora).

### v6.0 — Performance, bloqueio de login e fix Docker `[Web]` (2026-04-07)
- **Bloqueio de login:** após 2 tentativas incorretas, login bloqueado por 5 minutos. Contagem armazenada em `.tentativas.json` (protegido via `.htaccess`). Botão "Entrar" desabilitado durante bloqueio com mensagem de tempo restante.
- **Performance — aba Gráficos:** HTML dos charts só é reconstruído ao trocar de modo (individual ↔ equipe), não a cada filtro; cache de cores `_obterCorApp` (sem `localStorage` em loop); resize listener único no `DOMContentLoaded`; shimmer com `will-change: transform` e removido pós-render; event delegation na legenda de apps.
- **Dockerfile:** `ServerName localhost` para suprimir warning AH00558; diretório `/var/lib/php/sessions` criado com permissão para volume persistente.
- **Correção timeline:** `_cliparSobreposicoes()` corta barras onde a próxima começa — sem sobreposição nas 3 timelines.
- **Fix "Falha ao editar tarefa":** `editar.php` usava `'painel_adm'` como `user_id_executor` no histórico, mas esse user não existe na tabela `usuarios` — FK violation. Corrigido para usar o `user_id` do dono da tarefa.
- **Painel de horas no modal:** ao editar declaração, exibe Trabalhado / Declarado / Disponível no dia para o membro. Dados vêm de `registros_tempo` + soma das `atividades_subtarefas`.
- **Validação de horas:** `editar.php` recusa tempo que exceda o total trabalhado acumulado — retorna mensagem com horas disponíveis.
- **Fix trava de pagamento:** `criar.php` agora executa `UPDATE atividades_subtarefas SET bloqueada_pagamento=1` em todas as subtarefas com `referencia_data <= travado_ate_data` — antes o pagamento era registrado mas nenhuma tarefa era travada. Histórico de bloqueio registrado.

### v5.9 — Hardening de segurança do painel `[Web]` (2026-04-07)
- **Debug restrito a ENV:** `debug_ativo()` em `resposta.php` agora aceita apenas `APP_DEBUG=1` via variável de ambiente — removidos gatilhos via querystring (`?debug=1`) e header (`X-Debug: 1`) que permitiam a qualquer visitante expor caminhos internos do servidor em caso de erro.
- **`.tokens.json` protegido:** `.htaccess` adicionado em `commands/_comum/` bloqueando acesso HTTP a arquivos `.json`, `.bak`, `.old` e `.env` — impede roubo de tokens de sessão persistente.
- **`testar.php` protegido:** endpoint `conexao/testar.php` agora exige autenticação (`verificar_sessao_painel()`) — antes era público e expunha status do banco e mensagens de erro do PDO.

### v5.8 — Auditoria e correções de segurança do painel `[Web]` (2026-04-07)
- `graficos.php` estava sem autenticação — corrigido: `require_once auth.php` + `verificar_sessao_painel()` adicionados ao início do arquivo.
- Pasta `logs/` protegida via `.htaccess` (`Require all denied`) — impede acesso HTTP a arquivos de log com stack traces e dados sensíveis.
- `.gitignore` atualizado: ignora apenas `*.log` dentro de `painel/logs/`, mantendo o `.htaccess` rastreado.

### v5.7 — Sistema de autenticação do painel administrativo `[Web]` (2026-04-07)
- `login.php` criado: tela standalone com design RK Produções (dark card, gradiente de fundo, barra de acento azul).
- `logout.php` criado: destrói sessão e cookie, redireciona para login.
- `commands/_comum/auth.php` criado: toda a lógica de autenticação — bcrypt hash, sessão PHP, tokens de "permanecer logado".
- Credenciais configuradas em `auth.php` — senha armazenada como bcrypt (`PASSWORD_BCRYPT`), nunca em texto puro.
- "Permanecer logado" (30 dias): gera token de 64 caracteres aleatórios (`bin2hex(random_bytes(32))`), salvo em `.tokens.json` (ignorado pelo git) com TTL de 30 dias.
- `index.php`: verifica sessão no topo — redireciona para `login.php` se não autenticado.
- Botão "Sair" adicionado na navbar ao lado do "Baixar App".
- 17 endpoints protegidos com `verificar_sessao_painel()`: todos em `usuarios/`, `atividades/`, `atividades_subtarefas/`, `pagamentos/`, `relatorio/`, `graficos/`.
- Endpoints públicos mantidos (necessários para o app desktop): `status/atualizar.php`, `status/listar.php`, `status/horas_mes.php`, `baixar_app.php`. (`conexao/testar.php` protegido na v5.9)

### v5.6 — Auto-update silencioso com janela dedicada `[Desktop]` (2026-04-07)
- Auto-update não exibe mais popup de confirmação — baixa e reinicia silenciosamente.
- `URL_ATUALIZACAO` migrado para GitHub raw (`rafaelkolaias-lang/Cltcron/main/painel/downloads/CronometroLeve.exe`) — deploy via git, sem servidor separado.
- Ao detectar atualização: janela principal é substituída por card `320x320` (mesma linguagem do login) com barra azul, ícone ⟳ e texto centralizado.
- `WM_DELETE_WINDOW` bloqueado durante download — usuário não pode fechar.
- Encerramento via `os._exit(0)` agendado com `self.after(0, ...)` na thread principal — garante que o processo fecha de fato após lançar o novo exe.

### v5.5 — Redesign completo do GUI Desktop (dark theme) `[Desktop]` (2026-04-07)
- GUI totalmente redesenhado em tema escuro (`#111111`) com paleta: verde Iniciar, azul Pausar/Retomar, vermelho Excluir.
- Tela de login redesenhada com card layout, barra de acento azul e janela quadrada `480x520`.
- Formulário "Declarar Tarefa" redesenhado: card com barra de acento, labels uppercase, separador e rodapé dedicado.
- Ícone da janela aplicado via `logo.png` (RK Produções, 636×636 RGBA) usando Pillow `ImageTk.PhotoImage`.
- Overlay "Saindo, aguarde…" ao fechar; texto "Carregando…" em verde em todas as ações de botão.
- Bloqueio de tarefa com nome duplicado: aviso ao usuário antes de salvar.
- Corrigido: `deve_concluir` lido antes de `var_texto_botao.set("Salvando…")` — "Salvar e Concluir" não ignorava mais a conclusão.
- Corrigido: crash `_atualizar_cor_status` em widget destruído após transição de tela (guard `winfo_exists()`).

### v5.4 — Fix duplicação de tarefa ao falhar Salvar e Concluir `[Desktop]` (2026-04-07)
- `JanelaSubtarefas`: botão Salvar desabilitado imediatamente (antes da validação) + `update_idletasks()` — ignora cliques em fila.
- `_id_subtarefa_criada_nesta_janela` armazena o ID já criado; na segunda tentativa reutiliza o mesmo registro em vez de inserir um novo.

### v5.3 — Aba Gerenciar Tarefas `[Web]` (2026-04-07)
- Nova aba "Gerenciar Tarefas" entre Atividades e Gráficos no menu.
- Filtros: data início/fim, membro, atividade, canal de entrega.
- Tabela com todas as declarações (`atividades_subtarefas`): data, membro, atividade, tarefa, tempo, canal, status.
- Edição via modal: título, tempo (aceita `1h30m`, `90m`, `hh:mm:ss`), status, canal, observação.
- Trava de pagamento respeitada: tarefas bloqueadas mostram 🔒 e botão Editar desabilitado.
- Backend: `commands/atividades_subtarefas/listar.php` + `editar.php` com registro no histórico.

### v5.2 — UI não trava durante login e atualização `[Desktop]` (2026-04-07)
- Login (`autenticar_usuario`) e verificação de atualização (`urlopen`/`urlretrieve`) movidos para threads background.
- Janela permanece responsiva (move, minimiza) durante todas as operações de rede e banco.
- Resultados retornam à UI via `self.after(0, ...)` — padrão correto para Tkinter multithread.

### v5.1 — Rollback e feedback no auto-update `[Desktop]` (2026-04-06)
- `_verificar_atualizacao()` agora faz rollback automático se a substituição do exe falhar: restaura o `.bak` para a posição original.
- Erros de atualização exibem mensagem no status em vez de serem silenciados.

### v5.0 — Correção definitiva das setas de navegação `[Web]` (2026-04-06)
- `obterFiltros()` sempre lê os inputs de data (padrão 7 dias), sem mais forçar "só hoje".
- Na carga inicial a API já recebe o range completo → múltiplos dias em `_teamTimelineDias` → botões ←/→ funcionam imediatamente.

### v4.9 — Auto-update + Timeout de Zumbi `[App+Web]` (2026-04-06)
- **`[Desktop]` Auto-Update:** `_verificar_atualizacao()` em `app.py` faz HEAD request ao servidor; se `Content-Length` diferir do exe local, baixa, substitui via renomeação e reinicia automaticamente.
- **`[Web]` Timeout de Zumbi:** `graficos.php` força `status_atual = 'pausado'` se o último heartbeat tiver mais de 3 minutos — elimina "fantasmas" trabalhando no painel.
- **`[Web]` Setas de Navegação:** `_atualizarLabelTeamTimeline` desabilita explicitamente os botões quando `_teamTimelineDias` está vazio.

### v4.8 — Espessura máxima das barras `[Web]` (2026-04-06)
- Barras limitadas a 18px de altura em todas as timelines — elimina aspecto "grosso" na visão individual.

### v4.7 — Eixo X data-driven nas timelines `[Web]` (2026-04-06)
- Eixo X calculado com base no intervalo real dos dados ± 30 min de padding, em vez de 00:00–23:59 fixo.
- `minInterval: 15 min`, `maxInterval: 2h` para densidade de labels proporcional ao zoom.

### v4.6 — Controle único de navegação de datas `[Web]` (2026-04-06)
- Na visão individual, dois conjuntos de ←/→ substituídos por um único controle acima das duas timelines.
- `_teamTimelineDias` inclui dias de `periodos_abertos` + `periodos_foco` — nenhum dia fica de fora.
- Navegar entre dias atualiza simultaneamente: Timeline em Foco, Timeline Geral e Top Apps (donut).

### v4.5 — Segunda timeline: Todos os Apps Abertos `[Web]` (2026-04-06)
- Visão individual agora exibe duas timelines separadas: "Em Foco" e "Todos os Apps Abertos (foco + 2.º plano)".
- Dados da segunda timeline vêm de `periodos_abertos` (`cronometro_apps_intervalos`).

### v4.4 — Correções visuais: dropdown + shimmer `[Web]` (2026-04-06)
- Opções do `<select>` de Membro ganham `background-color: #1a1f2e` e `color: #e2e8f0` — legíveis em todos os OS.
- Shimmer da timeline: opacidade reduzida (pico 0.03) e `z-index: 0` — fica atrás das barras do canvas.

### v4.3 — Restaurar gráfico "Foco vs 2.º plano" `[Web]` (2026-04-06)
- Visão individual volta a mostrar o gráfico de barras "Todos os programas — foco vs 2.º plano" (`chartBarrasApps`) ao lado do donut.

### v4.2 — Unificação da visão individual com a visão de equipe `[Web]` (2026-04-06)
- `montarDetalheUsuario` sempre delega para `montarVisaoGeralTodosUsuarios` — uma única lógica de renderização para 1 membro ou N membros.
- Seletor "Usuários" (multi-select) removido; seletor "Detalhe" passa a ser o filtro principal enviado à API.

### v4.1 — Filtros integrados no card "Detalhe do Membro" `[Web]` (2026-04-06)
- Card de filtros do topo removido — datas, seletor, Aplicar, Limpar e 🎨 Cores integrados no cabeçalho do card principal.

### v4.0 — Terminologia: "Editor" → "Membro/Equipe" `[Web]` (2026-04-06)
- Termo "Editor" removido de toda a interface — substituído por "Membro", "Equipe" ou "Membro da equipe".
- IDs HTML internos mantidos para não quebrar referências JS existentes.

### v3.9 — Sincronização Top Apps ↔ Timeline `[Web]` (2026-04-06)
- Top Apps agora agrega `periodos_foco` filtrado pelo dia exibido na timeline — elimina divergência de horas.
- Navegar entre dias (←/→) rerenderiza o donut automaticamente.
- Filtro de app por clique aplica também na timeline (sem re-fetch).

### v3.8 — Filtro interativo por clique e legenda lateral `[Web]` (2026-04-06)
- Select de apps removido; filtro feito por clique nas fatias do donut ou nos itens da legenda lateral.
- Legenda lateral scrollável com dot colorido ao lado de cada rosca.
- `alternarFiltroApp` adiciona/remove app de `FILTROS_APPS_ATIVOS` e recarrega gráficos.

### v3.7 — Títulos dinâmicos nos gráficos `[Web]` (2026-04-06)
- Ao filtrar um único membro, títulos exibem o nome ("Visão Geral: Rafael") em vez de "da equipe".
- Dot de cor na tabela de apps usa `_obterCorApp` — consistente em todos os gráficos.

### v3.6 — Personalização de cores de apps `[Web]` (2026-04-06)
- Modal 🎨 Cores com `<input type="color">` por app — salvo no `localStorage`, persiste entre sessões.
- `_obterCorApp` unifica cores em todos os gráficos (prioridade: customizada → mapa fixo → hash).
- Auto-refresh (`setInterval 30s`) removido definitivamente.

### v3.5 — Refinamento visual da timeline `[Web]` (2026-04-06)
- Shimmer mais sutil (opacidade reduzida, animação 7s).
- Gradientes internos das barras removidos — cores sólidas por app.
- `MAPA_CORES_APPS` implementado: cor fixa por software em todo o sistema.

### v3.4 — Shimmer animado na timeline `[Web]` (2026-04-06)
- Pseudo-elemento CSS percorre a timeline da esquerda para a direita em 3.2s — simula luz passando pelas barras.
- Barras com `LinearGradient` ECharts (brilho central).

### v3.3 — Favicon RK `[Web]` (2026-04-06)
- `painel/img/favicon.svg` — ícone play vermelho + "RK" na aba do browser.

### v3.2 — Identidade Visual RK Produções `[Web]` (2026-04-06)
- Plus Jakarta Sans, fundo `#050811`, blobs radiais pink/roxo/laranja, glassmorphism nos cards.
- Logo navbar via CSS puro (play vermelho + "RK PRODUÇÕES").
- PALETA ECharts atualizada (15 cores no espectro RK).
- Scrollbar fina, transições `.18s`, glow nos botões, underline gradiente no link ativo.

### v3.1 — Navbar superior + remoção da sidebar `[Web]` (2026-04-06)
- Sidebar lateral substituída por `<nav class="navbar-grafite sticky-top">`.
- Submenus hover CSS puro: Usuários → "+ Adicionar"; Atividades → "+ Nova Atividade".
- Fix: padding elimina gap entre link e submenu (submenu não sumia mais ao mover o cursor).

### v3.0 — Botão Recarregar fixo + remoção do auto-refresh `[Web]` (2026-04-06)
- Botão "Recarregar" com `position: fixed` — acessível de qualquer aba e posição de scroll.
- Timer de 30s e botão "Auto: off/on" eliminados — zero requisições automáticas.

### v2.9 — Visão geral da equipe na aba Gráficos `[Web]` (2026-04-06)
- Selecionando "Todos" exibe: comparativo de tempo por membro, top apps da equipe (rosca) e timeline Gantt multi-membro.
- Títulos dinâmicos quando apenas 1 membro está filtrado.

### v2.8 — Preservação de horas ao "Zerar Cronômetro" `[Desktop]` (2026-04-05)
- `zerar_sessao()` insere em `cronometro_relatorios` com `relatorio = "Sessão zerada"` antes de descartar o estado local.
- Snapshots capturados dentro do lock — tempo fica disponível para declaração posterior.

### v2.7 — Executável standalone `[Desktop]` (2026-04-05)
- `CronometroLeve.exe` gerado via PyInstaller 6.19 (~14 MB, `--onefile`, sem console).
- Roda em qualquer Windows sem Python instalado. `.exe` excluído do repositório via `.gitignore`.

### v2.6 — "Salvar e Concluir" sempre conclui a tarefa `[Desktop]` (2026-04-05)
- `concluir_subtarefa` em `declaracoes_dia.py` aceita `segundos_gastos = 0` — remoção da restrição anterior.
- `salvar()` em `app.py` usa `deve_concluir = var_texto_botao.get() == "Salvar e Concluir"` — conclusão orientada pela intenção do botão.

### v2.5 — Ajustes visuais do painel `[Web]` (2026-04-05)
- Opções de `<select>` nos modais com `color: #000` e `background: #fff` — legíveis em todos os OS.
- `input::placeholder` e `textarea::placeholder` com `color: rgba(255,255,255,.5)` — contraste sobre fundo grafite.

### v2.4 — Estabilidade e segurança `[App+Web]` (2026-04-05)
- **`[Desktop]` Thread Safety:** `pausar`, `retomar` e `zerar_sessao` capturam IDs snapshottados dentro do lock antes de liberá-lo.
- **`[Desktop]` TclError Geral:** `_executar_em_background` verifica `winfo_exists()` antes de qualquer callback.
- **`[Desktop]` Eventos Redundantes:** `pausar()` com guard `_situacao_manual == "pausado"` — sem eventos duplicados.
- **`[Desktop]` Credenciais:** `banco.py` migrado para `os.environ.get()` com fallback.
- **`[Web]` ECharts resize:** `resizarGraficos()` chamada ao trocar para aba de Gráficos.

### v2.3 — Simplificação da UI desktop `[Desktop]` (2026-04-05)
- Botão único de controle: Iniciar / Pausar / Retomar em um único `ttk.Button` dinâmico.
- "Zerar Cronômetro" para a sessão sem criar relatório prematuro.
- "Nova subtarefa" → "Declarar Tarefa"; rótulo interno "Subtarefa" → "Tarefa".
- Máscara de tempo calculadora (dígitos entram pela direita); valor padrão `00:00:00`.
- Campo "Canal" substituído por `Combobox readonly` pré-selecionado com a atividade ativa.
- Seletor "Atividade:" removido da tela principal — auto-seleção da primeira atividade.
- Funcionalidade "Reabrir subtarefa" removida.
- Fix `_tick_ui`: contadores internos zerados em `zerar_sessao()` para exibir `00:00:00` corretamente.

### v2.2 — Performance e base do sistema `[App+Web]` (inicial)
- Debouncing de salvamento → redução de 95% no I/O de disco.
- UPSERT (`ON DUPLICATE KEY UPDATE`) para idempotência nos heartbeats.
- Cache de nomes de processos com TTL 60s.
- ECharts substituindo biblioteca anterior.

---

## 🎨 Identidade Visual (RK Produções)

O painel administrativo foi estilizado conforme a marca **RK Produções**, utilizando um design arrojado e de alto contraste:

- **Primária**: Vermelho Cinematográfico (`#e62117`) para o Play Button da marca.
- **Contraste**: Espectro de cores vibrantes (Pink, Orange, Yellow, Purple) para representar a flexibilidade e o dinamismo da produção.
- **Estética**: Cartões com desfoque de fundo (backdrop-filter) e bordas luminosas progressivas.

---

*Última atualização: 2026-04-11 — v7.8*
