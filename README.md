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
| Banco | MySQL 5.7+ / MariaDB 10.4+, InnoDB, utf8mb4 |
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
- Upload de arquivos pro MEGA na declaracao (vídeo/thumb/projeto), com aviso de "thumb ja entregue" e download direto dos arquivos da pasta (pastas que já têm thumb pronta aparecem em **verde** na lista de seleção)

### Painel Web (admin)

- **Dashboard** com status em tempo real de todos os editores
- **Graficos ECharts**: donut de apps, ranking foco vs 2o plano, timeline dia a dia
- **Tabela de editores** com colunas Trabalhado (verde) e Ocioso (amarelo)
- **Relatorios** de horas com calculo de valor (R$/hora)
- **Pagamentos** com trava de periodo (bloqueia edicao retroativa)
- **Gestao** de usuarios e atividades
- **MEGA**: upload obrigatorio de arquivos por canal/usuario (tipos: video, thumb, projeto, texto), com links publicos das pastas gerados automaticamente
- **Credenciais de API** cifradas em repouso (libsodium) + **Auditoria** anti-clicker (apps suspeitos + deteccao de input sintetico)

### Seguranca Anti-Fraude

- Editor **nao pode pausar** enquanto estiver ocioso (tempo ocioso fica registrado)
- Declaracao de horas validada contra `segundos_trabalhando` (sem ocioso, sem pausado)
- Tempo ocioso aparece separado no painel (amarelo) para o admin comparar
- Timeline mostra exatamente qual app estava em foco e em que horario

---

## Estrutura

```
Cronometro/
├── main.py                   # Entrypoint do app desktop
├── app/                      # Pacote modular do desktop (config, monitor, app_shell,
│                             #   subtarefas, mega_uploader, mega_sync, hooks_input, ...)
├── banco.py                  # Conexao MySQL thread-safe
├── atividades.py             # Logica de atividades e pagamentos
├── declaracoes_dia.py        # Subtarefas e declaracoes diarias
├── dados.sql                 # Schema completo (NAO versionado — so referencia local)
├── tools/sync_mega_links.py  # Backfill de links publicos do MEGA (mega-export)
├── Dockerfile                # Container do painel web
├── CronometroLeve.spec       # Config do PyInstaller
├── release.bat               # Build + commit/tag/push + GitHub release
│
└── painel/
    ├── index.php             # Pagina Dashboard (refator SPA -> multipagina: cada aba virou pagina)
    ├── usuarios.php  canal.php  relatorio.php  gerenciar-tarefas.php
    ├── credenciais.php  auditoria.php  log.php
    ├── mega.php (Pastas logicas)   mega-campos.php (Campos + Modelos)
    ├── _layout/             # topo.php, fim_conteudo.php, rodape.php (compartilhados)
    ├── css/painel.css        # Tema dark
    ├── js/                   # aba-*.js por funcionalidade: painel, usuarios, atividades,
    │                         #   graficos, relatorio, gerenciar-tarefas, credenciais,
    │                         #   auditoria, log-atividades, mega
    └── commands/             # Endpoints PHP por modulo:
        ├── conexao/  usuarios/ (+ api/)  atividades/  atividades_subtarefas/
        ├── pagamentos/  status/  relatorio/  graficos/  log_atividades/
        ├── credenciais/ (+ api/)   auditoria/
        └── mega/             # config canal, campos, modelos, pastas logicas, desktop_*
```

---

## Banco de Dados (~27 tabelas)

> Visão geral por categoria. O dump completo `dados.sql` é referência local (não versionado); mudanças de schema são feitas por ALTER manual no servidor. Detalhes por tabela no `!projeto.md`.

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
| `pagamento_abatimentos` | Snapshot do saldo pendente por atividade em cada pagamento |

### MEGA (upload obrigatorio por canal/usuario)
| Tabela | Descricao |
|--------|-----------|
| `mega_canal_config` | Pasta raiz no MEGA + flag `upload_ativo` por canal |
| `mega_campos_upload` | Campos exigidos por `user_id + id_atividade` (com `tipo`: video/projeto/thumb/texto/outro) |
| `mega_campos_modelos` | Templates globais reutilizaveis de campos |
| `mega_pasta_logica` | Indice das pastas do video (`NN - Titulo`) + `link_mega` publico |
| `mega_uploads` | Metadados de cada upload (status, quem subiu, qual campo) |

### Credenciais / Auditoria / Log
| Tabela | Descricao |
|--------|-----------|
| `credenciais_modelos` / `credenciais_usuario` | Credenciais de API cifradas em repouso (libsodium) |
| `auditoria_apps_suspeitos` | Apps que disparam flag de anti-clicker (match por substring) |
| `cronometro_input_stats` | Input humano vs sintetico por bucket de 60s (flag INJECTED) |
| `log_atividades` | Log de todas as acoes do servidor (retencao 60 dias) |

---

## Como Rodar

### 1. Banco de Dados

```bash
mysql -u root -p < dados.sql
```

### 2. App Desktop

```bash
pip install pymysql psutil
python main.py
```

Ou use o .exe compilado: `dist/CronometroLeve.exe`

### 3. Painel Web

**XAMPP:**
```
Projeto vive em htdocs/cronometro-web/painel/
Acesse: http://localhost/cronometro-web/painel/
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

## Troubleshooting

### "Sem conexao com o servidor" so em alguns usuarios

**Sintoma:** o app desktop fica em "Verificando..." e depois mostra `Sem conexao com o servidor.` para um usuario especifico, enquanto no PC do dev/admin e em outros usuarios conecta normalmente. Abrir `https://banco-painel.cpgdmb.easypanel.host` no **navegador do PC afetado** tambem falha com `ERR_CONNECTION_TIMED_OUT`.

**Causa:** nao e o app — e a rota de internet do usuario ate o servidor EasyPanel. Alguns provedores (ISPs) brasileiros tem peering ruim com o datacenter do EasyPanel/Hetzner e o TCP do PC dele nao consegue fechar handshake com o IP de destino. Antivirus com protecao web e firewalls corporativos podem causar o mesmo timeout.

**Como diagnosticar (2 passos):**

1. Pedir para o usuario abrir `https://banco-painel.cpgdmb.easypanel.host/baixar_app.php` no navegador.
   - Se der `ERR_CONNECTION_TIMED_OUT` -> e rota/firewall (siga passo 2).
   - Se abrir normal mas o app continua falhando -> ai sim e problema local do app (antivirus bloqueando o .exe, versao desatualizada, etc).
2. Pedir para ele conectar o PC no **4G/5G do celular** (hotspot) e testar. Se funcionar no 4G, confirma que e a rede dele.

**Solucao validada (caso real, 2026-05-25):**

Instalar o **Cloudflare WARP** ([1.1.1.1](https://1.1.1.1)), abrir o app, escolher o modo **"Trafego e DNS (UDP)"** e clicar em Conectar. A nuvem fica colorida ("Conectado") e o app desktop conecta na hora.

> Os modos "Somente DNS (HTTPS/TLS)" **nao resolvem** este caso — o problema nao e DNS, e rota TCP. So o modo de trafego completo passa o trafego pela rede Cloudflare e contorna o roteamento ruim do provedor.

**Se mesmo com WARP nao funcionar:** investigar antivirus (Kaspersky/ESET/Avast com protecao web ativa bloqueando o dominio), firewall do roteador ou VPN/proxy ativos no PC do usuario.

### "certificate has expired" na sincronizacao do MEGA (RESOLVIDO em v4.0.3)

**Sintoma:** a sync das pastas MEGA falha com `Pastas MEGA nao sincronizadas: Falha ao consultar painel: ... [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired`, **mesmo com a data e a hora do PC corretas**, e mesmo abrindo `https://banco-painel.cpgdmb.easypanel.host` normalmente no navegador.

**Causa:** o PC nao tem os certificados-raiz novos da Let's Encrypt (ISRG Root X1/X2) — comum em Windows desatualizado. O navegador funciona porque baixa esses roots sozinho; o app (OpenSSL) nao, e acabava seguindo o `DST Root CA X3`, vencido em 30/09/2021.

**Solucao definitiva (v4.0.3+):** o app passou a embutir os certificados (`certifi`) e validar HTTPS contra eles, em vez do repositorio do Windows — ver `app/config.py` (override de `ssl._create_default_https_context`). Funciona em qualquer PC, sem mexer no Windows. Usuarios em versoes antigas recebem o fix pelo auto-update (o download vem do GitHub, que nao e afetado).

**Solucao manual (so para versoes < v4.0.3):** instalar os roots `ISRG Root X1` e `ISRG Root X2` (https://letsencrypt.org/certs/) em "Autoridades de Certificacao Raiz Confiaveis", ou rodar o Windows Update.

### "Login no MEGA falhou: Failed to access server" na sincronizacao

**Sintoma:** a sync das pastas MEGA falha com `Login no MEGA falhou: mega-login falhou (rc=...): Failed to access server: ...`. **A chamada ao painel funcionou** (passou da etapa de certificado) — quem falha e o **MEGAcmd** ao conectar nos servidores do MEGA. **Nao tem relacao com o app, com o certificado nem com o auto-update** (o MEGAcmd e um programa separado, com conexao propria).

**Como confirmar a causa:** abrir `%LOCALAPPDATA%\MEGAcmd\megacmdserver.log` no PC e olhar as ultimas linhas. `Failed reqstat request. Retrying` repetido = MEGAcmd nao consegue falar com os servidores do MEGA (conexao instavel/parcial ou sessao travada).

**Solucao (em ordem):**

1. **Reiniciar o PC** (ou finalizar `MEGAcmdServer.exe` no Gerenciador de Tarefas) e clicar "Atualizar MEGA". Limpa uma **sessao travada** do MEGAcmd — **resolveu o caso real de 2026-06-05**.
2. Se voltar a falhar: **Cloudflare WARP** no modo "Trafego e DNS" (mesma solucao do problema de rota ate o painel — ver secao acima), pois pode ser roteamento ruim do provedor ate os servidores do MEGA.
3. Liberar `MEGAcmd` e os dominios do MEGA (`*.mega.nz`, `*.mega.co.nz`, `g.api.mega.co.nz`, `*.userstorage.mega.co.nz`) no antivirus/firewall.
4. Testar no 4G/5G do celular (hotspot): se funcionar, confirma que e a rede/provedor do PC.

### "Nao existe tempo monitorado disponivel no cronometro" ao declarar (horas nao salvam) — RESOLVIDO 2026-06-11

**Sintoma:** o usuario cronometra (mexendo no mouse), pausa e tenta declarar, mas recebe `Nao existe tempo monitorado disponivel no cronometro` — mesmo tendo trabalhado. Afetava TODOS os usuarios e nenhuma hora trabalhada era salva.

**Causa:** descasamento de schema. O app grava `cronometro_relatorios.id_atividade` como **NULL** (modo "cronometro neutro"), mas a coluna em producao estava como **`NOT NULL`**. Toda gravacao falhava com erro MySQL 1048 ("Column 'id_atividade' cannot be null") e a falha era **silenciosa** (`try/except: pass`). O banco ficava sem horas → a validacao anti-fraude via 0 → recusava a declaracao. O sintoma aparece no log tecnico (`~/.cronometro_leve_log_tecnico.txt`) como `[relatorio_erro] upsert falhou :: id_atividade cannot be null`.

**Solucao:** `ALTER TABLE cronometro_relatorios MODIFY COLUMN id_atividade INT NULL;` (alinha o banco com o app). Resolve para todos na hora, sem precisar de novo build/deploy. As horas do periodo em que ficou quebrado nao foram gravadas, mas dá para reconstruir parcialmente a partir de `cronometro_eventos_status` (heartbeats com `situacao`). Detalhes em `auditoria.md` #33.

---

## Changelog

> A lista completa e por-versao do app desktop fica em `app/config.py` (`HISTORICO_VERSOES`), que e a fonte da verdade e e exibida dentro do proprio app. Abaixo, so os destaques recentes.

### v4.0.7 (2026-06-12)

- **Fix:** ao declarar tarefa, um arquivo selecionado (ex.: thumb) podia nao ser enviado ao MEGA mesmo o sistema mostrando a tarefa como salva — acontecia sempre na conta administradora (todos os campos opcionais) e nos campos opcionais dos demais usuarios. Agora, havendo qualquer arquivo selecionado, o botao fica em "Enviar Arquivos" e o upload acontece de verdade antes de salvar. (auditoria #34)
- **Fix:** enviar arquivo sem preencher o tempo travava o app (`bad window path name`) porque o auto-save tentava concluir exigindo tempo > 0 numa janela ja fechada. Agora, sem tempo valido, a tarefa e salva como Aberta (entrega de thumb/arquivo sem horas) e o erro nao quebra mais.

### v4.0.6 (2026-06-11)

- **Fix:** pastas de video renomeadas direto no MEGA (ex.: marcando "THUMB BAIXADO" ou corrigindo o nome) sumiam da lista "Selecionar existente" — a sincronizacao diaria as inativava por engano. O app deixou de inativar pastas automaticamente; pastas renomeadas no MEGA continuam aparecendo. (Tambem reforcado no servidor, que protege ate quem esta em versao antiga.)

### v4.0.5 (2026-06-06)

- Na declaracao de tarefa, a lista "Selecionar existente" mostra em **verde** as pastas que ja tem thumb entregue (por voce ou por um colega), com a marca "✓ thumb feita" — da pra ver de relance quais nao precisam de thumb. Lista tambem ficou mais alta.

### v4.0.4 (2026-06-06)

- **Fix:** pastas com `?`, aspas ou ponto final no titulo sumiam da lista "Selecionar existente" (a sincronizacao as inativava por engano). Corrigido — voltam a aparecer.
- **Fix:** download de arquivo de pasta antiga (ou com caractere especial no nome) falhava com "nao encontrado". Agora o app tenta caminhos alternativos e baixa certo.
- **Melhoria:** geracao do link publico da pasta no MEGA passou a funcionar tambem em pastas com `?`/aspas no nome.

### v4.0.3 (2026-06-04)

- **Fix HTTPS:** correcao do erro "certificado expirado" na sincronizacao do MEGA em PCs com Windows desatualizado — o app agora embute os certificados-raiz (`certifi`) e nao depende mais do repositorio de certificados do Windows.

### v4.0.2 (2026-06-04)

- Botao **"Copiar erro"** na sincronizacao do MEGA (copia a mensagem completa do erro, antes cortada na tela).
- Aviso amigavel pedindo para ajustar a data/hora quando a falha de sync e causada por relogio do PC desatualizado.

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
