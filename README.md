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
├── main.py                   # Entrypoint do app desktop
├── app/                      # Pacote modular do desktop (config, monitor, app_shell, etc.)
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
python main.py
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

---

## Changelog

> A lista completa e por-versao do app desktop fica em `app/config.py` (`HISTORICO_VERSOES`), que e a fonte da verdade e e exibida dentro do proprio app. Abaixo, so os destaques recentes.

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
