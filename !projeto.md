# Cronômetro — Mapa do Projeto (para IAs)

> **Propósito deste arquivo:** servir como índice rápido para localizar código sem precisar varrer o repo. Leia o arquivo correspondente à sua tarefa em vez de tudo.

---

## 🎯 O que é

Sistema de monitoramento de produtividade. **App desktop** (Windows, Python/Tkinter) registra horas trabalhadas; **painel web** (PHP/Bootstrap) gerencia equipe e pagamentos. Banco MySQL/MariaDB.

---

## 🗂️ Onde está cada coisa

### Desktop (Python)

> **Refator v2.8 (2026-04-30, deleção do shim em 2026-05-01):** o monolito `app.py` (~4480 linhas) foi quebrado em pacote `app/` + `main.py` raiz. Comportamento preservado em todos os fluxos. **O shim `app.py` foi removido** — só existem `main.py` (raiz) + pacote `app/`. Entrypoint oficial é `main.py`; PyInstaller (`CronometroLeve.spec`) também aponta pra `main.py`. Tests rodam via `from app import ...` — `app/__init__.py` re-exporta os símbolos públicos.

| Arquivo | Quando ler |
|---|---|
| `main.py` | Entrypoint oficial — minimalista, só chama `app.main.main()`. |
| `app/__init__.py` | Re-exports do pacote (símbolos públicos para `from app import X`). |
| `app/main.py` | `main()` que cria o `App()` e chama `mainloop()`. **Antes do mainloop chama `_limpar_bak_residuais()`** — varre `*.bak` na pasta do `sys.executable` e apaga (só roda quando `frozen`). Defesa contra a armadilha #33: se o auto-update anterior deixou um `CronometroLeve.exe.bak` que o AV/Windows manteve "locked", o `unlink()` dentro de `_baixar` falha silenciosamente e o swap aborta — limpar na abertura garante pasta pronta pro próximo update. |
| `app/config.py` | Constantes globais, `VERSAO_APLICACAO`, `HISTORICO_VERSOES`, `LogTecnico`, `LOG_TEC`, `MODO_SCRIPT`, todos os `INTERVALO_*`, `LIMITE_*` e caminhos `ARQUIVO_*`. **Fonte canônica da versão** — `release.bat` lê via findstr daqui (`app\config.py`). Também expõe **prefs locais** persistidas em `~/.cronometro_leve_prefs.json` via `carregar_prefs()` / `salvar_pref(chave, valor)` — defaults em `_PREFS_DEFAULTS`. **HTTPS via certifi (v4.0.3+):** no import, sobrescreve `ssl._create_default_https_context` para validar contra `certifi.where()` (roots embutidos) em vez do repositório do Windows — corrige `certificate has expired` em PCs sem os roots novos da Let's Encrypt. Exige `collect_all('certifi')` no `CronometroLeve.spec`. |
| `app/win32_utils.py` | Helpers Win32 (`obter_segundos_ocioso_windows`, `obter_aplicativo_em_foco`, `listar_nomes_apps_visiveis`) + conversores (`formatar_hhmmss`, `converter_segundos_para_inteiro`, `dividir_tempos_por_dia`). Sem dependência circular. |
| `app/hooks_input.py` | `DetectorInputSintetico` + structs ctypes (`_MSLLHOOKSTRUCT`, `_KBDLLHOOKSTRUCT`) + flags `LLMHF_INJECTED` / `LLKHF_INJECTED`. Mantém referências fortes dos callbacks (`_cb_mouse_ref`/`_cb_kbd_ref`) — **nunca apagar**. |
| `app/monitor.py` | `EstadoMonitor` (dataclass) + `MonitorDeUso`. Coração do cronômetro: sessão, heartbeat, fila offline, foco/apps, persistência local, snapshots, integração com `DetectorInputSintetico`. |
| `app/subtarefas.py` | `JanelaSubtarefas(tk.Toplevel)` — janela "Tarefas da Atividade" / "Declarar Tarefa". **Pós-Fase 3 MEGA + progresso/cancel + UX polishing + integridade + upload-pasta + bugfixes pós-feedback + v3.1.2 (canal sem upload bloqueia + ocultar pagas):** `_abrir_formulario_subtarefa()` virou dispatcher: faz pré-fetch de `desktop_obter_config.php` (timeout 5s) e chama `_abrir_formulario_subtarefa_legado()` (modo antigo, com aviso suave) ou `_abrir_formulario_subtarefa_mega()` (form com pasta lógica + uploads dinâmicos + bloqueio de conclusão até uploads obrigatórios concluírem). **`__init__` aceita `mapa_canal_para_id: dict[str, int]`** (passado por `app_shell._abrir_tarefas_do_dia` a partir de `_mapa_item_para_id`) pra suportar troca de canal em runtime no form MEGA — refetch da config, reset pasta_logica, atualiza `pasta_raiz_holder["valor"]` e `var_pasta_raiz`, **reconstrói widgets dos campos** via `_construir_widgets_campos(novos_campos)` (frame `frame_uploads` é destruído + recriado). `salvar()` usa **`id_atividade_efetiva["id"]`** (NÃO `self._id_atividade`) — sem isso, a sub é gravada no canal de origem em vez do canal trocado. **No form MEGA:** Nº da pasta é **read-only** (calculado por `_calcular_proximo_numero()` = max(numero_video)+1 zfill 2; recalcula em cada alternância pra "criar"); 409 do `desktop_criar_pasta.php` dispara retry automático com refetch da config. Após criar pasta, switch automático pra "Selecionar existente" + radio "Criar nova" desabilitado. **Cada linha de campo tem 2 botões: "Selecionar arquivo" e "📁 Pasta"** (askdirectory + validação rglob + soma tamanho); ambos disabled durante upload. **`_atualizar_lock_pasta`** trava combobox + radios + botão "Criar pasta" enquanto `estado_campos` tem algum em `enviando`/`concluido` (impede trocar pasta no meio do upload). Helper `_iniciar_upload_mega(eh_pasta=False)` orquestra filedialog → **valida `pasta_existe` no MEGA antes** (sincronia, levanta `ErroPastaMegaInexistente` se sumiu — marca pasta_logica inativa) → `desktop_registrar_upload` (status=enviando) → **dedup do anterior**: se `arquivo_remoto_anterior` termina com `/` chama `remover_pasta_recursiva` (caso pasta), senão `remover_arquivo` → `MegaUploader.upload_arquivo(on_progress, cancel_event)` → grava `arquivo_remoto_anterior` no estado → `desktop_registrar_upload` (status=concluido/erro). **Progressbar determinate** com status `enviando X%…` ou `enviando pasta X%…`. **Botão "Cancelar"** (`pack` só durante upload) seta `cancel_event` → handler `_falha` reconhece `ErroUploadCancelado`. **`_atualizar_botao_salvar`** bloqueia com aviso explícito quando `estado_campos` está **vazio** (canal MEGA ativo + admin não cadastrou nenhum `mega_campos_upload` pro par user+canal — regra "MEGA ativo = precisa subir algo"). **Edição de subtarefa:** ao abrir o form, dispara `obter_dados_subtarefa` em background; pra cada arquivo concluído, popula `estado_campos[campo]["arquivo_remoto_anterior"]` + status visual `✓ enviado` + botão `Trocar arquivo`. **`_excluir_subtarefa`:** fetch dos dados MEGA → se `outras_subtarefas_na_pasta == 0` chama `remover_pasta_recursiva` + `marcar_pasta_logica_inativa`; senão remove só os arquivos da sub. Banco apaga **sempre** (banco é fonte da verdade); falhas no MEGA mostram `messagebox.showwarning` com lista. Pasta lógica criada por `desktop_criar_pasta.php`. Quando MEGA está ativo, o título da subtarefa salva passa a ser exatamente o `nome_pasta` retornado pelo backend. **v3.1.2 — bloqueio + ocultar pagas + UX legado:** (a) **`_var_ocultar_pagas`** (`tk.BooleanVar`, default lido de `carregar_prefs()["ocultar_tarefas_pagas"]`, default global True) controla checkbox `"Ocultar tarefas pagas"` no rodapé ao lado do botão "Configurar Pix"; toggle persiste via `salvar_pref("ocultar_tarefas_pagas", ...)` e dispara `_recarregar_dados()`. Filtro aplicado em `_aplicar`: subs com `bloqueada_pagamento=True` são puladas no loop de itens da árvore quando flag está ligada. **Linhas de pagamento (verdes) seguem aparecendo independente do filtro** — só esconde subs travadas. (b) **Dispatcher `_abrir_formulario_subtarefa`** classifica config: `cfg=None` (offline/timeout) → legado SEM aviso; `cfg.upload_ativo=False` → legado COM aviso e, se for **criação nova** (`subtarefa is None`), `bloquear_sem_upload=True`. (c) **`_abrir_formulario_subtarefa_legado(..., bloquear_sem_upload=False)`:** quando True, aviso vai vermelho `#e55555` em negrito, botão Salvar `state="disabled"` com texto fixo `"Configurar canal antes de declarar"`. Edição de subs antigas NÃO bloqueia (passa False mesmo com canal sem upload — preserva ajustes em legado pré-MEGA). (d) **Combo CANAL no formulário legado** agora sempre `state="disabled"` (era "readonly") — antes o user trocava canal mas o form continuava legado e o `id_atividade` salvo era sempre `self._id_atividade` da janela (combo era cosmético, gerava confusão). Pra trocar canal, fechar e selecionar pelo menu principal. (e) **Layout do legado:** linha 1 = CANAL + DATA, linha 2 = Nº DO VÍDEO + TAREFA (CANAL movido pro topo). |
| `app/app_shell.py` | `App(tk.Tk)` — shell principal: login, auto-login, tela principal, fixar/desfixar, regressiva, auto-update, `_tick_ui`. |
| `app/mega_uploader.py` | **(Fases 2+3 MEGA + progresso/cancel + integridade banco↔MEGA + upload-pasta + sync/recovery v3.0)** Integração com MEGAcmd + cliente HTTP do painel. **`MegaUploader`**: `garantir_instalado()`, `garantir_logado()`, `criar_pasta()`, `upload_arquivo(arquivo, pasta_remota, on_progress=None, cancel_event=None)` — aceita `Path` de **arquivo OU diretório** (MEGAcmd recursivo nativo via `mega-put -c <dir>`), `listar()`, **`remover_arquivo(path)`** (`mega-rm -f`, idempotente — ignora "not found"), **`remover_pasta_recursiva(path)`** (`mega-rm -r -f`), **`pasta_existe(path)→bool`** (baseado em `mega-ls`). Auto-instala MEGAcmd silenciosamente (NSIS `/S`) se faltar; busca `mega_email`/`mega_password` via `credenciais/api/obter.php`, decifra com pynacl (XSalsa20-Poly1305) e roda `mega-login`. **Login considerado OK em `rc in (0, 54)`** — MEGAcmd 2.5.2+ não emite mais "Login complete", só `Fetching nodes ||...||(X/Y MB: Z%)`. Subprocesso sempre com `CREATE_NO_WINDOW`+`SW_HIDE`. **`_executar_silencioso` redireciona stdout/stderr pra arquivos temp** (não PIPE — bug do daemon herdeiro, ver armadilha #25). Retry 1x em sessão expirada. **Streaming de progresso (`_executar_mega_put_streaming`):** Popen com stderr→arquivo + thread daemon que tail/parseia regex `\((\d+/\d+\s*[KMGT]?B:\s*(\d+\.?\d*)\s*%)\)` e dispara `on_progress(pct: float)` com throttle de 0.5%. **Cancelamento** via `cancel_event: threading.Event` — polling 200ms; ao set, `taskkill /F /T /PID` mata árvore (cmd.exe + shell + filhos), preserva `MEGAcmdServer` daemon. Levanta `ErroUploadCancelado` (subclasse de `ErroUploadMega`). **Download (verde compartilhado + baixar):** `baixar_arquivo(arquivo_remoto, destino_local, ...)` (1 arquivo: baixa pra tmp dentro do destino → os.replace) e `baixar_pasta(pasta_remota, destino_dir, ...)` (pasta recursiva direto no destino) + `_executar_mega_get_streaming` espelham o `mega-put` com `mega-get` (mesmo `_REGEX_PROGRESSO`, cancel via `cancel_event`, retry em sessão expirada; baixa pra tmp dir DENTRO da pasta de destino → `os.replace` atômico, sem cross-device/colisão). **Link público automático (v4.0.4+):** `exportar_link(caminho_remoto)` roda `mega-export -a` (fallback sem `-a` se já exportada) e devolve a URL `https://mega.nz/...`. Chamado pelo `_iniciar_upload_mega` (em `subtarefas.py`) logo após o upload — best-effort, 1× por pasta lógica por janela (set `self._links_pasta_exportados`) — e salvo via `PainelMegaApi.salvar_link_pasta`. Assim **toda pasta nova já nasce com link no painel**, sem depender do script manual `tools/sync_mega_links.py` (que continua como backfill/fallback). **`PainelMegaApi`**: cliente dos endpoints `commands/mega/desktop_*` — `obter_config_canal`, `criar_pasta_logica`, `registrar_upload`, **`salvar_link_pasta(id_pasta_logica, link_mega)`** (POST `pasta_logica_salvar_link.php`), **`obter_status_pasta(id_pasta_logica)`** (status compartilhado da pasta pro verde+download), **`obter_dados_subtarefa(id_subtarefa)`** (uploads concluídos + count de outras subtarefas que reusam a pasta lógica), **`marcar_pasta_logica_inativa(id_pasta_logica)`**, **`pastas_logicas_para_sync()`** (lista canais/pastas para sincronização diária banco↔MEGA), **`marcar_pastas_logicas_inativas_lote(ids)`** (soft-delete em lote usado pela sync) e **`uploads_orfaos_listar()`** (recovery de uploads sem subtarefa após queda/fechamento abrupto). Hierarquia de exceções: `ErroMega` raiz; subclasses `ErroInstalacaoMega`, `ErroLoginMega`, `ErroCredencialFaltando`, `ErroSessaoExpiradaMega`, `ErroUploadMega`, `ErroUploadCancelado`, **`ErroPastaMegaInexistente`** (subclasse de `ErroUploadMega` — sincronia rompida: pasta lógica existe no banco mas sumiu do MEGA), `ErroPainelHTTP` (com `codigo_http`). |
| `app/segredos.py` | **NÃO VERSIONADO** (`.gitignore`). Exporta `APP_CLIENT_DECRYPT_KEY` (base64 de 32 bytes) embutida no .exe. Importada por `app/config.py` com fallback vazio quando ausente. |
| `app/validador_pix.py` | `validar_pix(texto) -> (tipo, valor_normalizado)` / `ErroPixInvalido`. Aceita CNPJ(14d+DV), celular BR(10–11d com DDD), e-mail. Recusa CPF (mensagem dedicada) e qualquer formato fora desses três. Espelho de `painel/commands/_comum/pix.php` — manter sincronizado se mudar regra. |
| `app/mega_sync.py` | **(v3.0+)** Sincronização das pastas lógicas com a raiz do canal no MEGA. `executar_sincronizacao_async(user_id, uploader, api)` cria thread, gerencia estado em `.cronometro_leve_mega_sync.json` (via helpers de `app/config.py`) e notifica listeners (UI). Política conservadora: falha de listagem em qualquer canal aborta sem inativar nada. Lotes de 300. **Disparada por `_iniciar()` via `after(5_000, ...)`** (5 s após clicar Iniciar) — só roda 1× ao dia (controle por `data_sync_ok` em `~/.cronometro_leve_mega_sync.json`). Listeners se inscrevem com `registrar_listener(cb)` / `remover_listener(cb)`; callback recebe `(user_id, estado_dict)` em thread arbitrária — UI deve marshallar com `after(0, ...)`. Estado tem 4 status: `nao_sincronizado`, `sincronizando`, `sincronizado`, `erro`. `JanelaSubtarefas` consome pra bloquear `Declarar Tarefa` enquanto não está `sincronizado` — botão muda texto pra `SINCRONIZANDO` durante a sync; status aparece no **topo da janela** (substituiu a frase explicativa "Cadastre as subtarefas…" em v3.0). |
| `banco.py` | Camada PDO MySQL thread-safe. Editar só ao mudar conexão. |
| `atividades.py` | CRUD de canais, vínculo membros, regras de pagamento. |
| `declaracoes_dia.py` | Subtarefas (criar/editar/concluir), espelho `declaracoes_dia_itens`, auditoria. Funções-chave: `_sincronizar_item_espelho_da_subtarefa`; **validação anti-fraude global por usuário (sem filtro de atividade nem de data)** em `_validar_tempo_contra_monitoramento` — cronômetro neutro: o usuário pode declarar horas em qualquer atividade onde tenha subtarefa, desde que o total declarado não ultrapasse o total cronometrado (alinhado com `painel/commands/atividades_subtarefas/editar.php`). **v4.0.1: `obter_segundos_declarados_do_dia` agora filtra `bloqueada_pagamento = 0`** — antes somava todas as subtarefas (incluindo já pagas), causando bloqueio indevido após pagamento. Painel (`editar.php`) alinhado com o mesmo fix. Helpers de leitura `obter_abatimento_total_atividade`, `obter_segundos_declarados_desbloqueados` e `obter_segundos_cronometrados_atividade` aceitam `id_atividade=0` para somar todas (trabalhando + ocioso, métrica neutra para UI). `obter_resumo_do_dia` retorna `saldo_hhmmss` (interno), `declarado_ciclo_hhmmss` (subtarefas desbloqueadas do ciclo) e `cronometrado_hhmmss` (total cronometrado do usuário — exibido no rodapé da JanelaSubtarefas). **Abatimentos em `pagamento_abatimentos` são gravados pelo painel** (`_aplicar_pagamento.php`) — o desktop só lê. `atualizar_bloqueios_por_pagamento` e `_registrar_abatimentos_por_pagamento` continuam definidas como utilitários standalone (uso manual/legado), mas não são mais chamadas em `JanelaSubtarefas.__init__`. |
| `dados.sql` | **Schema de referência local — NÃO versionado** (está em `.gitignore`). Reflete o schema completo do banco (dump do MariaDB). Editar quando uma mudança no banco real exigir refletir aqui. **Ver convenções abaixo antes de editar.** |
| `credenciais_tabelas.sql` | **Migration manual da Fase 1 do módulo de Credenciais — único `.sql` versionado.** Cobre só `credenciais_modelos` e `credenciais_usuario`, e está **desatualizado**: não inclui a coluna `aplicar_novos_usuarios` que o código atual exige. Não usar como fonte da verdade do schema — é histórico do bootstrap inicial. |
| `atualizar_build.bat` | PyInstaller → `painel/downloads/CronometroLeve.exe`. |
| `CronometroLeve.spec` | Spec do PyInstaller. Entry = `main.py`. Usa `collect_all('nacl')` para garantir `_sodium.pyd` + `libsodium.dll` (pynacl) no `.exe` e `collect_all('certifi')` (v4.0.3+) para embutir o `cacert.pem` (HTTPS via certifi — ver `app/config.py`). `hiddenimports` lista todos os módulos de `app/` + `certifi` (incluir aqui ao adicionar módulo novo). |
| `release.bat` | Wrapper de release: lê `VERSAO_APLICACAO` de `app\config.py` via findstr, chama `atualizar_build.bat`, faz `git commit/tag/push` e cria GitHub Release com `gh release create` (anexa `dist/CronometroLeve.exe`). |
| `validate.bat` | Suíte de validação local (lint/typecheck/tests). **`cd` aponta para `C:\xampp\htdocs\dashboard\Cronometro` — caminho obsoleto** (projeto vive em `c:\xampp\htdocs\cronometro-web`). Não rodar sem corrigir. |
| `atualizar_build.bat.txt` | Backup textual do bat antigo. **Path obsoleto** (`C:\xampp\htdocs\dashboard\Cronometro`). Apenas referência histórica. |
| `pyproject.toml` | Config de tooling: `ruff` (target py310, line-length 120), `mypy`, `pytest` (testpaths `tests/`). **`version = "2.2"` está desatualizado** vs `VERSAO_APLICACAO` em `app/config.py` (atualmente v4.0.6) — fonte da verdade da versão é sempre `app/config.py`. |
| `requirements.txt` / `requirements-dev.txt` | Deps Python runtime/dev. CI consome `requirements-dev.txt` no job `test`. |
| `Backup banco/` | Dumps SQL históricos (`DD-MM-AA-dados.sql`). Ignorado pelo runtime — referência manual. |
| `package.json` / `node_modules/` | Apenas declara dep `ws` (websocket). **Não há `import 'ws'` em nenhum lugar do código** — dependência órfã, candidata a remoção. `node_modules/` está no diretório por inércia. |
| `Dockerfile` | Imagem `php:8.1-apache` para deploy do `painel/` (não do desktop). Habilita `mod_rewrite`/`headers`, instala `pdo_mysql`, ativa `AllowOverride All`. Não documenta o `.env` — secrets têm que ser injetados em runtime. |
| `AGENTS.md` | Apenas redireciona para `D:\regra-global-LLM\RULES.md` + arquivos locais `temporary_rules.md`/`reminder.md`. Não tem regra própria. |

#### Mapa rápido do desktop (onde mexer sem ler tudo)

**Estrutura modular pós-refator (2026-04-30):** cada bloco lógico mora num módulo dedicado dentro de `app/`. As referências que antes eram "linhas X–Y de `app.py`" agora são "arquivo X". Linhas internas de cada módulo são curtas o suficiente para Read direto.

- `LogTecnico` → `app/config.py`.
- Helpers Windows (`obter_segundos_ocioso_windows`, `obter_aplicativo_em_foco`, `listar_nomes_apps_visiveis`, `dividir_tempos_por_dia`, `formatar_hhmmss`, etc.) → `app/win32_utils.py`.
- ctypes structs + `DetectorInputSintetico` (hooks low-level v2.6) → `app/hooks_input.py`.
- `EstadoMonitor` + `MonitorDeUso` → `app/monitor.py`.
- `JanelaSubtarefas(tk.Toplevel)` → `app/subtarefas.py`.
- `App(tk.Tk)` (shell principal Tkinter: login, tela principal, botões, auto-update) → `app/app_shell.py`.
- Entrypoint → `main.py` (raiz) ou `app/main.py`.

**Se o problema for cronômetro / sessão / heartbeat**
- Ler em `app/monitor.py`: `MonitorDeUso.iniciar()` / `pausar()` / `retomar()` / `finalizar()` / `zerar_sessao()`.
- Sessão local/offline: `_salvar_estado_local_locked()`, `_carregar_estado_local()`, `_carregar_fila_offline()`, `_tentar_flush_fila_offline()`.
- Status em tempo real no banco: `_atualizar_status_atual_locked()` e `_limpar_status_atual()`.
- Eventos de auditoria: `_inserir_evento()`.

**Se o problema for foco de app / apps abertos / timelines do Dashboard**
- Foco em janela ativa: `_abrir_foco()`, `_fechar_foco()`. **`_acumular_foco_locked()` + `_flush_foco_periodico()` (v2.7+)** acumulam `segundos_em_foco` cumulativo a cada 10s — protege contra crash sem `fim_em`.
- Apps abertos por sessão: `_abrir_intervalo_app_locked()`, `_atualizar_intervalos_apps_locked()`, `_fechar_todos_intervalos_apps_locked()`.
- JSON consumido pelo painel em `usuarios_status_atual`: `_montar_apps_json_locked()`.
- Loop que alimenta tudo isso: `MonitorDeUso._loop()`.

**Se o problema for contagem de tempo trabalhado / ocioso / pausado**
- Regra de acumulação: `_acumular_tempo_ate_agora_locked()`.
- Snapshots numéricos: `_snapshot_locked()`, `obter_estado()`, `obter_segundos_trabalhando()`, `obter_segundos_pausado()`.
- Inserção de relatório final/zerado: `zerar_sessao()` e `finalizar()`.

**Se o problema for detecção de input humano vs sintético (v2.6, Auditoria/anti-clicker)**
- Classe: `DetectorInputSintetico` (antes de `class EstadoMonitor`).
- Instala `SetWindowsHookExW` com `WH_MOUSE_LL` + `WH_KEYBOARD_LL` numa thread dedicada com message loop.
- Lê flag `LLMHF_INJECTED` / `LLKHF_INJECTED` em cada evento — `True` = input veio de software (auto-clicker, macro).
- Acumula em dois `set`s de segundos epoch (idempotente a N eventos/s no mesmo segundo).
- `snapshot_e_limpar()` → usado por `MonitorDeUso._flush_input_stats_locked_free()`, disparado junto do heartbeat (60s).
- Grava em `cronometro_input_stats` (1 linha por bucket). **Não altera `segundos_trabalhando`** — é coleta paralela transparente.
- Inicia no primeiro `iniciar()` de sessão; para no `_ao_fechar` do app.

**Se o problema for janela “Declarar Tarefa” / subtarefas**
- Tela e lista do dia: `JanelaSubtarefas._montar_tela()` e `_recarregar_dados()`.
- Ações da grade: `_nova_subtarefa()`, `_editar_subtarefa()`, `_excluir_subtarefa()`.
- Formulário modal da tarefa: `_abrir_formulario_subtarefa()`.
- Conversões/validação do formulário: `_converter_texto_para_data()`, `_converter_texto_tempo_para_segundos()`, `_validar_nao_travado()`.
- Finalização do dia/relatório enviado: `_montar_relatorio_final()` e `_enviar_e_finalizar()`.
- **Para campos novos no formulário da tarefa**: comece sempre por `_abrir_formulario_subtarefa()`.
- **Status compartilhado da pasta (verde de thumb + download):** no form MEGA, ao selecionar uma pasta lógica, `_carregar_status_pasta()` chama `api.obter_status_pasta()` e mostra (a) linha verde "✓ Thumb já entregue por <nomes>" quando há upload `tipo='thumb'` de OUTRO usuário, e (b) lista "Arquivos disponíveis nesta pasta" (de outros users) com botão 📥 Baixar por arquivo (`MegaUploader.baixar_arquivo` + progressbar/Cancelar). Tudo dentro de `_abrir_formulario_subtarefa_mega`, perto de `_ao_selecionar_pasta`.
- **Canal sem upload MEGA configurado bloqueia criação nova (v3.1.2+):** dispatcher detecta `cfg.upload_ativo=False` E `subtarefa is None` → passa `bloquear_sem_upload=True` pra `_abrir_formulario_subtarefa_legado`. Aviso vermelho em negrito + botão Salvar `state="disabled"`. **Edição de subs existentes (legado pré-MEGA) NÃO bloqueia** — só criação nova. Falha de fetch (`cfg=None`, offline/timeout) NÃO pune.
- **Combo CANAL no formulário legado é cosmético (v3.1.2+):** sempre `state="disabled"`. O `id_atividade` salvo vem de `self._id_atividade` da janela (canal de origem) — trocar o combo nunca afetou nem o tipo de form (legado vs MEGA) nem o canal salvo. Pra trocar canal, fechar e selecionar pelo menu principal. Form MEGA continua tendo troca real via `_ao_trocar_canal`.
- **Formato do título salvo (v2.4+):** `"NUMERO - NOME"` (ex: `"23 - artemis II"`). Ao editar, o app separa no primeiro ` - `. Banco e web recebem apenas o título já montado.
- **Checkbox Drive (v2.4+):** `chk_drive` + `_atualizar_cor_drive()` via `trace_add` em `var_drive`. Vermelho `#e55555` = desmarcado; verde `#4ade80` = marcado. Bloqueio de salvar preservado.
- **Ordenação clicável dos cabeçalhos da grade (v2.7+):** estado interno `_sort_col` / `_sort_dir` / `_lista_base_ordenacao` (lista de 5-tuplas com `sort_keys` tipados). `_alternar_ordenacao_coluna()` faz ciclo triestado (nova → `asc`; mesma `asc` → `desc`; mesma `desc` → restaura ordem padrão original). `_atualizar_indicadores_cabecalhos()` adiciona `↑`/`↓` ao label ativo. `_aplicar_ordenacao()` recria os itens da Treeview. `Atualizar` reseta para o padrão. Linhas de pagamento participam da ordenação mantendo tag verde.
- **Checkbox "Ocultar tarefas pagas" no rodapé (v3.1.2+):** ao lado de "Configurar Pix". Default ligado. Filtra subs com `bloqueada_pagamento=True` na renderização. Persistido em `~/.cronometro_leve_prefs.json` via `app/config.py::carregar_prefs()` / `salvar_pref()`. Linhas de pagamento verdes (📒) seguem aparecendo — só esconde subs travadas.
- **Rodapé da janela (v2.8+):** exibe `Cronometradas | Declaradas` — métrica neutra que NÃO revela o saldo declarável. Consome `cronometrado_hhmmss` (trabalhando + ocioso) e `declarado_ciclo_hhmmss` de `obter_resumo_do_dia`. O `saldo_hhmmss` continua existindo no resumo mas é uso interno (validação backend). **Cronometradas reseta a cada pagamento (2026-05-01):** `obter_segundos_cronometrados_atividade` filtra `cronometro_relatorios.criado_em >= MAX(Pagamentos.data_pagamento)` (do mesmo user+atividade). Sem pagamento = soma todo histórico. Ao excluir um pagamento, o "último pagamento" passa a ser o anterior automaticamente e a soma volta sozinha. Granularidade por dia (DATETIME `criado_em` vs DATE `data_pagamento` com `>=`); horas do mesmo dia do pagamento caem no ciclo novo — aceita aproximação por simplicidade (ver conversa de design).

**Se o problema for login / tela principal / UX do app**
- Login salvo: `_ler_login_salvo()`, `_salvar_login()`, `_tentar_auto_login()`, `_logar()`.
- Montagem da tela principal: `_montar_tela_principal()`.
- Botão principal Iniciar/Pausar/Retomar: `_acao_principal()`, `_iniciar()`, `_pausar()`, `_retomar()`.
- Janela fixa pequena: `_alternar_fixar()`, `_abrir_fixado()`, `_fechar_fixado()`.
- Atualização visual periódica: `_tick_ui()`.

**Se o problema for atividades/canais selecionados**
- Carregamento de canais: `_carregar_atividades()`.
- Combobox e contexto atual: `_definir_combo_por_id_atividade()`, `_obter_id_atividade_selecionada()`, `_obter_contexto_atividade_ativa()`.

**Se o problema for auto-update**
- Ler `App._verificar_atualizacao()` + `_verificar_atualizacao_periodica()`.
- Em v3.0+ usa `MonitorDeUso.pausar_e_preservar_sessao()` antes do restart (não zera mais — sessão é restaurada automaticamente como PAUSADA).
- Se envolver perda de horas no restart, conferir `MonitorDeUso.pausar_e_preservar_sessao()` e `obter_dados_sessao_pendente_do_usuario` (auto-restore).
- **`pausar_e_preservar_sessao()` força persistência mesmo OCIOSO (bug #19):** `pausar()` tem early-return quando a situação é "ocioso"; sozinho ele não consolidava nada ao fechar/logout/auto-update com o PC parado. Agora `pausar_e_preservar_sessao()`, após o `pausar()`, chama `_upsert_relatorio_parcial()` + (sob lock) `_salvar_estado_local_locked()` + `_atualizar_status_atual_locked()` de forma idempotente.

**Se o problema for declaração que recusa/libera horas erradas (validação anti-fraude)**
- A janela "Declarar Tarefa" agora recebe `monitor` e, antes de validar, chama `JanelaSubtarefas._sincronizar_e_obter_adicional()` → faz `monitor.sincronizar_relatorio_parcial()` (flush da sessão no banco) e passa `segundos_monitorados_adicionais=0`. O **banco é a fonte autoritativa**. Isso evita a **dupla contagem** (banco já inclui o parcial flushado + somar a sessão de novo → liberava horas a mais, bug #20) e a **recusa de horas recém-trabalhadas** (valor da sessão congelava na abertura da janela, bug #18). `declaracoes_dia.py::_validar_tempo_contra_monitoramento` é inalterado (recebe adicional=0). Sem monitor (testes), cai no snapshot estático.
- **Foco por janela acumula em float (bug #21):** `_segundos_em_foco_atual` é float; `_acumular_foco_locked` faz `+= delta` (antes `+= int(delta)` truncava cada tick de ~0,2s pra 0). Conversão pra int só ao gravar no banco.
- **Upsert do relatório parcial é serializado por lock próprio (bug #22):** `_upsert_relatorio_com_snapshots` faz `SELECT→UPDATE/INSERT` sem UNIQUE KEY no banco. Para não criar linha duplicada (que dobraria horas) quando dois flushes correm juntos (loop de 5min + flush sob demanda da declaração/fechamento), o corpo do worker roda dentro de `self._trava_upsert_relatorio` (lock **separado** de `self._trava` — nunca bloqueia o loop principal). **Não** chamar `_upsert_relatorio_com_snapshots` segurando esse lock.
- **Update "não atualiza sozinho na máquina do user" (v3.1.2+):** primeiro suspeito é `.bak` antigo travado na pasta — ver armadilha #33. Limpeza preventiva via `_limpar_bak_residuais()` em `app/main.py` roda em todo `main()` (frozen). Como confirmação manual: pedir pro user fechar o app, apagar `CronometroLeve.exe.bak` (e `_novo.exe` residual) da pasta do exe, reabrir. Auto-update compara só `Content-Length` (HEAD no GitHub raw) — se algum dia o build tiver byte-equivalente, não detecta diff (não foi observado em prática).

**Armadilhas específicas do desktop**
- Quase tudo que mexe em estado do monitor precisa respeitar `with self._trava:` em `MonitorDeUso` (em `app/monitor.py`).
- UI Tkinter não deve bater no banco diretamente; o padrão é usar `_rodar_em_background()` / `_executar_em_background()`.
- Em bugs de subtarefa, normalmente o fluxo real passa por `JanelaSubtarefas` (em `app/subtarefas.py`) + `declaracoes_dia.py` juntos.
- **`Pagamentos` não tem coluna `user_id`** — a FK é `id_usuario` (int). Queries devem fazer `JOIN usuarios u ON u.id_usuario = p.id_usuario WHERE u.user_id = %s`. Também não tem `id_atividade` (essa coluna vive em `pagamento_abatimentos`).
- **Formulário legado sempre bloqueado (v4.0+):** o dispatcher `_abrir_formulario_subtarefa` agora passa `bloquear_sem_upload=True` em **todos** os caminhos que levam ao formulário legado (sem credenciais, fetch falhou, canal sem `upload_ativo`, edição de sub antiga). Toda declaração de tarefa deve passar pelo formulário MEGA com o botão "Enviar Arquivos". O legado abre apenas como tela informativa bloqueada com aviso vermelho.
- **Auto-criação de pasta remota no MEGA (v4.0+):** antes do upload, `_iniciar_upload_mega` verifica se a pasta remota completa (`/raiz/pasta_logica/user_id/`) existe via `pasta_existe()`. Se não existir, cria automaticamente com `criar_pasta()` (`mega-mkdir -p`, idempotente). Substituiu o comportamento anterior que marcava a pasta como inativa e levantava `ErroPastaMegaInexistente`.
- **Sanitização de nomes de pasta MEGA (v4.0+):** dupla — PHP (`mega_normalizar_nome_pasta` em `_comum.php`) remove `"<>|?*:` na criação; Python (`_sanitizar_caminho_mega` em `mega_uploader.py`) sanitiza todos os args de `_run_mega` + `pasta_remota` em `upload_arquivo` na execução. Aspas duplas viram apóstrofo, demais proibidos são removidos. **(2026-06-06) Python passou a remover também `% & ^`** (metacaracteres do cmd.exe — `cmd /c "..."`); `:` e `\` NÃO são removidos no Python (já existem em pastas reais no MEGA). **Armadilha resolvida (auditoria #28-#31):** essa sanitização era aplicada de forma inconsistente — a sync (`mega_sync.py`) comparava nome CRU do banco vs nome SANITIZADO no MEGA → inativava pastas com `?`/`"` (sumiam de "Selecionar existente"); e o download sanitizava o caminho mesmo quando o MEGA tinha o caractere físico → "Couldn't find". Fix: `mega_sync` agora casa contra nome cru **OU** sanitizado; `baixar_arquivo`/`baixar_pasta` têm `sanitizar=bool` e `subtarefas._op` tenta candidatos (sanitizado/cru × com/sem subpasta `/<user_id>/`). **(2026-06-08, auditoria #32) Inativação automática DESLIGADA:** o casamento por nome NÃO sobrevive a renome manual no MEGA (editor adiciona "THUMB BAIXADO", corrige digitação) → a sync inativava pasta real. Agora `app/mega_sync.py::INATIVAR_AUTOMATICO=False` (sync vira não-destrutiva, só loga) **e** o endpoint `desktop_marcar_pastas_logicas_inativas_lote.php` é no-op no servidor (protege apps antigos). Exclusão real de pasta segue pelo endpoint **unitário** `desktop_marcar_pasta_logica_inativa.php`. Esconder pasta apagada no MEGA passa a ser manual.
- **Lista "Selecionar existente" colorida (v4.0.5+):** `desktop_obter_config.php` devolve por pasta o flag `thumb_entregue` (existe upload concluído de tipo `thumb` de QUALQUER usuário, via `mega_campos_upload.tipo`). No app (`app/subtarefas.py`), o helper `_inserir_item_pasta` pinta a linha de **verde** quando `thumb_entregue` OU é tarefa do próprio user (`status_visual` em_andamento/concluida), **cinza** quando paga; adiciona a marca "✓ thumb feita". Altura do Listbox = `min(10, max(5, n))`.
- **Status de erro da sync MEGA + botão "Copiar erro" (v4.0.2+):** em `JanelaSubtarefas._aplicar_estado_mega_sync_na_ui` (`app/subtarefas.py`), no estado `erro` a mensagem do rótulo é cortada em 80 chars, mas a completa fica em `self._msg_erro_completa_mega`; o botão `_btn_copiar_erro_mega` ("Copiar erro") aparece só nesse estado (`_mostrar_btn_copiar_erro_mega`) e copia a mensagem inteira via clipboard. Quando `_eh_erro_de_hora_mega()` detecta `certificate_verify_failed` (relógio do PC errado), troca o texto técnico por aviso pedindo ajustar data/hora do Windows.
- **Cronômetro é neutro (v3.1.3+):** o usuário pode declarar as horas cronometradas em qualquer atividade dele, não importa em qual atividade ele cronometrou. A validação anti-fraude (`_validar_tempo_contra_monitoramento`) compara `monitorado_total_user − abatimento_total_user >= declarado_total_user + segundos_novos`, sem filtrar por `id_atividade`. Antes era por atividade, gerando o erro `"Não existe tempo monitorado disponível no cronômetro para esta atividade."` quando o user cronometrava em uma e tentava declarar em outra. Painel (`editar.php`) já era global — o fix alinhou o desktop. **Consequência:** `pagamento_abatimentos` continua com snapshot por `(user_id, id_atividade)` para rastro histórico, mas funcionalmente o reset do ciclo é por usuário; pode haver descasamento (cronometrado em ativ X, declarado em ativ Y) — é esperado.
- Em bugs de Dashboard originados no desktop, quase sempre a origem está em:
  - `cronometro_relatorios` (`finalizar()` / `zerar_sessao()`)
  - `usuarios_status_atual` (`_atualizar_status_atual_locked()`)
  - `cronometro_foco_janela` / `cronometro_apps_intervalos` (`_abrir_foco()` / `_atualizar_intervalos_apps_locked()`)
- **`DetectorInputSintetico` (v2.6):** callbacks dos hooks PRECISAM manter referência forte (`self._cb_mouse_ref` / `self._cb_kbd_ref`). Se o garbage collector coletar esses refs o Windows crasha o processo. A thread do hook precisa de message loop (`GetMessageW`) — sem isso os hooks low-level param de receber eventos em ~300ms.

### Web — Frontend (`painel/`)

> **Refatoração SPA → multipágina CONCLUÍDA (branch `dev`, Partes 0-10).** Cada aba virou página própria; o `index.php` é o Dashboard. **Parte 10:** `painel.js::trocarAba` enxugado — só trata `abaDashboard`/`abaUsuarios`/`abaGestaoUsuario` (as únicas invocadas); `obterAbaVisivel`/`rerenderizarAbaAtual` foram mantidas (servem o botão "Recarregar" nas páginas dedicadas). `aba-timeline.js` segue como placeholder reservado (nunca foi carregado). **Parte 0:** cabeçalho/menu/rodapé comuns extraídos para `_layout/` (`topo.php`, `fim_conteudo.php`, `rodape.php`) — toda página inclui esses partials. **Migradas p/ página própria:** Log (`log.php`, P1), Relatório (`relatorio.php`, P2), Gerenciar Tarefas (`gerenciar-tarefas.php`, P3), Credenciais (`credenciais.php`, P4 — modais/`aba-credenciais.js` seguem TAMBÉM no index pois a Gestão do Usuário ainda os usa; resolver na P8), Canal/Atividades (`canal.php`, P5 — `modalNovaAtividade`/`aba-atividades.js` seguem TAMBÉM no index pois o atalho do Dashboard usa), Auditoria (`auditoria.php`, P6 — `aba-auditoria.js` segue TAMBÉM no index pois expõe o cache de flags ao Dashboard/Gestão; modalAppSuspeito foi pra auditoria.php), MEGA (`mega.php`, P7 — migração limpa, seção + `aba-mega.js` inteiros, sem modais/acoplamento), Usuários+Gestão (`usuarios.php`, P8 — leva consigo aba-usuarios/credenciais/auditoria/gerenciar-tarefas + 4 modais; deep-link `?user=<id>` abre a Gestão; gráficos do Dashboard e Auditoria navegam pra cá). **Sobra no index só o Dashboard** (+ os atalhos "+ Adicionar Usuário/Canal" que mantêm modalAdicionarUsuario/modalNovaAtividade + aba-usuarios/atividades + aba-auditoria p/ flags + aba-graficos). **Navegação:** links do menu são URLs reais — seção já migrada → sua página (ex.: `./log.php`); seção ainda no monolito → `./index.php?aba=<id>`. `painel.js` só intercepta o clique (modo SPA) se a seção existir na página atual, senão deixa o href navegar; no boot lê `?aba=` p/ abrir a aba certa e pula o boot do Dashboard em páginas dedicadas.

| Arquivo | Cobertura |
|---|---|
| `_layout/topo.php` | **(Parte 0)** Cabeçalho compartilhado: guard de sessão + `<head>` + topbar/sidebar (menu) + abre `<main>`. Params da página: `$tituloPagina`, `$subtituloPagina`, `$abaAtiva`, `$cssExtra`. |
| `_layout/fim_conteudo.php` | **(Parte 0)** Fecha `<main>`/rodapé/container (vem ANTES dos modais — z-index). |
| `_layout/rodape.php` | **(Parte 0)** Scripts base (bootstrap+chart.js) + `$scriptsAba` da página + `painel.js` (núcleo) + toggle mobile + fecha `</body>`. |
| `index.php` | Página **Dashboard** (home). **(Parte 9)** Todas as outras abas já viraram páginas próprias — sobra só `#abaDashboard` (cards + gráficos em `#areaGraficos`). Mantém os atalhos "+ Adicionar Usuário/Canal" (modais + `aba-usuarios.js`/`aba-atividades.js`) e `aba-auditoria.js` (flags dos gráficos) + `aba-graficos.js`. Usa os partials de `_layout/`. |
| `log.php` | **(Parte 1)** Página dedicada do Log de Atividades (usa `_layout/` + `js/aba-log-atividades.js`). |
| `relatorio.php` | **(Parte 2)** Página dedicada do Relatório de Tempo Trabalhado (`js/aba-relatorio.js`). Relatório agregado por período — sem paginação de linhas. |
| `gerenciar-tarefas.php` | **(Parte 3)** Página dedicada de Gerenciar Tarefas Declaradas + modal de edição (`js/aba-gerenciar-tarefas.js`). Lista paginada (`page`/`per_page`); o JS ganhou fallback local de paginação p/ não depender do `aba-usuarios.js`. |
| `credenciais.php` | **(Parte 4)** Página dedicada de Credenciais e APIs + modais `modalGerenciarModelos`/`modalSubstituirValor` (`js/aba-credenciais.js`). Esses modais e o script continuam DUPLICADOS no index.php porque a Gestão do Usuário depende deles (até a P8). |
| `canal.php` | **(Parte 5)** Página dedicada de Canais (Atividades) + `modalNovaAtividade` (`js/aba-atividades.js`, que ganhou auto-load standalone). O modal e o script continuam no index.php porque o atalho "+ Adicionar Canal" do Dashboard depende deles. |
| `auditoria.php` | **(Parte 6)** Página dedicada de Auditoria (usuários com flag + CRUD apps suspeitos) + `modalAppSuspeito` (`js/aba-auditoria.js`, com auto-init standalone). O script continua DUPLICADO no index.php porque expõe o cache de flags (`obterFlagUsuarioSync`/`garantirFlagsMap`/`renderizarAlertasNaGestao`) usado pelo Dashboard (graficos) e pela Gestão (usuarios). Link "Ver aba Auditoria" da Gestão agora navega p/ auditoria.php. |
| `mega.php` | Página **MEGA · Pastas lógicas** (só o bloco de pastas/vídeos). **Split em 2026-06-05:** a config foi separada pra `mega-campos.php`. Mantém `<section id="abaMega">` — o boot do aba-mega.js dispara em qualquer página com esse id e cada bloco se protege pelo próprio elemento, então só roda o que existe. Carrega `js/aba-mega.js?v=12`. **Armadilha (corrigida 2026-06-08):** `carregarCanais()` em `aba-mega.js` NÃO pode dar early-return quando `tbodyMegaCanais` falta — essa tabela só existe em `mega-campos.php`, mas o **filtro de canais do bloco Pastas** (em `mega.php`) depende de `estado.canais` que essa função preenche. Antes ela abortava e o filtro "Todos os canais" vinha vazio. Agora busca os canais sempre e só pula a escrita na tabela ausente. |
| `mega-campos.php` | Página **MEGA · Campos de upload** (split de 2026-06-05). Ordem: **campos por usuário** (seleciona só o usuário → `#megaCamposPorCanal` renderiza TODOS os canais dele agrupados, cada canal com sua mini-tabela de campos + "+ Novo campo" próprio; sem seletor de canal) + botão **"Usar modelo existente"** → modal `#modalUsarModelos` com checkboxes de **modelos** E **canais** (cria cada modelo em cada canal marcado, cartesiano, com dedup por label/canal) → **tabela CRUD de Modelos inline** (`#tbodyMegaModelos`: editar/excluir/+novo, substituiu os popups `window.prompt`) → **Configuração por canal** (no fim). Link "← Pastas lógicas" no topo. Tem `<section id="abaMega">`. |
| `usuarios.php` | **(Parte 8)** Página dedicada de Usuários + sub-tela Gestão do Usuário. Carrega `aba-usuarios.js`+`aba-credenciais.js`+`aba-auditoria.js`+`aba-gerenciar-tarefas.js` e os 4 modais (Adicionar Usuário, Gerenciar Modelos, Substituir Valor, Editar Tarefa). `aba-usuarios.js` ganhou auto-init standalone + **deep-link `?user=<id>`** (abre a Gestão). Os gráficos do Dashboard (`aba-graficos.js`) e a Auditoria (`aba-auditoria.js`) navegam p/ `usuarios.php?user=<id>` quando `#abaGestaoUsuario` não existe na página atual. `modalAdicionarUsuario`+`aba-usuarios.js` seguem TAMBÉM no index (atalho do Dashboard). |
| `login.php`, `logout.php` | Autenticação standalone. |
| `js/painel.js` | Núcleo: `requisitarJson`, utilidades (`mostrarAlerta` etc.), navegação (intercepta SPA só se a seção existe; deep-link via `?aba=`), status ao vivo, Dashboard. |
| `js/aba-graficos.js` | ECharts: timelines, donuts, comparativos. **~2080 linhas — Grep primeiro.** Containers ECharts são **estáticos** dentro de `garantirEstruturaSimplificada()` em `#areaUsuarioSelecionadoGraficos`. **Recorte atual vem SEMPRE de `_diaAtualmenteExibido()`** — setas ← → disparam `atualizarGraficos()` (fetch novo), filtro manual ativa `_modoTotalPeriodo`. Estado de "Carregando…" via `_indicarCarregandoGraficos()` / `_pararCarregandoGraficos()`. |
| `js/aba-usuarios.js` | Gestão de Membros: CRUD, página de Gestão (Resumo + pagamentos + tarefas declaradas). |
| `js/aba-gerenciar-tarefas.js` | Lista global de subtarefas com filtros e modal de edição. |
| `js/aba-atividades.js` | CRUD de Canais (chama tabela `atividades` no banco). |
| `js/aba-relatorio.js` | Relatório com export CSV (`;` + BOM UTF-8). |
| `js/aba-credenciais.js` | Aba Credenciais e APIs: CRUD de modelos + gestão de credenciais por usuário (cifradas) + seção "APIs globais ativas" (`#boxApisGlobais`/`#listaApisGlobais`) listando modelos com `aplicar_novos_usuarios=1` e botão "Remover global". Integração automática com Gestão do Usuário via `data-user-id`. |
| `js/aba-auditoria.js` | **Aba Auditoria (v2.6):** CRUD de apps suspeitos + lista global de usuários com flag 🚩. Expõe cache compartilhado de flags (`PainelAbaAuditoria.obterFlagUsuarioSync`) reusado pelo Dashboard e Gestão. Renderiza card "Input automatizado detectado" + gráfico ECharts na Gestão do Usuário. |
| `js/aba-mega.js` | **Aba MEGA (admin) — carregado em `mega.php` E `mega-campos.php`** (split 2026-06-05; os blocos se protegem pelos próprios elementos). Tem **CRUD inline de Modelos** (`renderizarTabelaModelos`/`linhaModeloEditavel`/`bindModelosActions`/`novoModelo` em `#tbodyMegaModelos`) que substituiu os popups `window.prompt` (`gerenciarModelos`/`salvarLinhaComoModelo` removidos). Blocos: (1) config de pasta raiz no MEGA + flag `upload_ativo` por canal; (2) CRUD inline de campos de upload por `user_id + id_atividade` — **com `<select>` de tipo (Vídeo/Projeto/Thumb/Texto/Outro)** propagado pro payload e pros modelos; (3) pastas lógicas cadastradas com **link clicável pro MEGA** (abre nova aba), **status de publicação** (Publicado/Pendente com badge + linha verde), **botões "Publicado"/"Cancelar"**, **filtros** (busca texto, status, canal). Edição via linha inline (sem modal). Expõe `window.PainelAbaMega.renderizarAbaMega()`. |
| `js/aba-log-atividades.js` | **Log de Atividades (Parte 1 — usado em `log.php`):** log geral de todas as ações do servidor com filtros (entidade, ação, executor, busca, período), paginação, e modal de detalhe (dados antes/depois em JSON). Expõe `window.logAtividadesCarregar()`. **Auto-carrega** quando em página dedicada (sem `#abaDashboard`); no index é sob demanda. |
| `js/aba-timeline.js` | **PLACEHOLDER (~25 linhas).** Apenas registra `window.PainelAbaTimeline` com funções vazias. Não há aba "Timeline" funcional ainda — só esqueleto reservado. |
| `css/painel.css` | Tema RK Produções dark. |

### Web — Backend (`painel/commands/`)

```
_comum/
  resposta.php   — responder_json($ok, $msg, $dados, $status). debug_ativo() só via APP_DEBUG=1 ENV.
  auth.php       — verificar_sessao_painel(), bcrypt, tokens "lembrar" (.tokens.json), bloqueio (.tentativas.json).
  env.php        — carregar_env_local(): lê painel/.env ou ./.env. ENV real tem precedência.
  cripto.php     — libsodium secretbox. obter_chave_mestra_secreta(), cifrar_segredo(), decifrar_segredo(), obter_chave_cliente_fixa(), cifrar_para_cliente(), gerar_mascara_parcial().
  credenciais_upsert.php — helpers de upsert cifrado por (id_modelo, user_id), herança de credenciais globais para novos usuários, e gerência de status em massa por usuário. preparar_stmt_upsert_credencial(), upsert_credencial_usuario_cifrada(), listar_credenciais_globais_para_herdar(), herdar_credenciais_globais_para_usuario(), revogar_credenciais_de_usuario(), reativar_credenciais_revogadas_de_usuario().
  rate_limit.php — janela deslizante com flock + arquivos JSON. rate_limit_proteger(), rate_limit_consumir(), obter_ip_cliente(). Storage: painel/logs/ratelimit/ (ignorado).
  pix.php        — pix_validar(string): {tipo,valor}. CNPJ(14d+DV), celular BR(10–11d com DDD), e-mail. Recusa CPF e formatos aleatórios. Espelho de `app/validador_pix.py` (manter sincronizado).
  usuarios_estrutura.php — usuarios_garantir_chave_pix(): ALTER TABLE usuarios ADD COLUMN chave_pix VARCHAR(255) NULL idempotente (introduzido 2026-05-01).
  log_atividades.php — log_registrar($pdo, entidade, acao, descricao, dados_depois, dados_antes, id_entidade, executor): registra ação na tabela `log_atividades`. log_atividades_garantir_tabela() cria a tabela lazy. log_atividades_cleanup($pdo, 60) remove registros > 60 dias (LIMIT 5000/request). Nunca quebra a operação principal (try/catch silencioso).
  .htaccess      — bloqueia .json, .bak, .old, .env via HTTP.
conexao/
  conexao.php    — PDO MySQL via ENV (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS) com fallback. VERSIONADO com porta 3306. Local usa 3307 via skip-worktree.
  testar.php     — health check (auth).
status/          — TODOS PÚBLICOS (sem auth) — usados pelo app desktop:
  atualizar.php (UPSERT heartbeat), listar.php (status ao vivo), horas_mes.php
graficos/graficos.php          — dados de TODOS os charts ECharts
relatorio/tempo_trabalhado.php — relatório com valor_pendente = valor_estimado − total_pago.
                                 **Horas TRABALHADAS lidas de `cronometro_relatorios` (não `registros_tempo`,
                                 que é legada/vazia)** — antes lia da legada e "Trabalhado" saía 00:00:00 pra
                                 todos (bug #17). Agrupa por COALESCE(referencia_data, DATE(criado_em)).
atividades/                    — listar, criar, editar, excluir, alterar_status
atividades_subtarefas/         — listar (inclui agregados de horas/pagamentos), editar
usuarios/                      — listar, listar_ativos, criar, editar, excluir, atualizar_status,
                                 alternar_visibilidade_dashboard (toggle ocultar_dashboard, payload {user_id, ocultar_dashboard:0|1}).
                                 criar.php herda credenciais com aplicar_novos_usuarios=1.
                                 atualizar_status.php sincroniza credenciais com status (ativa↔inativa = ativo↔revogado em massa).
                                 excluir.php é soft-delete (status_conta='inativa'); também revoga credenciais.
                                 listar.php retorna `chave_pix` (string|null) — coluna criada lazy via `usuarios_garantir_chave_pix()`.
                                 api/                       — CONSUMO PELO DESKTOP (auth: user_id + chave do usuário, mesmo
                                                              padrão de credenciais/api/_auth_cliente.php):
                                   obter_pix.php  — GET, retorna {chave_pix, tipo} do próprio user.
                                   salvar_pix.php — POST {chave_pix:"..."}, valida server-side via
                                                    `_comum/pix.php#pix_validar()`. Vazio/null = limpa.
                                                    Recusa CPF (mensagem dedicada) e qualquer formato fora de
                                                    CNPJ(14d+DV) / celular BR(10–11d) / e-mail.
pagamentos/
  criar.php / editar.php / excluir.php / listar_por_usuario.php
  _aplicar_pagamento.php — funções compartilhadas: pagamento_aplicar(), pagamento_desvincular(), pagamento_reprocessar_todos()

(fora de commands/, na raiz de painel/:)
painel/baixar_app.php  — serve CronometroLeve.exe para auto-update (público, sem auth)
credenciais/                   — CRUD administrativo (auth painel):
  listar_modelos.php, salvar_modelo.php, excluir_modelo.php (5 protegidos)
  listar_por_usuario.php, salvar_valor.php, revogar_valor.php
  remover_global.php           — desliga aplicar_novos_usuarios=0 + revoga em todos
                                 os usuários (status='revogado'). Em transação.
  api/                         — CONSUMO PELOS APPS (auth: user_id + chave do usuário):
    _auth_cliente.php          — aceita Authorization: Bearer user:chave, X-User-Id+X-User-Chave ou query string. Rate limit 4-bucket.
    listar.php                 — lista identificadores preenchidos do usuário autenticado
    obter.php?identificador=X  — decifra com MASTER → recifra com CLIENT → entrega base64+nonce. Atualiza ultimo_acesso_em.
auditoria/                     — Auditoria de apps suspeitos (v2.6, auth painel):
  listar_apps_suspeitos.php    — GET (?incluir_inativos=1 opcional)
  salvar_app_suspeito.php      — POST criar/editar (reativa se nome_app já existir inativo)
  excluir_app_suspeito.php     — POST soft-delete (ativo=0)
  flags_usuarios.php           — GET cruza auditoria_apps_suspeitos com cronometro_apps_intervalos via LIKE '%substring%'. Retorna por usuário: tem_flag_7dias + apps_detectados[] com sessões, horas, primeiro/último uso. Opcional ?user_id=X.
  input_stats.php              — GET agrega cronometro_input_stats por dia (?user_id=X&dias=15). Retorna humano/sintético por dia + totais + percentual_sintetico.
mega/                          — Módulo MEGA (Fase 1 — config admin + endpoints desktop). Tabelas auto-criadas
                                 via mega_garantir_estrutura() em _estrutura.php (chamado por todos os endpoints).
                                 _estrutura.php             — DDL idempotente (CREATE TABLE IF NOT EXISTS) das 5
                                                              tabelas mega_* + INSERT IGNORE dos 2 modelos de
                                                              credencial (mega_email, mega_password) em
                                                              credenciais_modelos. **Coluna `tipo` (bloco G,
                                                              ALTER idempotente):** em mega_campos_upload e
                                                              mega_campos_modelos, VARCHAR(20) default 'outro',
                                                              valores video/projeto/thumb/texto/outro — classifica
                                                              o conteúdo do campo (base do "verde compartilhado"
                                                              de thumb e do download por tipo).
                                 _comum.php                 — Helpers: mega_normalizar_nome_pasta($num,$titulo)
                                                              produz "NN - Titulo" canônico; mega_normalizar_tipo()
                                                              restringe ao conjunto MEGA_TIPOS_CAMPO; mega_normalizar_extensoes()
                                                              limpa lista CSV de extensões;
                                                              mega_user_pertence_atividade(pdo, user_id, id_atividade)
                                                              consulta atividades_usuarios pra autorização (defesa
                                                              contra IDOR — ver armadilha #29);
                                                              mega_user_pertence_pasta_logica(pdo, user_id, id_pasta)
                                                              variante que deriva o id_atividade da pasta lógica.
                                 (admin — auth painel)
                                 canal_config_listar.php    — GET tabela LEFT JOIN atividades+mega_canal_config (lista
                                                              canais não cancelados, mesmo sem config).
                                 canal_config_salvar.php    — POST upsert {id_atividade, nome_pasta_mega, upload_ativo}.
                                 campos_listar.php          — GET (?user_id=X&id_atividade=Y&incluir_inativos=1) campos
                                                              de upload exigidos.
                                 campos_salvar.php          — POST upsert UM campo (id_campo opcional). Inclui
                                                              `tipo` (video/projeto/thumb/texto/outro). campos_listar
                                                              e campos_modelos_* também leem/gravam `tipo`.
                                 campos_excluir.php         — POST soft-delete (ativo=0).
                                 campos_modelos_listar.php  — GET templates globais de campo (?incluir_inativos=1 opcional).
                                 campos_modelos_salvar.php  — POST upsert template; UNIQUE nome_modelo (colisão = 409).
                                 campos_modelos_excluir.php — POST soft-delete do template.
                                 pasta_logica_listar.php    — GET (?id_atividade=Y opcional). Retorna link_mega,
                                                              video_publicado, publicado_em.
                                 pasta_logica_marcar_publicado.php — POST {id_pasta_logica, publicado:0|1}.
                                                              Marca/desmarca vídeo como publicado no YouTube.
                                                              Registra no log de atividades.
                                 (desktop — auth user_id+chave via _auth_cliente.php de credenciais/api)
                                 pasta_logica_listar_para_sync.php — GET todas as pastas ativas com nome_pasta_mega
                                                              (sem IDOR). Usado pelo script sync_mega_links.py.
                                 pasta_logica_salvar_link.php — POST {id_pasta_logica, link_mega}. Salva link
                                                              público do MEGA gerado por mega-export.
                                 desktop_obter_config.php   — GET ?id_atividade=Y → {upload_ativo, pasta_raiz_mega,
                                                              campos_exigidos[], pastas_logicas[]}. Sem config retorna
                                                              upload_ativo=false (preserva fluxo legado).
                                                              **Conta "adm" (2026-06-08):** campos_exigidos NÃO vem de
                                                              mega_campos_upload — vem de TODOS os mega_campos_modelos
                                                              ativos, em qualquer canal, com obrigatorio SEMPRE false.
                                                              Assim modelo/canal novo já aparecem pra adm sem
                                                              reconfigurar e nada é exigido dela. Demais users seguem
                                                              o fluxo normal por user+canal.
                                 desktop_criar_pasta.php    — POST cria pasta lógica com nome canônico "NN - Titulo".
                                                              Reativa se existir desativada; retorna 409 se ativa
                                                              colidir.
                                 desktop_registrar_upload.php — POST registra metadado de upload (criar/atualizar).
                                                                Não armazena arquivo — só status.
                                 desktop_obter_dados_subtarefa.php
                                                              — GET ?id_subtarefa=X → {pasta_raiz_mega,
                                                                pasta_logica:{id,nome,ativo}, arquivos[],
                                                                outras_subtarefas_na_pasta}. Usado por
                                                                _excluir_subtarefa pra saber o que limpar
                                                                no MEGA, e pelo form em modo edição pra
                                                                hidratar arquivo_remoto_anterior.
                                 desktop_obter_status_pasta.php
                                                              — GET ?id_pasta_logica=X → {id_atividade, nome_pasta,
                                                                pasta_raiz_mega, arquivos_pasta[]}. Status
                                                                COMPARTILHADO da pasta (por pasta, não por user):
                                                                lista o upload MAIS RECENTE por (user_id,
                                                                nome_campo) — JOIN com MAX(id_upload) descarta
                                                                re-uploads antigos cujo arquivo já saiu do MEGA —
                                                                de QUALQUER usuário, cada um com `tipo` (subquery
                                                                mega_campos_upload por user+ativ+label=nome_campo)
                                                                e `caminho_remoto` já montado. IDOR via
                                                                mega_user_pertence_pasta_logica. Alimenta no
                                                                desktop o "verde compartilhado" (thumb de outro
                                                                user) e a lista de download direto.
                                 desktop_marcar_pasta_logica_inativa.php
                                                              — POST {id_pasta_logica} → soft-delete da
                                                                pasta lógica. Chamado quando o desktop
                                                                detecta sincronia rompida (pasta sumiu
                                                                no MEGA) ou quando uma exclusão de sub
                                                                resulta em pasta vazia.
                                 desktop_marcar_pastas_logicas_inativas_lote.php
                                                              — POST {ids_pasta_logica:[...]} → versão batch
                                                                pra rotina de sync periódico do desktop.
                                                                Defesa IDOR: filtra IDs que pertencem a
                                                                canais do user; alheios voltam em
                                                                `ids_ignorados`. Limite 1000/chamada.
                                 desktop_pastas_logicas_para_sync.php
                                                              — GET → {canais:[{id_atividade, titulo_atividade,
                                                                pasta_raiz_mega, upload_ativo:true,
                                                                pastas_logicas:[…]}]}. Só canais do user com
                                                                `upload_ativo=1`. Usado pelo desktop pra rodar
                                                                sync MEGA-vs-banco em lote (lista raiz uma vez
                                                                por canal e compara em memória).
                                 desktop_uploads_orfaos_listar.php
                                                              — GET → {pastas:[{id_pasta_logica, …, uploads:[…]}]}
                                                                pra recovery após queda abrupta. Filtra
                                                                `id_subtarefa IS NULL` + status pendente/enviando/
                                                                concluido (ignora `erro`). Agrupado por pasta
                                                                lógica — desktop cria 1 subtarefa aberta por pasta
                                                                e depois faz UPDATE de id_subtarefa em cada
                                                                upload via desktop_registrar_upload.
log_atividades/                — Log geral de atividades do servidor (auth painel):
                                 listar.php     — GET com filtros (entidade, acao, executor, busca,
                                                   data_inicio, data_fim) + paginação. Cleanup automático
                                                   de registros > 60 dias a cada request.
                                 detalhe.php    — GET ?id_log=X retorna dados_antes/dados_depois
                                                   decodificados do JSON.
```

---

## 🗄️ Banco de Dados — Tabelas-chave

| Tabela | O que guarda | Notas |
|---|---|---|
| `usuarios` | Membros: `user_id`, `nome_exibicao`, `nivel`, `valor_hora`, `chave`, `status_conta`, `ocultar_dashboard` | `chave` no formato `rk_XXXXX`. `status_conta` enum `('ativa','inativa','bloqueada')` — `_auth_cliente.php` só aceita `'ativa'` (qualquer outro valor barra com 403); `usuarios/atualizar_status.php` só aceita transições para `'ativa'`/`'inativa'`. `ocultar_dashboard=1` esconde do Dashboard e da lista operacional de campos MEGA, mas continua na aba Usuários e nas demais abas administrativas. `valor_hora` aceita 0. |
| `atividades` | Canais (apesar do nome legacy) | UI mostra como "Canal" |
| `atividades_usuarios` | N:N canal ↔ membro | |
| `atividades_subtarefas` | Declarações de horas | `bloqueada_pagamento` (1=trava), `id_pagamento`, `referencia_data`, `canal_entrega` (legacy: pode vir como `#ID - Nome (status)`) |
| `atividades_subtarefas_historico` | Auditoria JSON | `acao`, `dados_antes`, `dados_depois`, `user_id_executor` |
| `cronometro_sessoes` | Sessões iniciadas | `iniciado_em`, `finalizado_em` |
| `cronometro_eventos_status` | Heartbeats e transições | enum `tipo_evento`: `inicio`/`pausa`/`retorno`/`ocioso_inicio`/`ocioso_fim`/`finalizar`/`heartbeat`/`zerar` |
| `cronometro_relatorios` | Relatórios finalizados | **`referencia_data` = data REAL do trabalho** (não `criado_em`). Fonte do Resumo. **`id_atividade` é gravado NULL (cronômetro neutro) — a coluna DEVE aceitar NULL.** Era `NOT NULL` em produção e travou TODA gravação de horas de ~26/05 a 11/06 (erro 1048 silencioso, auditoria #33); corrigido com `ALTER TABLE cronometro_relatorios MODIFY id_atividade INT NULL`. |
| `cronometro_apps_intervalos` | Apps abertos por sessão | `inicio_em`, `fim_em`, `segundos_em_foco`, `segundos_segundo_plano`, `ultima_atualizacao_em` (auto). **Duração no gráfico (v2.7+)** prioriza `(segundos_em_foco + segundos_segundo_plano)` cumulativo — sobrevive a crash. Cap 20h é último recurso. |
| `cronometro_foco_janela` | Foco de janelas | Base das timelines individuais. **`segundos_em_foco` cumulativo (v2.7+)** atualizado a cada 10s pelo app — sobrevive a crash. `fim_em` continua sendo gravado em fechamentos limpos. Para registros legados (`segundos_em_foco=0`) `graficos.php` mantém fallback de cap 3h. |
| `usuarios_status_atual` | Estado em tempo real | `situacao`, `ultimo_em`. Timeout zumbi: >3min sem heartbeat → "Pausado" |
| `Pagamentos` | Histórico de pagamentos | `data_pagamento`, `valor`, `referencia_inicio`, `referencia_fim`, `travado_ate_data` |
| `pagamento_abatimentos` | **(v2.7+)** Saldo pendente por atividade no momento de cada pagamento — abatimento reversível, hoje usado pelo desktop **somado em todas as atividades do user** para compor o saldo global disponível na validação anti-fraude (v3.1.3+, antes era por atividade) | Chave `(user_id, id_pagamento, id_atividade)`. **Escrito uma única vez** pelo painel em `pagamento_aplicar()` (`_aplicar_pagamento.php::pagamento_registrar_abatimentos`); o catch só engole MySQL errno 1062 (duplicate entry) — outros erros de integridade (FK 1452, NOT NULL 1048) propagam. **Cálculo (v2.8+, janela temporal):** `pendente = monitorado_em_janela − declarado − já_abatido` por atividade, onde `monitorado_em_janela` soma `cronometro_relatorios.segundos_trabalhando` apenas até `MAX(COALESCE(s.concluida_em, s.criada_em))` da última subtarefa concluída daquela atividade. Trabalho cronometrado **após a última declaração** (e antes do pagamento) NÃO é abatido — vira saldo disponível no próximo ciclo. Atividades sem nenhuma declaração ficam sem abatimento. **Imutável após criado** — edição de pagamento NÃO recalcula. Apagado só por `pagamento_desvincular()` quando o pagamento é excluído. Lido pelo desktop em `obter_abatimento_total_atividade(user_id, 0)` (id_atividade=0 = soma todas). Tabela criada via `_garantir_estrutura` no `declaracoes_dia.py` (DDL ainda no Python; PHP só verifica existência via `pagamento_tabela_abatimentos_existe`). **Pendente:** FK `(id_pagamento) → Pagamentos(id_pagamento)` ainda não declarada — aguarda permissão de schema. |
| `declaracoes_dia_itens` | Espelho simples de subtarefas concluídas | Sincronizado por `_sincronizar_item_espelho_da_subtarefa` |
| `registros_tempo` | LEGADO — agregados por dia/situação | Pode estar vazio em instalações novas; algumas queries têm fallback |
| `credenciais_modelos` | Modelos globais (ChatGPT, Gemini, Minimax, Elevenlabs, Assembly, MEGA email, MEGA password) | `identificador` único; **7 modelos protegidos** (`chatgpt`, `gemini`, `minimax`, `elevenlabs`, `assembly`, `mega_email`, `mega_password`) não podem ser excluídos — bloqueio em `excluir_modelo.php` e em `MODELOS_PROTEGIDOS` no `aba-credenciais.js`. `aplicar_novos_usuarios TINYINT(1) DEFAULT 0` indica que o valor global deve ser herdado por usuários cadastrados depois (ligado pelo modo `aplicar_todos=true` de `salvar_valor.php`). |
| `credenciais_usuario` | Valor cifrado por `(id_modelo, user_id)` | `valor_cifrado` MEDIUMBLOB (libsodium), `nonce` 24B, `versao_chave`, `status` ativo/revogado |
| `auditoria_apps_suspeitos` | **(v2.6)** Lista configurável de nomes de processos que disparam alerta | `nome_app` é SUBSTRING (LIKE '%x%'), `ativo` (soft-delete), `motivo`, `criado_por`. Seed inicial com 10 apps (gs-auto-clicker, autohotkey, tinytask, etc). |
| `cronometro_input_stats` | **(v2.6)** Agregado por bucket de 60s de input humano vs sintético | `segundos_input_humano` / `segundos_input_sintetico` detectados via flag `LLMHF_INJECTED` do Windows. Coleta só começa em clientes v2.6+. Indexada por `(user_id, referencia_data)`. |
| `cronometro_finalizacoes` / `cronometro_finalizacoes_subtarefas` | **LEGADO** | Existem no banco mas nenhum endpoint do painel ou função do desktop (pacote `app/`) grava nelas atualmente; a única referência viva é `painel/commands/atividades/excluir.php`. Tratar como tabelas órfãs — não usar em features novas (use `cronometro_relatorios`). |
| `mega_canal_config` | **(Fase 1 MEGA)** Config por canal: pasta raiz no MEGA + flag `upload_ativo`. | Chave: `id_atividade UNIQUE`. Tabela auto-criada por `mega_garantir_estrutura()` em `painel/commands/mega/_estrutura.php`. Sem linha = upload não exigido (fluxo legado preservado no desktop). |
| `mega_campos_upload` | **(Fase 1 MEGA)** Campos de upload exigidos por `user_id + id_atividade`. | Sem UNIQUE composto (admin pode ter vários campos por par). Soft-delete (`ativo`). Colunas: `label_campo`, **`tipo`** (`video`/`projeto`/`thumb`/`texto`/`outro`, default `outro` — base do "verde compartilhado" de thumb e do download por tipo no desktop), `extensoes_permitidas` (CSV `mp4,zip`), `quantidade_maxima`, `obrigatorio`, `ordem`. |
| `mega_pasta_logica` | **(Fase 1 MEGA)** Índice canônico das pastas lógicas do vídeo. | `UNIQUE (id_atividade, nome_pasta)` — duplicidade só dentro do mesmo canal. `nome_pasta` no formato `"NN - Titulo"` (montado por `mega_normalizar_nome_pasta`). Soft-delete (`ativo`); `desktop_criar_pasta.php` reativa se existir desativada. |
| `mega_uploads` | **(Fase 1 MEGA)** Metadados de uploads (auditoria, sem armazenar arquivo). | Status enum `pendente/enviando/concluido/erro`. `id_subtarefa NULL` no início; preenchido após `_enviar_e_finalizar`. Endpoint `desktop_registrar_upload.php` faz INSERT (id_upload=0) ou UPDATE (id_upload>0) restrito ao próprio user_id. Uploads com `id_subtarefa IS NULL` viram candidatos a recovery via `desktop_uploads_orfaos_listar.php` (queda abrupta / fechamento sem salvar). |
| `mega_campos_modelos` | **(MEGA modelos)** Templates globais reutilizáveis de campos de upload. | UNIQUE `nome_modelo`. Colunas: `label_campo`, **`tipo`** (mesmo conjunto de `mega_campos_upload`), `extensoes_permitidas`, `quantidade_maxima`, `obrigatorio`, `ordem`, `ativo`. **Não cria campo automaticamente em ninguém** — admin aplica linha por linha em `mega_campos_upload` (apenas atalho de preenchimento). Sem FK pro `mega_campos_upload`. Soft-delete via `ativo`. |
| `log_atividades` | **(Log geral)** Registro de TODAS as ações do servidor (criar/editar/excluir em qualquer entidade). | Auto-criada lazy via `log_atividades_garantir_tabela()` em `painel/commands/_comum/log_atividades.php`. Colunas: `id_log`, `data_hora`, `user_id_executor`, `entidade`, `acao`, `id_entidade`, `descricao`, `dados_antes` (JSON), `dados_depois` (JSON), `ip`. **Retenção 60 dias** — cleanup automático a cada request de listagem (DELETE LIMIT 5000). Aba "Log" no painel com filtros e paginação. |

---

## 🔁 Fluxos críticos

### 1. Cálculo do Resumo para pagamento (Gestão do Usuário)

**Backend:** `painel/commands/atividades_subtarefas/listar.php`
- Aceita `?user_id=X&resumo_periodo=tudo|30dias`
- Soma `cronometro_relatorios.segundos_trabalhando/segundos_ocioso` filtrado por `referencia_data`
- Soma `atividades_subtarefas.segundos_gastos`
- Soma `Pagamentos.valor` por `data_pagamento`

**Frontend:** `painel/js/aba-usuarios.js` → `carregarResumoHorasPagamento()`
- **Trabalhado** = declarado + não declarado
- **Declarado** = subtarefas (todas)
- **Não declarado** = `cronometrado − declarado` (mín. 0)
- **A pagar** = `(declarado × R$/h) − total_pago` (mín. 0)
- **Pago (2026-05-01)** = `total_pago` formatado em R$ — card visual ao lado de "A pagar" (`#gestaoResumoPago` em `index.php`). Respeita o filtro TUDO/30 DIAS via `total_pago` que já vem filtrado por `data_pagamento` no backend.

### 2. Sistema de Pagamento

**`pagamentos/criar.php`** → chama `pagamento_aplicar()` em `_aplicar_pagamento.php`:
1. Insere em `Pagamentos`
2. Trava `atividades_subtarefas` por `referencia_data` no período (`referencia_inicio` → `referencia_fim`/`travado_ate_data`)
3. Marca `registros_tempo.id_pagamento` no mesmo critério
4. Grava histórico `bloqueio_pagamento` em `atividades_subtarefas_historico`
5. **Snapshot do saldo pendente por atividade em `pagamento_abatimentos`** via `pagamento_registrar_abatimentos()` — fórmula `pendente = monitorado_em_janela − declarado − abatido_anterior`. **Janela temporal:** `monitorado` soma `cronometro_relatorios.segundos_trabalhando` apenas até `MAX(COALESCE(s.concluida_em, s.criada_em))` da última subtarefa concluída por atividade. Trabalho cronometrado **após a última declaração** e antes do pagamento NÃO é abatido — carrega como saldo para o próximo ciclo. Atividades sem nenhuma declaração viram janela vazia (sem abatimento, todo monitorado carrega). Idempotente por `UNIQUE (id_pagamento, user_id, id_atividade)`; usa `INSERT` com `try/catch` que só engole MySQL errno 1062 (duplicate entry) — outros erros de integridade (FK 1452, NOT NULL 1048) propagam. Pula silenciosamente se a tabela ainda não existe (verificado por `pagamento_tabela_abatimentos_existe()`).

**`pagamentos/editar.php`** → se mudou campo de período (`data_pagamento`, `referencia_inicio`, `referencia_fim`, `travado_ate_data`), chama `pagamento_reprocessar_todos()`: limpa e reaplica **apenas os bloqueios** de subtarefas/`registros_tempo`. **Abatimentos NÃO são tocados** — são imutáveis (snapshot do momento do pagamento, não recalculável retroativamente).

**`pagamentos/excluir.php`** → `pagamento_desvincular()` apaga linhas em `pagamento_abatimentos` daquele pagamento específico (libera o saldo da atividade); depois exclui pagamento e reprocessa bloqueios dos restantes. Abatimentos dos demais pagamentos ficam intactos.

**Fonte única de verdade:** todas as escritas em `pagamento_abatimentos` são feitas pelo PHP no momento do pagamento (transacional). O desktop apenas lê. Funções utilitárias em `declaracoes_dia.py` (`atualizar_bloqueios_por_pagamento`, `_registrar_abatimentos_por_pagamento`) ficaram como **backup** standalone — não são mais chamadas automaticamente em `JanelaSubtarefas.__init__`.

### 3. Auto-update do desktop

`app/app_shell.py` → `App._verificar_atualizacao()` + `_verificar_atualizacao_periodica()`:
1. HEAD request ao GitHub raw (`URL_ATUALIZACAO`) para comparar `Content-Length` do exe local vs remoto.
2. Se diferente: mostra overlay "Atualizando…" → download em background (`urlretrieve`) → backup do exe atual → swap atômico (`os.rename`).
3. **Antes do restart: chama `monitor.pausar_e_preservar_sessao()`** (preserva sessão localmente; o novo exe restaura automaticamente como PAUSADA via `obter_dados_sessao_pendente_do_usuario` no `_montar_tela_principal`). Antes era `zerar_sessao()` — trocado em v3.0+ pra evitar perda de continuidade visual.
4. **Aviso sonoro:** `winsound.MessageBeep(MB_ICONINFORMATION)` antes do restart pra alertar o user.
5. **Restart:** `subprocess.Popen([caminho_atual])` → `time.sleep(0.5)` → `sys.exit(0)`. O sleep + `sys.exit` (em vez de `os._exit`) deixam o bootloader PyInstaller `--onefile` limpar o `_MEI...` em Temp — reduz o aviso "Failed to remove temporary directory".
6. **Checagem periódica auto-aplica:** `_verificar_atualizacao_periodica` roda a cada `INTERVALO_VERIFICAR_UPDATE_MS=2 min` e chama `_verificar_atualizacao` direto se detectar update — não exige modal de confirmação. (Antes era 10 min + modal manual.)
7. **Retry no auto-login:** `_logar` faz até 3 tentativas com 2s entre cada uma quando `autenticar_usuario` falha — cobre janela de instabilidade de rede logo após o restart do auto-update.
8. **Limpeza preventiva de `.bak` (v3.1.2+):** `app/main.py::_limpar_bak_residuais()` roda em todo `main()` antes do `mainloop()`. Apaga qualquer `*.bak` na pasta do `sys.executable`. Defesa contra bug observado em campo: `_baixar` faz `backup_exe.unlink()` se `.bak` antigo já existir; se o `unlink` falhar (AV com handle aberto, lock transitório do Windows), o `try/except: pass` externo aborta o swap silenciosamente — sem aviso ao user — e o app continua rodando a versão velha. A limpeza na inicialização garante que toda nova sessão começa com a pasta pronta.
9. Pulado em modo dev (`getattr(sys, "frozen", False) == False`).

### 4. Credenciais e APIs (cifragem em repouso + consumo pelos apps)

**Duas chaves, domínios separados** (ambas em `painel/.env`):
- `APP_SECRETS_MASTER_KEY` — cifra/decifra os valores no banco (só o servidor).
- `APP_CLIENT_DECRYPT_KEY` — compartilhada com todos os apps consumidores. O servidor **recifra** o payload antes de entregar.

**Fluxo do painel (Fase 1):**
- Admin cadastra valor → `cripto.php::cifrar_segredo()` com MASTER_KEY → guarda `(valor_cifrado, nonce, versao_chave)` em `credenciais_usuario`.
- Listagens só retornam máscara parcial (`gerar_mascara_parcial`). Valor puro nunca sai do servidor.
- **Modo global (`aplicar_todos=true` em `salvar_valor.php`):** aplica a credencial a todos os usuários ativos com NONCE NOVO por usuário **e** liga `credenciais_modelos.aplicar_novos_usuarios=1` para que cadastros futuros herdem automaticamente. Modo individual (`aplicar_todos=false`) NÃO toca a flag global.
- **Bloqueio de desativados (defesa em camadas):**
  - `_auth_cliente.php` retorna 403 se `status_conta != 'ativa'` (já existia).
  - `salvar_valor.php` individual recusa com 409 se o `user_id` informado estiver inativo.
  - `salvar_valor.php` global filtra `WHERE status_conta='ativa'` no SELECT — inativos não recebem linha nova nem têm a sua atualizada.
- **Herança em novos cadastros:** `usuarios/criar.php` chama `herdar_credenciais_globais_para_usuario()` após inserir o usuário. Para cada modelo com `aplicar_novos_usuarios=1`, pega a credencial-referência ativa de menor `id_credencial`, decifra com MASTER, recifra com nonce novo e faz upsert em `credenciais_usuario`. Falhas individuais (MAC inválido, etc.) são silenciosas — não derrubam o cadastro.
- **Sincronia de status do usuário com credenciais (`atualizar_status.php`):**
  - `ativa → inativa`: `revogar_credenciais_de_usuario()` marca todas como `status='revogado'`. Não apaga.
  - `inativa → ativa`: `reativar_credenciais_revogadas_de_usuario()` volta o que estava revogado para `status='ativo'`. Credenciais antigas voltam a valer.
  - `excluir.php` (soft-delete) também revoga.
- **Remover global (`remover_global.php`):** numa transação, desliga `aplicar_novos_usuarios=0` no modelo **e** marca todas as credenciais ativas desse modelo como `status='revogado'`. Modelo continua existindo — credenciais individuais podem voltar a ser atribuídas.

**Fluxo do app consumidor (Fase 2):**
- App envia `Authorization: Bearer <user_id>:<chave>` → `_auth_cliente.php` valida contra `usuarios`.
- `obter.php`: decifra do banco com MASTER → recifra com CLIENT (novo nonce) → devolve `{cipher, nonce}` base64.
- App decifra com `APP_CLIENT_DECRYPT_KEY` embutida no binário.
- Rate limit 4-bucket (auth_attempt/auth_fail por IP; consumo por user e por IP).
- Modelos protegidos (`chatgpt`, `gemini`, `minimax`, `elevenlabs`, `assembly`, `mega_email`, `mega_password`) não podem ser excluídos (bloqueio em `excluir_modelo.php` e UI).

**Documentação autoritativa:** `!manual-credenciais.md` (ignorado pelo git; contém contratos + chave do cliente).

### 5. Auditoria de apps suspeitos + input sintético (v2.6)

**Fase 1 — por nome de processo:**
- Admin cadastra apps suspeitos em `auditoria_apps_suspeitos` via aba "Auditoria" (painel/js/aba-auditoria.js).
- Match por `LIKE '%nome_app%'` contra `cronometro_apps_intervalos.nome_app` — pega variações de versão/arquitetura automaticamente.
- `flags_usuarios.php` consolida por usuário: `tem_flag_7dias` (último uso nos 7 dias) + histórico completo.
- UI: bandeira 🚩 no Dashboard + aba Usuários + card "Alertas de Auditoria" na Gestão. Cache compartilhado de 1min evita fetch duplicado. Evento `painel:flags-auditoria-atualizadas` sincroniza as 3 UIs.
- Ícone 🚨 no link "Auditoria" da navbar só aparece se existir ao menos um `tem_flag_7dias=true` (atualizado via `_atualizarIconeAbaAuditoria()`).

**Fase 2 — por detecção de input (mais preciso):**
- `DetectorInputSintetico` em `app/hooks_input.py` conta segundos distintos com input humano vs sintético (flag `LLMHF_INJECTED`).
- Flush a cada 60s (junto do heartbeat) por `MonitorDeUso._flush_input_stats_locked_free()` em `app/monitor.py` → `cronometro_input_stats`.
- `input_stats.php` agrega por dia → card vermelho + gráfico ECharts na Gestão do Usuário.
- Vantagem sobre Fase 1: não depende do nome do processo (pega renomeados ou drivers kernel-mode que conseguem disfarçar nome, mas não a flag INJECTED).
- Política transparente: **não altera `segundos_trabalhando`**. Apenas registra para auditoria paralela.

### 7. Upload obrigatório no MEGA (Fases 1+2+3 + progresso/cancel + UX/integridade/pasta — todas implementadas)

**Status:** Pipeline ponta a ponta funcional + ciclo de vida completo (criar/editar/excluir) propaga banco↔MEGA + upload de pasta inteira. Validado: pasta lógica criada no banco → `mega-login` automático (auto-instala MEGAcmd se faltar) → **valida `pasta_existe` no MEGA** (sincronia on-demand) → `mega-put -c` com **barra de progresso real** → grava `arquivo_remoto_anterior` no estado pro próximo "Trocar arquivo" deletar automaticamente via `remover_arquivo`. **Excluir subtarefa** chama `remover_pasta_recursiva` (se for a última sub usando aquela pasta lógica) ou `remover_arquivo` por arquivo (se outras subs reusam) + `marcar_pasta_logica_inativa` no banco. **Editar subtarefa** popula `arquivo_remoto_anterior` via `obter_dados_subtarefa` em background — UI já abre com `✓ enviado` nos campos concluídos. **Upload de pasta** via botão `📁 Pasta` (cada linha de campo). **Trocar canal** no form refaz fetch da config e **reconstrói os widgets dos campos exigidos** com a lista do novo canal (via `_construir_widgets_campos`, que destrói o conteúdo do `frame_uploads` e recria a partir de `campos_exigidos[]` retornado pelo backend). Botão **"Cancelar"** disponível durante upload — usa `taskkill /F /T` pra matar a árvore de subprocessos.

**Modelo aprovado (`!executar.md` tarefa 1):**
- **Por canal/atividade:** define a pasta raiz do canal no MEGA (`mega_canal_config`).
- **Por `user_id + id_atividade`:** define quais campos de upload aquele usuário precisa preencher (`mega_campos_upload`).
- **Pasta lógica do vídeo:** indexada no banco (`mega_pasta_logica`) com nome canônico `"NN - Titulo"`. Bloqueio de duplicidade só **dentro do mesmo canal**.
- **Auth desktop:** mesma do módulo Credenciais — `user_id + chave` via `credenciais/api/_auth_cliente.php`.
- **Login MEGA (Fase 2 — IMPLEMENTADA em `app/mega_uploader.py`):** conta dedicada do sistema, credenciais armazenadas via módulo Credenciais existente — modelos `mega_email` e `mega_password` (já seedados em `credenciais_modelos`, ambos protegidos contra exclusão). Admin preenche em modo global (`aplicar_todos=true`) e cada cliente recebe via `obter.php`. `MegaUploader.garantir_logado()` busca via HTTP, decifra com `APP_CLIENT_DECRYPT_KEY` (lida de `app/segredos.py`) e roda `mega-login email senha`. Auto-instala MEGAcmd se faltar (NSIS `/S` baixado de `https://mega.nz/MEGAcmdSetup64.exe`). Sempre `CREATE_NO_WINDOW`. **Senha jamais aparece em logs** — filtragem explícita antes de propagar erros.
- **Comportamento sem config (Validação 1 do executar):** canal sem `mega_canal_config` ou sem `upload_ativo=1` → desktop mantém fluxo antigo (decisão **A**, com aviso visível na UI).

**Fluxo final implementado:**
1. Desktop chama `desktop_obter_config.php?id_atividade=Y` ao abrir o formulário (timeout 5s, fallback automático para form legado em qualquer falha).
2. Se `upload_ativo=true`, renderiza seção **Pasta lógica** (Criar nova / Selecionar existente) + **Arquivos para upload** dinâmicos.
3. "Criar nova" → POST `desktop_criar_pasta.php` (cria registro no banco com nome canônico `NN - Titulo`).
4. Cada upload: POST `desktop_registrar_upload.php` (status=enviando) → `MegaUploader.upload_arquivo()` em background (`mega-put -c`, cria pasta no MEGA se faltar) → POST `desktop_registrar_upload.php` (status=concluido | erro).
5. Botão "Salvar e Concluir" desabilitado enquanto: (a) pasta lógica não definida; OU (b) algum campo `obrigatorio=1` não atingiu `status_upload='concluido'`. Aviso textual sobre o que está pendente.
6. Título salvo da subtarefa = exatamente o `nome_pasta` retornado por `desktop_criar_pasta.php` (substitui `f"{numero} - {titulo}"` digitado).
7. Edição de subtarefa existente: lookup por `nome_pasta == titulo_subtarefa` em `pastas_logicas[]` retornadas pela config; se achar, modo "selecionar" pré-povoado; senão "criar".
8. Após `criar_subtarefa`/`atualizar_subtarefa`, faz POST best-effort em `desktop_registrar_upload.php` pra vincular `id_subtarefa` aos `mega_uploads` criados antes da subtarefa existir.
9. **Recovery após queda (v3.0+):** `app_shell._disparar_recovery_uploads_orfaos()` é agendado via `after(2000)` em `_logar()`. Em background chama `desktop_uploads_orfaos_listar.php` → para cada pasta com uploads órfãos (sem `id_subtarefa`) cria 1 subtarefa Aberta via `RepositorioDeclaracoesDia.criar_subtarefa(titulo=nome_pasta, observacao="Recuperada após fechamento abrupto…")` e vincula cada upload via `desktop_registrar_upload.php` (UPDATE com `id_subtarefa`). `messagebox.showinfo` no fim com a contagem. Roda 1× por login (flag `_recovery_orfaos_executado` resetada no `_sair`).
10. **Sync MEGA-banco (v3.0+):** `app_shell._agendar_sync_mega_se_necessario()` é chamado no callback de sucesso de `_iniciar()`. `after(5_000, ...)` dispara `mega_sync.executar_sincronizacao_async` que consome `desktop_pastas_logicas_para_sync.php`, lista a raiz de cada canal no MEGA (`MegaUploader.listar`), compara em memória, e inativa em lote via `desktop_marcar_pastas_logicas_inativas_lote.php` (300 IDs/lote). 1× ao dia por user. Falha de listagem em qualquer canal aborta sem inativar nada (defesa contra MEGA offline / login falhou).
11. **Fechamento do form com upload em andamento (v3.0+):** se `state="enviando"` em qualquer campo, `_ao_fechar_janela` pergunta com `messagebox.askyesno`. Se confirmar, dispara `cancel_event.set()` em todos os uploads ativos. A subtarefa Aberta já existe (auto-criada no 1º upload — v2.9.3+), então o trabalho não se perde.

**Pré-requisitos operacionais (já estabelecidos pelas Fases 1+2):**
- Admin precisa preencher `mega_email`+`mega_password` na aba Credenciais em modo global (sem isso, `garantir_logado()` lança `ErroCredencialFaltando` — UI mostra messagebox claro).
- `app/segredos.py` deve existir localmente com `APP_CLIENT_DECRYPT_KEY` real (mesma chave do `painel/.env`).
- `URL_PAINEL` em `app/config.py` aponta pra produção por padrão; override via env var `CRONOMETRO_URL_PAINEL` (útil em dev local: `http://localhost/cronometro-web/painel`).

### 6. Renderização de gráficos (Dashboard)

`aba-graficos.js`:
- `obterFiltros()` envia 7 dias por padrão (sem filtro manual) ou range manual
- `montarVisaoGeralTodosUsuarios()` usa **show/hide via `d-none`** em containers estáticos — **NUNCA `innerHTML`**
- `_teamTimelineIdxDia = 0` = hoje (gráficos abrem mostrando hoje)
- Setas navegam `_teamTimelineDias` (preenchido com dias contíguos dos dados)

---

## ⚠️ Convenções que IAs sempre erram

1. **`painel/commands/conexao/conexao.php` É versionado.** Commitar sempre com `DB_PORT` default = `'3306'` (produção). Localmente fica `'3307'` (XAMPP homologação). Protegido por `git update-index --skip-worktree` — pulls não sobrescrevem o 3307 local. **Não** remover do git. **Não** alterar `DB_USER`/`DB_PASS` sem coordenar — senha exposta no histórico público motiva rotação futura.
2. **Schema vs banco:** o repo tem só `credenciais_tabelas.sql` versionado (migration inicial da Fase 1, **desatualizado**). O dump completo `dados.sql` existe **localmente** mas está no `.gitignore` — é referência, não fonte da verdade. **Alterar qualquer arquivo SQL NÃO altera o banco real.** Mudanças de schema requerem ALTER manual no servidor (peça permissão antes); depois reflita o ALTER em `dados.sql` local para manter o dump coerente.
3. **`registros_tempo` pode estar vazio** — sempre tenha fallback em queries.
4. **Atividade ↔ Canal:** termo interno é `atividade` (DB, IDs HTML, classes JS), termo visível é `Canal`. **NÃO renomear IDs internos.**
5. **`canal_entrega` legacy:** dados antigos vêm como `#ID - Nome (status)`. Frontend limpa via regex (`limparCanal()` em `aba-usuarios.js`). Novas declarações já vêm limpas.
6. **`referencia_data` vs `criado_em`:** sempre filtrar `cronometro_relatorios` por `referencia_data` (data real do trabalho). `criado_em` é só fallback para dados antigos.
7. **`requisitarJson` em `aba-graficos.js`** retorna `json.dados` direto (não `json` inteiro). Outras IIFEs retornam `json` completo. Verificar antes de usar.
8. **4 cópias de `requisitarJson`** existem em arquivos JS diferentes (`painel.js`, `aba-usuarios.js`, `aba-atividades.js`, `aba-graficos.js`) — não confundir. `aba-credenciais.js` tem helper próprio chamado `requisitar` (nome diferente, comportamento parecido). Outras IIFEs (`aba-gerenciar-tarefas.js`, `aba-relatorio.js`, `aba-auditoria.js`) usam `fetch` direto.
9. **Endpoints públicos** (`status/atualizar`, `status/listar`, `status/horas_mes`, `baixar_app`) são lidos pelo desktop SEM autenticação. Nunca adicionar `verificar_sessao_painel()` a eles.
10. **Tarefa concluída com 0 segundos é VÁLIDA** — não filtrar por `segundos > 0` em queries de espelho.
11. **Título de subtarefa no formato `NUMERO - NOME` (v2.4+):** o separador estrutural é o **primeiro** ` - `. O nome pode conter outros traços. Não quebrar na segunda ocorrência.
12. **Credenciais (`credenciais_usuario.valor_cifrado`) NUNCA retornam do backend em claro.** Somente máscara parcial. Mesmo admin logado só consegue substituir, não ler.
13. **`painel/.env` (não versionado) precisa ter `APP_SECRETS_MASTER_KEY` e `APP_CLIENT_DECRYPT_KEY`** — 32 bytes em base64 cada. Sem elas, o módulo de Credenciais quebra no load. Chave do cliente documentada em `!manual-credenciais.md` (também não versionado).
14. **Erros genéricos no painel** (ex.: "Erro no servidor.") aparecem detalhados quando `APP_DEBUG=1` está no `.env` do servidor. Os `requisitarJson` (4 cópias em `painel.js`, `aba-usuarios.js`, `aba-atividades.js`, `aba-graficos.js`) já incluem `dados.erro` na mensagem do `Error`.
15. **Rate limit aplica somente nos endpoints `credenciais/api/*`.** Outros endpoints do painel não têm. Storage em `painel/logs/ratelimit/` (ignorado no git).
16. **Auditoria (v2.6) — match por substring:** `auditoria_apps_suspeitos.nome_app` NUNCA é o nome completo do processo (ex: `gs-auto-clicker-3.1.4-installer.exe`). É uma substring curta (ex: `gs-auto-clicker`). O match no backend é `LIKE '%nome_app%'`. Isso é proposital para absorver variações de versão/arquitetura.
17. **Auditoria (v2.6) — flag 7 dias é dinâmica:** "usuário com bandeira" = houve uso de app suspeito nos últimos 7 dias rolando (`NOW() - INTERVAL 7 DAY`). Histórico completo (`apps_detectados`) permanece para sempre, mesmo após a bandeira sumir. Não confundir os dois conceitos na UI.
18. **Input sintético (v2.6) — coleta só funciona a partir do cliente v2.6+.** Clientes antigos (v2.5 e anteriores) não enviam nada a `cronometro_input_stats`. Gestão do Usuário exibe o card apenas se houver dados na tabela; caso contrário, fica oculto.
19. **`VERSAO_APLICACAO` mora em `app/config.py`** (fonte canônica pós-refator). Atualize SEMPRE que for fazer build+release. É gravado em `cronometro_sessoes.versao_app` de cada sessão iniciada (rastreabilidade). `release.bat` lê de `app\config.py` via findstr. **Atenção:** `pyproject.toml` tem `version = "2.2"` que NÃO é a versão do app — só metadado de packaging desatualizado. Versão atual no repo: **v4.0.7** (2026-06-12).
20. **Hooks low-level (v2.6):** as callbacks do `DetectorInputSintetico` (em `app/hooks_input.py`) dependem de referência forte (`self._cb_mouse_ref` / `self._cb_kbd_ref`). Nunca remover esses atributos — se o GC coletar, o processo crasha com violação de acesso.
21. **Recorte do Dashboard (aba-graficos.js):** a fonte única da verdade do dia/período renderizado é `_diaAtualmenteExibido()` (modo dia) ou `_filtroTemMultiplosDias()` (modo período). **NÃO use `_teamTimelineDias[_teamTimelineIdxDia]` diretamente em novas funções de recorte** — isso foi causa de bug onde setas pareciam não funcionar. Em modo dia, cada clique em seta ajusta `_diaNavegacaoSeta` e dispara `atualizarGraficos()` (novo fetch do backend só com aquele dia). Filtro manual tem precedência e limpa `_diaNavegacaoSeta`.
22. **Duração no gráfico — regra cumulativa (v2.7+):**
    - **`cronometro_foco_janela`:** `segundos_em_foco` cumulativo é a fonte de verdade quando > 0 (gravado a cada 10s pelo app). `graficos.php` em `sqlPeriodos`: `segundos_em_foco > 0` → `inicio_em + segundos_em_foco`; senão (registro legado de cliente antigo) → fallback histórico (`fim_em` se existir, senão cap de 3h sobre `inicio_em`).
    - **`cronometro_apps_intervalos`:** `(segundos_em_foco + segundos_segundo_plano)` cumulativo (já existia desde antes) é a fonte de verdade quando > 0. `graficos.php` em `sqlPeriodosAbertos` aplica a mesma cascata: cumulativo → `fim_em` → `ultima_atualizacao_em` → `usuarios_status_atual.ultimo_em` → cap 20h.
    - **Ao tocar nessas queries, manter os fallbacks** — clientes pré-v2.7 ainda existem com `segundos_em_foco=0` na tabela de foco. Não usar `TIMESTAMPDIFF(inicio_em, fim_em)` como fonte primária.
23. **`subprocess.run(... capture_output=True, ...)` trava com daemon herdeiro no Windows (MEGAcmd).** O `mega-*.bat` invoca `MEGAcmdShell.exe` que pode spawnar `MEGAcmdServer.exe` como daemon. O server **herda os fds dos pipes do `subprocess.PIPE`**. Como `subprocess.run` lê via `Popen.communicate()` que espera **todos** os escritores do pipe fecharem, o read fica preso pra sempre — mesmo após o `cmd.exe` principal sair, porque o daemon segura o handle. Sintoma típico: o subprocess.run nunca retorna nem dispara `TimeoutExpired`. **Fix permanente em `app/mega_uploader.py::_executar_silencioso`:** sempre redirecionar stdout/stderr pra **arquivos temporários** (`tempfile.NamedTemporaryFile`); `subprocess.run` retorna quando o processo principal termina, sem esperar arquivos fecharem. Para streaming (`mega-put` com progresso) usar `Popen` + thread daemon que faz `tail` do arquivo de stderr e parseia. **Não trocar a estratégia de arquivos por `PIPE` em nenhum hipótese** — o bug volta imediatamente em qualquer comando MEGAcmd que provoque o spawn do server.

24. **MEGAcmd 2.5.2+ não emite mais "Login complete" no stdout do `mega-login`.** Versões anteriores imprimiam essa string ao final; versões atuais imprimem só `Fetching nodes ||...||(2/2 MB: 100%)` e saem com `rc=0`. **Não usar busca por string como critério de sucesso** — confiar exclusivamente no exit code: `rc == 0` (login feito) ou `rc == 54` (already logged in). Ambos = sucesso.

25. **Cancelamento de `mega-put` no Windows precisa matar a árvore inteira.** `proc.kill()` em Windows mata **só** o processo principal (cmd.exe), deixando filhos vivos que continuam o upload em background. **Solução:** `subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)])` (`/T` = árvore). NÃO matar o `MEGAcmdServer.exe` daemon junto — ele é compartilhado entre sessões; matá-lo invalida a sessão atual e força relogin. Implementação em `MegaUploader._matar_arvore`.

26. **Auth do desktop em endpoints `credenciais/api/*` e `mega/desktop_*` — SEMPRE mandar os 3 headers juntos.** Apache+PHP-FPM em alguns hosts (incluindo o EasyPanel atual de produção) **strippa** `Authorization` antes do PHP, e o `_auth_cliente.php` cai no caminho de "credenciais vazias" → retorna 401 indistinguível de chave inválida. O cliente Python (`app/mega_uploader.py::_construir_headers_auth`) já manda `Authorization: Bearer`, `X-User-Id` E `X-User-Chave` simultaneamente — o PHP usa o primeiro que estiver presente. **Não simplifique pra mandar só `Authorization`** mesmo que pareça redundante: se mexer nesse host (ou em qualquer .htaccess/proxy futuro) o desktop pode parar de autenticar com o mesmo sintoma de 401. O `_auth_cliente.php` também tem fallback duplo (`REDIRECT_HTTP_*` e `apache_request_headers()`) pra cobrir clientes legados que só mandam `Authorization`.

27. **`ocultar_dashboard` — onde filtrar e onde NÃO filtrar.**
    - **Filtra no servidor:** `commands/status/listar.php` e `commands/graficos/graficos.php` (`acao=meta` e `graficos_obter_usuarios_base`). Em `acao=painel`, o filtro é reforçado por um set `$user_ids_permitidos` derivado do `usuarios_base` — todos os loops subsequentes (`status_atuais`, `apps`, `foco`, `abertos_agora`) ignoram `user_id` que não esteja nesse set, senão os JOINs com `usuarios` reintroduzem ocultos via outras tabelas.
    - **Filtra no consumidor (frontend):** `aba-graficos.js::carregarTempoDeclarado()` busca `usuarios/listar.php`, deriva `setOcultos` e remove de `dados.linhas`/`dados.totais_por_usuario` + soma de pagamentos, recalculando `total_geral_*`. O backend `relatorio/tempo_trabalhado.php` continua intocado (a aba Relatório precisa ver todos).
    - **NÃO filtra:**
      - `painel.js::carregarUsuariosParaDashboard()` — os contadores "Total" e "Ativos" contam **todos** os cadastros (regra do usuário: a flag oculta só dos gráficos/equipe, nunca altera estatísticas de cadastro).
      - `commands/auditoria/flags_usuarios.php` — alimenta Dashboard E aba Usuários; o filtro do Dashboard já vem de `graficos.php` (consumidor só enriquece com a flag), e a aba Usuários precisa ver flag de oculto também.
      - Abas administrativas (`aba-atividades.js`, `aba-gerenciar-tarefas.js`, `aba-relatorio.js`) — admin precisa enxergar todos.
    - **Endpoint de toggle:** `commands/usuarios/alternar_visibilidade_dashboard.php` (POST `{user_id, ocultar_dashboard:0|1}`).
    - **UI:** botão único 🚫/👁 ao lado do badge de Status na aba Usuários (`aba-usuarios.js::botaoVisibilidadeDashboard`). Oculto fica com `opacity:0.5`.

31. **`JanelaSubtarefas` é OVERVIEW de TODOS os canais (v2.9.2+).** `_recarregar_dados` chama `listar_subtarefas_do_dia(user_id, id_atividade=0)` e `obter_resumo_do_dia(user_id, id_atividade=0, ...)`. As funções no `declaracoes_dia.py` aceitam `id_atividade=0` significando "todas as atividades do user" — as queries pulam o `AND id_atividade = %s` e a validação de pertença só roda quando `id_atividade > 0`. **Editar sub de outro canal funciona:** `_abrir_formulario_subtarefa` deriva `id_ativ_lookup` da sub (não de `self._id_atividade`); ambos forms (legado + MEGA) inicializam o id_atividade efetivo a partir da sub em modo edição. **`self._id_atividade` continua sendo o canal da SESSÃO** (cronômetro ativo) — usado só pra: default do canal ao criar sub nova, `_montar_relatorio_final`/`_enviar_e_finalizar` (finalizam o dia da sessão) e `obter_config_canal` em modo "nova".

32. **Sub Aberta automática + visual vermelho (v2.9.3+).** No form MEGA, **o primeiro upload concluído cria a sub no banco com `concluida=0` automaticamente** (helper `_criar_sub_aberta_se_necessario` é chamado dentro de `_iniciar_upload_mega::_op` antes do `registrar_upload(status=concluido)` final). Uploads subsequentes na mesma janela reusam o mesmo `id_subtarefa` via `self._id_subtarefa_criada_nesta_janela`. **Regra de salvar:** com upload concluído + tempo=0 → bloqueia "Salvar" com aviso ("preencha o tempo gasto"). Sem upload + tempo=0 → permitido (sub fica como Aberta só com cabeçalho). **Visual:** subs `concluida=0` ganham tag `aberta` (foreground `#ff6b6b`, background `#3a1a1a`) na Treeview da overview — chamativo pra lembrar de finalizar. **Cleanup:** ao fechar a janela do form MEGA em modo "nova" (X ou Cancelar), se houver `pasta_logica.id_pasta_logica > 0` mas nenhuma sub criada e nenhum upload concluído → chama `marcar_pasta_logica_inativa` automaticamente (evita pastas órfãs queimando número). Em modo edição, NUNCA limpa pasta. Ao salvar com sub já criada (modo nova com upload prévio), `_operacao` chama `atualizar_subtarefa` com os campos atuais do form antes de concluir — cobre o caso do user editar observação/canal/data depois do upload.

28. **Form MEGA (`_abrir_formulario_subtarefa_mega`) — 5 regras invisíveis que IAs futuras quebram fácil:**
    - **`id_atividade_efetiva["id"]` ≠ `self._id_atividade`.** O segundo é o canal de origem da janela; o primeiro pode ter sido trocado em runtime via combobox de canal. **Toda chamada que precisa do canal "real" (criar pasta lógica, salvar subtarefa, refetch de config)** tem que usar o efetivo. Mesma regra pra `pasta_raiz_holder["valor"]` (vs `pasta_raiz_mega` capturado por closure inicial).
    - **`arquivo_remoto_anterior` com sufixo `/` indica PASTA, sem `/` indica ARQUIVO.** O dedup em `_iniciar_upload_mega::_op` precisa rodar `remover_pasta_recursiva` em pastas (mega-rm -r -f) — `remover_arquivo` (mega-rm -f) NÃO apaga diretório. Se trocar essa heurística, o `mega-put -c <dir>` posterior pode mesclar conteúdos e deixar arquivos órfãos.
    - **Pra `eh_pasta=True`, dedup roda SEMPRE — mesmo caminho idêntico ao anterior.** `mega-put -c <dir>` recursivo mescla com pasta remota existente; sem limpar antes, arquivos antigos da pasta local ficam órfãos no MEGA quando o usuário reenvia uma pasta com o mesmo nome. Pra arquivo, sobrescrita do `mega-put` resolve — só limpa quando muda o caminho. Lógica em `_iniciar_upload_mega::_op`.
    - **`_atualizar_botao_salvar` bloqueia salvar quando `estado_campos` está vazio.** Regra de negócio: se MEGA está ativo no canal, o admin tem que ter cadastrado pelo menos um `mega_campos_upload` pra esse user — senão o usuário poderia "concluir" sem subir nada. Não relaxar esse check sem alinhar a regra.
    - **Trocar canal RECONSTRÓI os widgets de campos** via `_construir_widgets_campos(novos_campos)` — destrói filhos do `frame_uploads` e recria. Se alguém adicionar lógica que persiste estado/widgets de campos por outro caminho (ex: cache global), tem que limpar nesse mesmo handler. **`estado_campos` é a fonte da verdade da lista atual de campos** — qualquer código que itere campos exigidos deve ler de lá, não de variáveis snapshot da inicialização.

29. **Endpoints `mega/desktop_*` — pertença ao canal é obrigatória.** Os endpoints consumidos pelo desktop autenticam via `_auth_cliente.php` (user_id+chave), mas autenticação **NÃO é autorização**. O user precisa também estar atribuído à atividade alvo (`atividades_usuarios`). **Regra:** todo endpoint `desktop_*` que recebe `id_atividade` (direto ou derivado de `id_pasta_logica`) chama `mega_user_pertence_atividade()` ou `mega_user_pertence_pasta_logica()` (em `_comum.php`) **antes** de qualquer query/mutação. Sem isso vira IDOR clássico — qualquer user autenticado lista/cria pastas em canais alheios. Resposta padrão: 403 ("usuário não tem acesso a esta atividade") quando o user existe mas não pertence; 404 quando o objeto (pasta lógica/subtarefa) não existe (não vazar a existência).

34. **Detecção de MEGAcmd exige `MEGAclient.exe` E os wrappers `.bat`.** `_localizar_megacmd` em `app/mega_uploader.py` não pode olhar só pra `MEGAclient.exe` — instalações parciais/corrompidas (visto no PC do Marcus, 2026-05-01) deixam o exe principal mas faltam `mega-whoami.bat`/`mega-login.bat`/etc. A detecção passa, mas a primeira chamada de `_run_mega` quebra com `comando não encontrado: <path>` e o login MEGA aborta. **Fix:** `_instalacao_completa(base)` valida `MEGAclient.exe` + lista `BATS_OBRIGATORIOS_MEGACMD` (`mega-whoami`/`mega-login`/`mega-mkdir`/`mega-put`/`mega-rm`/`mega-ls`); se algum `.bat` faltar, retorna False → `_localizar_megacmd` retorna None → `garantir_instalado` dispara `_instalar_megacmd_silenciosamente` automaticamente. **Manter a lista sincronizada:** ao adicionar uso novo de `_run_mega("mega-XYZ")` em comando que ainda não está em `BATS_OBRIGATORIOS_MEGACMD`, incluir `"mega-XYZ.bat"` na tupla — senão a validação fica frouxa pra esse comando e o bug volta caso a instalação parcial atinja só o `.bat` novo.

33. **Auto-update: `.bak` antigo trava swap silenciosamente (v3.1.2+).** O fluxo de `_baixar` em `app/app_shell.py` faz `backup_exe.unlink()` antes de renomear o exe atual pra `.bak`. Se o `unlink` levantar exceção (AV com handle aberto no `.bak` velho, lock transitório do Windows, sessão prévia do app antigo ainda referenciando), o `try/except Exception: pass` externo aborta o swap **silenciosamente** — o user não vê erro nem overlay, app continua rodando a versão velha e a notificação periódica (a cada 2 min) repete o mesmo loop. **Sintoma típico:** "atualizei o exe no GitHub mas o app do user não atualiza sozinho." **Defesa:** `app/main.py::_limpar_bak_residuais()` apaga `*.bak` da pasta do `sys.executable` em todo `main()` (`frozen` only) — toda nova sessão começa com a pasta limpa. Confirmar manualmente pedindo pro user fechar app e apagar `CronometroLeve.exe.bak` + `CronometroLeve_novo.exe` da pasta. Não trocar o `except: pass` por log silenciosamente — sem visibilidade do erro real, o próximo bug do swap (permissão, disco cheio, AV diferente) volta a ser invisível. Se for refatorar, **logar a exceção em `~/.cronometro_leve_log_tecnico.txt`** antes de engolir.

30. **`usuarios.user_id` (string) ≠ `usuarios.id_usuario` (PK numérica).** A tabela `usuarios` tem **dois identificadores**: `user_id` (string pública tipo `"adm"`/`"rk_xxxx"` — usada pelo auth do desktop e pelo painel admin) e `id_usuario` (auto-increment, PK interna). Tabelas relacionais N:N (`atividades_usuarios.id_usuario`, etc.) usam a **PK numérica**. Endpoints/queries que recebem `user_id` (string) e precisam consultar essas tabelas TÊM que fazer JOIN: `JOIN usuarios u ON u.id_usuario = au.id_usuario WHERE u.user_id = ?`. Tentativa direta de `WHERE user_id = ?` em `atividades_usuarios` quebra com `Unknown column 'user_id'`.

---

## 🛠️ Padrões de código

### Backend PHP
- **Resposta JSON:** sempre via `responder_json($ok, $msg, $dados, $status_http)`.
- **Debug:** `debug_ativo()` retorna `true` apenas se `APP_DEBUG=1` no ambiente.
- **Erro padrão:** `try { ... } catch (Throwable $e) { responder_json(false, 'msg', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500); }`
- **Conexão:** `obter_conexao_pdo()` (sempre via `require_once conexao/conexao.php`).

### Frontend JS
- **Sem framework.** Vanilla JS + Bootstrap 5.
- **Escape:** cada IIFE define seu próprio helper. `escaparHtml()` em `aba-graficos.js`/`aba-atividades.js`; `esc()` em `aba-credenciais.js`. Outros JS escapam inline. Não existe um helper global compartilhado.
- **ECharts:** em `aba-graficos.js` há `criarOuObterChart(id, minH)` (linha ~738) que reusa instâncias via `echarts.getInstanceByDom`. Outras IIFEs com gráficos (ex.: `aba-auditoria.js`) chamam `echarts.init` direto — convenção do `aba-graficos.js`, não do projeto inteiro.

### Python
- **Pacote `app/` modular (pós-refator v2.8):** novo código Python desktop entra em `app/<modulo>.py`. O shim `app.py` na raiz **não existe mais** (deletado em 2026-05-01). Importações dentro do pacote sempre absolutas (`from app.monitor import MonitorDeUso`), nunca relativas.
- **Lock thread-safe:** operações no `MonitorDeUso` (em `app/monitor.py`) capturam snapshots dentro de `with self._trava:` antes de soltar.
- **DB queries em background:** UI nunca chama banco direto — sempre via `_rodar_em_background()` (em `app/app_shell.py`) ou `_executar_em_background()` (em `app/subtarefas.py`).
- **Auto-update só em `.exe`:** guard `getattr(sys, "frozen", False)` no início.
- **Entrypoint:** `python main.py` em dev, `CronometroLeve.exe` (gerado a partir de `main.py` via `CronometroLeve.spec`) em produção.

---

## 🔒 Segurança (resumo)

- **Endpoints administrativos** protegidos via `verificar_sessao_painel()`.
- **bcrypt** para senha do admin do painel; cookie de sessão com `SameSite=Strict` (configurado em `_comum/auth.php`).
- **Bloqueio de login:** 2 erros → 5min de bloqueio.
- **`.htaccess`** bloqueia acesso HTTP a `.json`, `.bak`, `.old`, `.env`.
- **Pasta `logs/`** com `Require all denied`. Inclui `logs/ratelimit/*.json` (não versionado).
- **Config do banco** em `conexao.php` (versionado com porta 3306; vars ENV opcionais).
- **Módulo Credenciais:**
  - Cifragem em repouso com `sodium_crypto_secretbox` (XSalsa20-Poly1305). Chave `APP_SECRETS_MASTER_KEY` no `.env` do servidor.
  - Entrega ao cliente **re-cifrada** com `APP_CLIENT_DECRYPT_KEY` (mesma em todos os apps).
  - Autenticação dos apps = `user_id + chave` do próprio usuário (sem "token de serviço" separado).
  - Rate limit de 4 buckets em `credenciais/api/_auth_cliente.php`.
  - Valor puro NUNCA é retornado nem logado em nenhum caminho.

---

## 🌐 Troubleshooting — "Sem conexão com o servidor" só em alguns usuários

**Sintoma:** app desktop fica em "Verificando…" e depois exibe `Sem conexão com o servidor.` para um usuário específico. No PC do dev/admin e em outros usuários conecta normalmente. Abrir `https://banco-painel.cpgdmb.easypanel.host` no **navegador do PC afetado** também falha com `ERR_CONNECTION_TIMED_OUT`.

**Causa:** não é o app — é a rota de internet do usuário até o servidor EasyPanel. Provedores (ISPs) brasileiros eventualmente têm peering ruim com datacenters do EasyPanel/Hetzner, e o TCP do PC dele não fecha handshake com o IP de destino. Antivírus com proteção web e firewalls corporativos também podem causar o mesmo timeout.

**Diagnóstico rápido (2 passos):**
1. Pedir pro usuário abrir `https://banco-painel.cpgdmb.easypanel.host/baixar_app.php` no **navegador** dele.
   - Se der `ERR_CONNECTION_TIMED_OUT` → problema de rota/firewall (segue passo 2).
   - Se abrir normal mas o app não conecta → aí sim é problema local do app (antivírus bloqueando `.exe`, versão desatualizada, etc.).
2. Pedir pra ele conectar o PC no **4G/5G do celular (hotspot)** e testar. Se funcionar no 4G, confirma que é a rede dele.

**Solução validada (caso real — usuário em 2026-05-25):** instalar **Cloudflare WARP** ([1.1.1.1](https://1.1.1.1)), abrir o app, selecionar modo **"Tráfego e DNS (UDP)"** e clicar em Conectar. A nuvem fica colorida ("Conectado") e o app destrava na hora. Os modos "Somente DNS (HTTPS/TLS)" **não resolvem** porque o problema não é DNS — é rota TCP; só o modo de tráfego completo passa pela rede da Cloudflare e contorna o roteamento ruim do ISP.

**Quando o WARP não resolve:** investigar antivírus (Kaspersky/ESET/Avast com proteção web ativa bloqueando o domínio), firewall do roteador, ou VPN/proxy ativos no PC do usuário.

### "certificate has expired" na sync MEGA (RESOLVIDO em v4.0.3)

**Sintoma:** `Falha ao consultar painel: ... [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired`, com data/hora do PC corretas e o site abrindo no navegador. **Causa:** PC sem os roots novos da Let's Encrypt (ISRG Root X1/X2) — o OpenSSL seguia o `DST Root CA X3` (vencido 2021); o navegador funciona porque baixa o root sozinho. **Fix definitivo (v4.0.3+):** `app/config.py` força o HTTPS a validar contra `certifi` embutido. Versões antigas pegam pelo auto-update (download vem do GitHub, não afetado). Workaround manual p/ versões < v4.0.3: instalar ISRG Root X1/X2 ou Windows Update.

### "Login no MEGA falhou: Failed to access server" na sync MEGA

**Sintoma:** `Login no MEGA falhou: mega-login falhou (rc=...): Failed to access server: ...`. A chamada ao painel **passou** (não é certificado nem app) — quem falha é o **MEGAcmd** ao conectar nos servidores do MEGA. **Diagnóstico:** `%LOCALAPPDATA%\MEGAcmd\megacmdserver.log` com `Failed reqstat request. Retrying` repetido = conexão instável/parcial ou **sessão travada** do MEGAcmd. **Fix (ordem):** (1) **reiniciar o PC** / matar `MEGAcmdServer.exe` → resolveu o caso real de 2026-06-05 (sessão travada); (2) Cloudflare WARP "Tráfego e DNS" se for rota ruim até o MEGA; (3) liberar MEGAcmd + domínios `*.mega.nz`/`g.api.mega.co.nz` no antivírus/firewall; (4) testar no 4G. Independente do nosso código — MEGAcmd é processo separado com conexão própria.

---

## 🎨 Identidade Visual

- Vermelho `#e62117`, acentos pink/orange/yellow/purple
- Tema dark, glassmorphism (`backdrop-filter`)
- Fonte: Plus Jakarta Sans (Google Fonts)

---

## 🔁 CI/CD

`.github/workflows/ci.yml` em push/PR para `main`:
- `ruff` (lint), `mypy` (typecheck — só em `banco.py`, `atividades.py`, `declaracoes_dia.py`), `pytest` (em `tests/`), `bandit` (security)
- **Job `test` está vermelho desde que o CI nasceu** (mais de 30 runs de falha consecutivos). Causa: `app/win32_utils.py:16` faz `user32 = ctypes.windll.user32` no top-level, e `ctypes.windll` é Windows-only. CI roda `ubuntu-latest`, então o import de `tests/test_tempo.py` (`from app import ...`) cascateia até `win32_utils` e crasha com `AttributeError: module 'ctypes' has no attribute 'windll'` antes de qualquer teste rodar. **Não foi commit recente que quebrou** — sempre foi assim, ninguém percebeu porque o app só roda em Windows. Fix simples (não aplicado ainda): `user32 = getattr(ctypes, "windll", None) and ctypes.windll.user32` — em Windows nada muda; em Linux vira `None` e o módulo importa OK. Funções que usam `user32`/`kernel32` só falhariam se chamadas em Linux, e nenhum teste chama.
