# 🌐 Guia de Testes via Navegador (para IAs)

> Cópia local do mestre `D:/regra-global-LLM/Não Ler/navegador-testes.md`.
> **Quando ler:** SOMENTE quando o usuário pedir explicitamente para entrar no navegador / testar a plataforma na interface real. Fora isso, não carregar.

> **Ao ser acionado, ANTES de tudo:** se o usuário **não informou a porta de debug (CDP)** do navegador, **pergunte a porta** (Dolphin Anty ou Chrome com `--remote-debugging-port`; portas típicas 8222 / 9222). Sem a porta não há como conectar.

> Este arquivo é **dinâmico e por plataforma**: ao descobrir um fluxo, seletor ou comportamento novo, **anote na seção da plataforma** pra a próxima IA já saber onde clicar e o que esperar.

---

## 🧠 Princípio nº 1 — TEXTO é barato, SCREENSHOT é caro

Ler um screenshot custa ~50× mais tokens que ler texto. Portanto:

- O script deve **VERIFICAR e IMPRIMIR TEXTO** (PASS/FAIL, contagens, status, mensagens de toast, se um modal está visível) — em vez de tirar print pra "olhar".
- **Print só quando:** (a) for um detalhe visual que só se enxerga na imagem, ou (b) o usuário pedir pra ver. E aí **1 print**, não vários.
- **Agrupe passos por fase:** 1 execução de script = 1 bloco de resultado. Nunca "1 clique → 1 print → repete".
- Faça os scripts **auto-verificáveis** (eles mesmos imprimem `PASS`/`FAIL`).

## ⚙️ Setup do driver (sem poluir o projeto)

1. Confirmar CDP acessível: `curl -s http://localhost:<PORTA>/json/version` → deve retornar JSON com `webSocketDebuggerUrl`.
2. Driver leve: **`puppeteer-core`** (NÃO baixa navegador, só conecta). Instalar num diretório **scratch** (ex.: `C:\tmp\bt`), nunca no `node_modules` do projeto:
   - `mkdir C:\tmp\bt`, dentro: `npm init -y` e `npm i puppeteer-core`
3. Conectar à instância **já aberta**: `puppeteer.connect({ browserURL: 'http://localhost:<PORTA>', defaultViewport: null })`. Pegar a página existente (`browser.pages()`), não abrir nova aba.

## 🤖 Padrões de automação (apps Livewire / SPA)

- **Clicar por TEXTO visível**, não por seletor CSS frágil: varrer `button, a, [role=button], label` e achar o que contém o texto. O DOM muda a cada render.
- **Esperar entre ações**: SPA re-renderiza assíncrono. Use `waitForFunction(() => document.body.innerText.includes('<texto esperado>'))` antes do próximo passo (um `sleep` curto após o clique também ajuda).
- **Upload de arquivo**: achar `input[type=file]` (mesmo oculto) e `el.uploadFile('C:\\caminho\\arquivo')`. Com vários inputs, mirar pelo `accept`/`wire:model`.
- **Fechar modal clicando fora**: clicar no backdrop com `page.mouse.click(8, 8)` (canto, fora do painel).
- **Assert de modal visível**: checar no DOM se o painel do modal está renderizado E `offsetParent !== null`.
- **Toast**: ler o texto do elemento de toast logo após a ação.
- Reusar um **runner genérico** (`act.js`) que recebe uma lista de passos em JSON (`goto`, `clickText`, `fill`, `upload`, `waitText`, `hasText`, `backdrop`, `shot`).

## ⚠️ Limites honestos (avisar o usuário)

- Reportar fielmente: se um passo falhou (seletor não achado, toast de erro), dizer.

---

# 🗺️ MEMÓRIA — Mapa por plataforma

## Dokploy — VPS nova (migração do cronometro-web)

### Ambientes
- Painel Dokploy: `http://2.24.87.57:3000/dashboard/projects` (porta CDP de debug usada: **8221**).
- Login: e-mail/senha (credenciais fornecidas pelo usuário em chat — **não versionar**).
- ⚠️ **REGRA DE OURO:** há VÁRIOS outros projetos do usuário nesta instância. **PROIBIDO deletar ou modificar qualquer projeto existente.** Só criar/configurar o projeto novo `RK produções`.

### Versão / contexto
- Dokploy **v0.29.2**. Conta `rafaelkolaias@gmail.com` (org "My Organization").
- Projetos existentes (NÃO TOCAR): **Mag**, **zap-flowing-homologue** (5 svc), **wonderdesignn**, **zap-flowing** (6 svc).
- Projeto criado pra esta migração: **RK produções** (2026-06-14).

### Navegação (rotas)
- Login: `http://2.24.87.57:3000/` → input[type=email] + input[type=password] → botão texto "Login". Sucesso → `/dashboard/home`.
- Projetos: `/dashboard/projects`. Home: `/dashboard/home`.
- Sidebar (texto): Home, Projects, Deployments, Monitoring, Schedules, Traefik File System, Docker, Settings, etc.

### Fluxos principais
- **Criar projeto:** botão texto `Create Project` → modal `[role=dialog]` com `input[name=name]` + `textarea[name=description]` + Tags → botão `Create`. Fecha sozinho ao criar.
- **Entrar no projeto:** clicar no link do card (URL vira `/dashboard/project/<projId>/environment/<envId>`). RK produções: projId=`o8AtMLlkbZYh0r2l5Vchh`, envId=`vhkOo_tdDlegeExI4uGJF`.
- **Create Service** (dropdown Radix — abre só com clique de mouse REAL, `page.mouse.click` nas coords; `.click()` programático NÃO abre): itens `Application`, `Database`, `Compose`, `Template`, `AI Assistant`.
- **Database form:** radios de tipo (PostgreSQL/MongoDB/MariaDB/MySQL/Redis/libSQL) + `input[name=name]` (serviço) + `input[name=appName]` + `textarea[name=description]` + `input[name=databaseName]` + `input[name=databaseUser]` + `input[name=databasePassword]` + `input[name=dockerImage]` → botão `Create`.

### Armadilhas conhecidas
- DOM é SPA (Next.js/React). Clicar por TEXTO visível, esperar re-render. Login redireciona `/dashboard/projects` → `/` quando deslogado.
- **Dropdowns Radix (Create Service) só abrem com `page.mouse.click(x,y)` nas coordenadas reais** — `el.click()` via evaluate não dispara o pointerdown.
- Fechar modal: `Escape` (funciona) ou botão `Close`.
