# gemini-design.md — Guia de redesign do painel web (para o Gemini)

> **Quem é você nesse fluxo:** você (Gemini) é o **planejador de DESIGN/FRONT-END**.
> Sua única entrega é um **planejamento de redesign visual** escrito no arquivo
> `!executar.md` deste projeto, na seção **"Tarefas Claude 1"**, em tarefas numeradas
> com `Status: PENDENTE` — quem executa o código é o Claude.
> **Você NÃO altera nenhum arquivo do projeto além de `!executar.md`** (e, se
> precisar, `!projeto.md`). Nada de backend, banco, endpoints ou lógica de
> negócio — isso é responsabilidade do Claude e está fora do seu escopo.
> Se faltar informação, **pergunte ao usuário antes** de registrar no `!executar.md`.
> Quando houver mais de um caminho de design, apresente as opções com as
> diferenças claras e deixe o usuário escolher.

---

## 1. O que é a plataforma

Painel web administrativo do sistema **Cronômetro** (RK Produções): monitora a
produtividade de uma equipe de editores de vídeo. Um app desktop (fora do escopo)
cronometra as horas de cada membro; o painel web é onde o **admin**:

- acompanha em tempo real quem está trabalhando/pausado/ocioso;
- vê gráficos de atividade, foco por aplicativo e timelines;
- gerencia membros (usuários), canais (de YouTube), tarefas declaradas e pagamentos;
- audita fraude (apps suspeitos, input sintético);
- gerencia credenciais/API keys cifradas dos membros;
- configura uploads obrigatórios no MEGA (pastas de vídeo por canal).

Usuário do painel: **1 admin** (não é produto público; é ferramenta interna diária).
Emoção desejada: controle, clareza, agilidade. Hoje o painel funciona, mas está
**visualmente poluído, denso e pouco intuitivo** — o objetivo do redesign é
**moderno, limpo, intuitivo, menos bagunçado**, mantendo TODAS as informações
e funcionalidades existentes.

## 2. Stack e restrições técnicas (INEGOCIÁVEIS no plano)

- **PHP multipágina** (sem SPA, sem React/Vue/build step). Cada página inclui
  partials compartilhados: `painel/_layout/topo.php` (head + topbar + sidebar),
  `fim_conteudo.php`, `rodape.php` (scripts).
- **Bootstrap 5.3** (dark) + **CSS próprio** em `painel/css/painel.css` (~870 linhas,
  tema "grafite" com gradiente RK) + **JavaScript vanilla** em arquivos por página
  (`painel/js/aba-*.js`). Gráficos em **ECharts** (e Chart.js carregado na base).
- O redesign deve ser alcançável **editando HTML/CSS/JS existentes** — pode
  reescrever o CSS inteiro, trocar componentes, criar novos partials; não pode
  exigir framework novo nem npm build.
- Os **endpoints PHP e os dados retornados não mudam**. Os `id=` de elementos que
  o JS usa podem mudar, desde que a tarefa liste o de→para (o Claude ajusta o JS).
- Tema **dark** continua (é a identidade). Identidade "RK Produções" com gradiente
  (variáveis CSS já existentes: `--rk-1 #ff1f5b`, `--rk-2 #ff6b1f`, `--rk-3 #ffd600`,
  `--rk-4 #a800ff`, `--rk-5 #1a1aff`).
- Responsivo: uso principal é desktop, mas não pode quebrar em tela pequena.

## 3. Design system atual (o que existe hoje)

- Cartões: `.cartao-grafite` (fundo rgba escuro, borda 1px suave, radius 16px, blur).
- Tabelas: `table-dark table-borderless` + `.tabela-suave` (hover) +
  `.cabecalho-tabela-sticky`. **Quase toda tela é uma tabela densa** — essa é a
  maior fonte de "bagunça".
- Cards de métrica: `.card-metrica` (rótulo uppercase pequeno + valor grande).
- Badges bootstrap (bg-success/warning/danger/secondary) + `.badge-suave`.
- Menu lateral fixo (sidebar) com nav-pills; topbar com título da página.
- Botões: `btn-light` (ação primária), `btn-outline-light` (secundária), com glow
  no hover.
- Referência de direção já aprovada pelo usuário: a página **MEGA · Campos de
  upload** (`mega-campos.php`) foi recém-redesenhada com **abas internas (pills)**,
  **cards por canal** com cabeçalho e ações próprias, **estados vazios orientados**
  (passo a passo 1-2-3), **badges coloridos por tipo** e **modal guiado em 2 passos
  com resumo ao vivo**. Esse é o nível de intuitividade desejado nas demais telas.

## 4. Mapa das páginas (todas em `painel/`)

| Página | JS principal | O que tem hoje |
|---|---|---|
| `login.php` | — | Login simples (usuário+senha, "permanecer logado"). |
| `index.php` — **Dashboard** | `painel.js` + `aba-graficos.js` (~2080 linhas) + `aba-auditoria.js` | Home. Seções: **"Monitoramento de Atividade"** (status ao vivo de cada membro: trabalhando/pausado/ocioso, app em foco), **"Visão Geral da Equipe"** (cards Membros/Trabalhando/Pausados/Ociosos + donut), **"Top apps da equipe (foco agregado)"**, **"Timeline da equipe"** (ECharts, barras por membro/hora), **"Tempo Declarado"** (cards Período/Trabalhado/Total declarado/Pago/Pagamento Pendente + comparativos). Atalhos "+ Adicionar Usuário" e "+ Adicionar Canal" (modais). Clique num membro → navega pra Gestão do Usuário. |
| `usuarios.php` — **Usuários + Gestão** | `aba-usuarios.js` + `aba-credenciais.js` + `aba-auditoria.js` + `aba-gerenciar-tarefas.js` | Lista de membros (tabela CRUD: nome, nível, R$/h, status da conta, chave, PIX, ocultar do dashboard). Sub-tela **Gestão do Usuário** (deep-link `?user=<id>`): cards de resumo (Trabalhado/Declarado/Não declarado/Ocioso/A pagar/Pago), filtro TUDO/30 dias, gráficos individuais (timeline por dia com setas ‹ ›, donut de apps, foco por janela), alertas de auditoria, pagamentos (criar/editar/excluir), tarefas declaradas, credenciais do usuário. É a tela mais densa e mais usada. |
| `canal.php` — **Canais** | `aba-atividades.js` | CRUD de canais em TABELA (título, descrição, status via `<select>` inline, usuários vinculados, ações). Modal "Novo Canal" (título, descrição, status, vincular usuários). **Ver requisitos específicos na seção 6 — o usuário já decidiu que aqui vira blocos/cards.** |
| `gerenciar-tarefas.php` — **Gerenciar Tarefas** | `aba-gerenciar-tarefas.js` | Tabela global paginada de tarefas declaradas (subtarefas) com filtros (usuário, canal, status, busca, período) e modal de edição. |
| `relatorio.php` — **Relatório** | `aba-relatorio.js` | Relatório agregado de tempo trabalhado por período com export CSV. |
| `credenciais.php` — **Credenciais e APIs** | `aba-credenciais.js` | Modelos de credenciais (ChatGPT, Gemini, etc.), valores cifrados por usuário, APIs globais, modais de gestão. |
| `auditoria.php` — **Auditoria** | `aba-auditoria.js` | Usuários com flag 🚩 (input automatizado/apps suspeitos, últimos 7 dias) + CRUD de apps suspeitos + modal. |
| `log.php` — **Log** | `aba-log-atividades.js` | Log geral de ações do servidor com filtros, paginação e modal de detalhe (JSON antes/depois). |
| `mega.php` — **MEGA · Pastas lógicas** | `aba-mega.js` | Tabela de pastas de vídeo criadas pelos usuários (link pro MEGA, status Publicado/Pendente, filtros, ordenação por coluna). |
| `mega-campos.php` — **MEGA · Campos de upload** | `aba-mega.js` | **Recém-redesenhada** (abas pills + cards por canal + modal guiado). Usar como referência; só propor ajustes finos se necessário. |

## 5. O que DEVE ser mantido (conteúdo/informação)

O usuário aprovou explicitamente as informações do Dashboard — elas **devem
continuar existindo**, podendo (e devendo) ganhar design melhor e menos poluído:

1. **Monitoramento de Atividade** (status ao vivo por membro)
2. **Visão Geral da Equipe**
3. **Top apps da equipe (foco agregado)**
4. **Timeline da equipe**
5. **Tempo Declarado**

Regra geral para TODAS as páginas: **nenhuma informação ou funcionalidade pode
sumir** — o redesign reorganiza, agrupa, hierarquiza e limpa, mas não corta dados.

## 6. Requisitos de design JÁ DECIDIDOS pelo usuário (incorporar no plano)

### 6.1 Página Canais (`canal.php`) — prioridade
- **Abandonar o modelo tabela/colunas.** Cada canal vira um **bloco/card quadrado**
  com as informações dentro (título, descrição, usuários vinculados, ações).
- **Cada usuário tem uma cor única** para destaque visual (ex.: avatar/chip
  colorido). Ideal: a cor do usuário ser **consistente na plataforma inteira**
  (mesma cor na timeline, na gestão, nos canais) — propor um esquema (ex.: paleta
  fixa atribuída por ordem de cadastro ou hash do `user_id`).
- **Canais sem nenhum usuário vinculado devem ficar destacados** (alerta visual —
  são canais parados/esquecidos).
- A conta **"adm" é ignorada por padrão** na exibição de vínculos (não conta como
  usuário do canal). Adicionar um **toggle "Mostrar adm"**: ligado, mostra os
  canais/vínculos do adm; desligado (padrão), oculta pra ficar limpo.
- **Status do canal**: hoje o backend tem `aberta / em_andamento / concluida /
  cancelada` — o usuário considera isso sem sentido. No design deve existir apenas
  **Ativado / Desativado** (ex.: switch no card). O mapeamento/migração do backend
  é tarefa do Claude (fora do seu escopo); no plano de design basta especificar o
  componente visual assumindo o estado binário.
- (Já implementado no backend pelo Claude, não planejar: excluir canal só é
  permitido se ele não tem nada no MEGA e nenhuma hora declarada.)

### 6.2 Direção geral
- Menos tabelas gigantes; mais cards, agrupamento visual e hierarquia.
- Estados vazios sempre orientados ("o que fazer agora"), como em `mega-campos.php`.
- Cores com significado consistente (status, tipos, usuários) — hoje badges são
  usados de forma irregular entre páginas.
- Dashboard: manter as 5 seções, mas propor layout menos poluído (agrupamento,
  espaçamento, tipografia, talvez colapsáveis).
- Evitar poluição: cada tela deve responder rápido "o que estou vendo e o que
  posso fazer aqui".

## 7. O que você deve entregar no `!executar.md`

1. **Tarefas numeradas na seção "Tarefas Claude 1"**, com `Status: PENDENTE`,
   **incrementais e por página** (ex.: "Design System base (CSS)", "Dashboard",
   "Canais", "Usuários/Gestão", ...), em ordem de execução sugerida — comece pelo
   design system base (variáveis, componentes) e pela página Canais (prioridade
   do usuário).
2. Cada tarefa deve especificar **visualmente** o que construir: layout (esboço em
   texto/ASCII se ajudar), componentes, classes/variáveis CSS novas, cores,
   espaçamentos, estados (hover/vazio/carregando), e o **de→para** de elementos
   que o JS consome (ids/estruturas), quando mudarem.
3. **Não escreva código de backend nem toque em endpoints/banco** — se uma ideia
   de design exigir dado novo, registre como "pergunta/dependência para o Claude"
   dentro da tarefa.
4. Respeite as regras de coordenação do projeto: antes de editar `!executar.md`,
   escreva `AGUARDE ALTERANDO` na primeira linha e remova ao terminar. Não remova
   tarefas concluídas existentes.
5. Em decisões com mais de um caminho (ex.: paleta de cores por usuário, layout do
   dashboard), **apresente as opções + sua recomendação** e aguarde a escolha do
   usuário antes de fixar no plano.
