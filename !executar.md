# Plano de Execução — Cronômetro Web

> **Como usar:** manter no topo apenas as tarefas pendentes. Quando algo for concluído, registrar de forma enxuta somente se ainda fizer sentido para o trabalho atual.

---

## Tarefas Claude 1

### ✅ 7. Verde compartilhado de thumb + botão "Baixar arquivo" da pasta (2026-06-05)

**Pedido do usuário:** (1) quando um thumbmaker sobe a thumb, fica verde só pra ele — outro thumbmaker não vê que a thumb já foi feita e pode refazer; (2) o thumbmaker precisa entrar no MEGA pra ver o vídeo — queria baixar direto do cronômetro. Editor e thumbmakers dividem a mesma pasta do vídeo.

**Solução aplicada (Claude 1):**

1. **Banco — coluna `tipo`** (`painel/commands/mega/_estrutura.php`, bloco G idempotente): `tipo VARCHAR(20) NOT NULL DEFAULT 'outro'` em `mega_campos_upload` e `mega_campos_modelos`. Valores canônicos: `video`, `projeto`, `thumb`, `texto`, `outro`. Padrão idempotente igual ao bloco F (`link_mega`).

2. **Helper** `mega_normalizar_tipo()` + const `MEGA_TIPOS_CAMPO` em `_comum.php`.

3. **CRUD do painel grava/lê `tipo`:** `campos_listar.php`, `campos_salvar.php`, `campos_modelos_listar.php`, `campos_modelos_salvar.php`.

4. **UI admin (aba MEGA):** `aba-mega.js` ganhou `<select>` de tipo (Vídeo/Projeto/Thumb/Texto/Outro) na linha editável + coluna na leitura + propagação no payload e nos modelos; `mega.php` ganhou `<th>Tipo</th>` (cache-buster `v=7`). **Admin precisa marcar manualmente, uma vez, o tipo de cada campo já existente** (todos ficam `outro` por padrão).

5. **Novo endpoint** `painel/commands/mega/desktop_obter_status_pasta.php` (GET `?id_pasta_logica`): auth desktop + IDOR via `mega_user_pertence_pasta_logica`. Retorna `arquivos_pasta[]` (todos os uploads concluídos da pasta, de qualquer usuário, com `tipo` resolvido por subquery `mega_campos_upload` e `caminho_remoto` já montado `/raiz/pasta/user_id/arquivo`).

6. **Desktop `app/mega_uploader.py`:** `PainelMegaApi.obter_status_pasta()`; `MegaUploader.baixar_arquivo()` + `_executar_mega_get_streaming()` (espelho do `mega-put`, agora com `mega-get`: progresso, cancelamento, retry em sessão expirada; baixa pra tmp dir dentro do destino → `os.replace` atômico).

7. **Desktop `app/subtarefas.py`** (form MEGA): ao selecionar uma pasta lógica, `_carregar_status_pasta()` busca o status compartilhado e mostra: **(a)** linha verde "✓ Thumb já entregue por <nomes> — não precisa refazer" quando há upload `tipo='thumb'` de outro usuário; **(b)** lista "Arquivos disponíveis nesta pasta" (de outros usuários) com botão 📥 Baixar por arquivo (`asksaveasfilename` + progressbar + Cancelar, espelhando o upload). Pergunta se quer abrir o arquivo ao concluir.

**Verificação:** `php -l` limpo; `py_compile`+import OK; ruff só com achados pré-existentes; pytest 79 passou (as 3 falhas em `test_declaracoes_validacao.py` são pré-existentes, do commit 1f121be, sem relação).

**Correções pós-auditoria (2026-06-05):**
- **#1 download obsoleto:** `desktop_obter_status_pasta.php` agora retorna só o upload mais recente por (user_id, nome_campo) via JOIN com `MAX(id_upload)` — descarta linhas `concluido` de re-uploads ("Trocar arquivo") cujo arquivo já foi apagado do MEGA.
- **#3 regressão colspan:** revertidos pra `colspan="7"` os placeholders da tabela de Pastas no `aba-mega.js` (um `replace_all` largo os tinha mudado pra 8 junto com a tabela de Campos).
- **#4 colspan defasado:** `mega.php` placeholder inicial da tabela de Campos corrigido pra `colspan="8"`.
- **#5 status preso:** `subtarefas.py` `_rebuild_lbx_pasta` agora chama `_limpar_status_pasta_ui()` — ao trocar de canal, a linha verde/lista de download da pasta anterior não fica mais presa.
- **#2 (corrigido — Opção B):** campos enviados como PASTA (nome_arquivo termina em "/") agora baixam de verdade. `MegaUploader.baixar_pasta()` (mega-get recursivo, sem tmp/os.replace) + no form a linha detecta pasta (`eh_pasta`), abre `askdirectory` (escolher pasta de destino) em vez de "Salvar como", e o rótulo mostra 📁. Ao concluir, oferece abrir a pasta baixada.

**Pontos de atenção:**
- **Alteração de banco já no código** (idempotente): a coluna `tipo` é criada na próxima vez que qualquer endpoint MEGA rodar `mega_garantir_estrutura()`. **Ainda não foi aplicada/deployada** — depende de deploy autorizado pelo usuário.
- O `tipo` do upload é resolvido cruzando `mega_uploads.nome_campo = mega_campos_upload.label_campo` (+ user_id + id_atividade). Se o admin renomear o label depois, uploads antigos não casam e caem em `outro` (mesma limitação de toda a tabela).
- O download lista arquivos de **outros** usuários (o material que o thumbmaker precisa) — não os do próprio user.

---

### ✅ 6. Sistema de Log de Atividades no painel ADM (2026-05-20)

**Solução aplicada (Claude 1):**

1. **Tabela `log_atividades`** — criada lazy via `log_atividades_garantir_tabela()` em `painel/commands/_comum/log_atividades.php`. Campos: `id_log`, `data_hora`, `user_id_executor`, `entidade`, `acao`, `id_entidade`, `descricao`, `dados_antes` (JSON), `dados_depois` (JSON), `ip`. Retenção 60 dias com cleanup automático (DELETE LIMIT 5000 a cada listagem).

2. **Função centralizada `log_registrar()`** — nunca quebra a operação principal (try/catch silencioso). Detecta executor da sessão e IP automaticamente.

3. **Endpoints:**
   - `painel/commands/log_atividades/listar.php` — GET com filtros (entidade, ação, executor, busca, período) + paginação + cleanup automático.
   - `painel/commands/log_atividades/detalhe.php` — GET retorna dados_antes/dados_depois decodificados.

4. **Aba "Log" no painel** — `painel/js/aba-log-atividades.js` + section `#abaLogAtividades` em `index.php`. Filtros dinâmicos (populados do banco), paginação, modal de detalhe com antes/depois lado a lado.

5. **Endpoints instrumentados (22 arquivos):**
   - **Usuários:** criar, editar, excluir, salvar_canais
   - **Atividades:** criar, editar, excluir, alterar_status
   - **Subtarefas:** editar
   - **Pagamentos:** criar, editar, excluir
   - **Credenciais:** salvar_modelo, excluir_modelo, salvar_valor, revogar_valor
   - **Auditoria:** salvar_app_suspeito, excluir_app_suspeito
   - **MEGA:** canal_config_salvar, campos_salvar, campos_excluir, campos_modelos_salvar, campos_modelos_excluir

**Pontos de atenção:**
- Tabela criada lazy (primeiro `log_registrar()` cria automaticamente via `CREATE TABLE IF NOT EXISTS`).
- Endpoints desktop (`desktop_registrar_upload`, `desktop_criar_pasta`, etc.) NÃO foram instrumentados — são chamados pelo app Python, não pelo admin. Se quiser logar ações desktop no futuro, basta adicionar `require_once` + `log_registrar()` nesses arquivos.
- Cleanup roda LIMIT 5000 por request de listagem — em bases grandes, pode levar alguns requests para limpar tudo após os 60 dias.

---

### ✅ 5. Bug: aspas e caracteres especiais no nome da pasta lógica quebram upload MEGA (rc=53) (2026-05-20)

**Solução aplicada (Claude 1):**

1. **PHP — `painel/commands/mega/_comum.php` função `mega_normalizar_nome_pasta()`:**
   - Adicionada sanitização antes de retornar: `"` → `'` (legibilidade), e `<>|?*:` removidos.
   - Re-trim após remoção para colapsar espaços residuais.
   - Pastas novas criadas a partir de agora já saem sem caracteres proibidos.

2. **Python — `app/mega_uploader.py`:**
   - Nova função `_sanitizar_caminho_mega()` com `str.maketrans` (mesma regra: `"` → `'`, demais removidos).
   - `_run_mega()`: sanitiza todos os args antes de montar `subprocess.list2cmdline` — protege `mega-mkdir`, `mega-rm`, `mega-ls`, etc.
   - `upload_arquivo()`: sanitiza `pasta_remota` antes de normalizar barras — protege `_executar_mega_put_streaming`.

**Pontos de atenção:**
- Pastas já criadas no MEGA/banco com aspas no nome precisam de rename manual ou script de correção.
- A sanitização é dupla (PHP na criação + Python na execução) para defesa em profundidade.

---

## Tarefas Claude 2

_(nenhuma tarefa pendente no momento)_

---

## Concluídas

### ✅ 4. Cronômetro neutro — validação anti-fraude global por usuário (2026-05-02, v3.1.3)

**Pedido do usuário:** o cronômetro deve ser "neutro" — usuário pode declarar suas horas em qualquer atividade onde tenha subtarefa, não importa em qual atividade ele cronometrou. Bloqueio "Não existe tempo monitorado disponível no cronômetro para esta atividade" não fazia sentido para o propósito do projeto.

**Estado anterior:**
- **Painel** (`editar.php`): já validava global por usuário (sem filtro de atividade).
- **Desktop** (`declaracoes_dia.py::_validar_tempo_contra_monitoramento`): validava por atividade. Inconsistente com o painel.

**Solução aplicada (Claude 1):**
- [declaracoes_dia.py:739-771](declaracoes_dia.py#L739-L771): `_validar_tempo_contra_monitoramento` agora chama `obter_segundos_monitorados_do_dia(user_id, None, 0)`, `obter_abatimento_total_atividade(user_id, 0)` e `obter_segundos_declarados_do_dia(user_id, None, 0, ...)` — `id_atividade=0` significa "todas as atividades do user". Parâmetro `id_atividade` removido da assinatura (não tinha mais uso).
- 3 call-sites internos atualizados ([declaracoes_dia.py:1037-1041, 1095-1099, 1399-1403](declaracoes_dia.py#L1037)).
- Mensagens de erro ajustadas: removida a expressão "para esta atividade".
- Testes ([tests/test_declaracoes_validacao.py](tests/test_declaracoes_validacao.py)) atualizados pra nova assinatura — 15/15 passando.
- `app/config.py`: `VERSAO_APLICACAO` bumpada para `v3.1.3` + entrada em `HISTORICO_VERSOES`.
- `!projeto.md` atualizado em 3 pontos (descrição de `declaracoes_dia.py`, armadilhas do desktop, descrição de `pagamento_abatimentos`).

**Anti-fraude permanece intacto:** continua impossível declarar mais horas do que o usuário trabalhou no total. Só relaxa a granularidade (de "por atividade" para "por usuário").

**Pontos de atenção:**
- `pagamento_abatimentos` continua gravando snapshot por `(user_id, id_atividade)` para rastro histórico, mas o reset de ciclo é por usuário. Se o user cronometrar em ativ X e declarar em ativ Y, os números por atividade na tabela vão ficar descasados — é esperado e não afeta funcionalidade.
- Auto-update do desktop compara por `Content-Length` ([app_shell.py:524-528](app/app_shell.py#L524-L528)). Bump de versão é cosmético (UI/título/novidades), não condição pro update funcionar.

---

### ✅ 3. Fix `Cronometradas: 00:00:00` no desktop (2026-05-02)

**Sintoma:** alex (e potencialmente todos os usuários) viam `Cronometradas: 00:00:00` no rodapé da `JanelaSubtarefas`, impossibilitando declarar — apesar do gráfico do painel mostrar as horas corretas (5h44 trabalhado + 36min ocioso no dia 02/05).

**Causa raiz:**
A query em [declaracoes_dia.py:637-641](declaracoes_dia.py#L637-L641) buscava `MAX(data_pagamento) FROM Pagamentos WHERE user_id = %s AND id_atividade = %s` — mas a tabela `Pagamentos` em produção tem `id_usuario` (FK int), não `user_id`, e **não tem** `id_atividade` (essa vive em `pagamento_abatimentos`). Toda chamada lançava `SQLSTATE 42S22 Unknown column 'user_id'`. O `except Exception: return 0` em [declaracoes_dia.py:659-660](declaracoes_dia.py#L659-L660) silenciava o erro e retornava 0 segundos. Bug afetava 100% dos usuários do desktop, não só o alex.

**Solução aplicada (Claude 1):**
- [declaracoes_dia.py:637-646](declaracoes_dia.py#L637-L646): query trocada para o padrão das outras 3 queries do mesmo arquivo: `SELECT MAX(p.data_pagamento) FROM Pagamentos p JOIN usuarios u ON u.id_usuario = p.id_usuario WHERE u.user_id = %s`. Removido o filtro `id_atividade` (pagamento é por usuário no schema atual, não por atividade).
- Validação contra produção: alex tem 12:18:43 cronometradas no ciclo atual (após pagamento de 2026-05-01).

**Pontos de atenção:**
- `!projeto.md` atualizado: nova armadilha sobre `Pagamentos.id_usuario` (não `user_id`) na lista de armadilhas do desktop.
- Auto-update do desktop compara por `Content-Length` ([app_shell.py:524-528](app/app_shell.py#L524-L528)), não por versão — não foi necessário bumpar `VERSAO_APLICACAO`. Rebuild basta.
- Nenhuma hora foi perdida; `cronometro_relatorios` estava intacto. Era apenas um bug de leitura/cálculo no desktop.

---

### ✅ 2. Fix MEGA upload em PCs com espaço no nome de usuário Windows (2026-05-02)

**Sintoma reportado pelo Marcus:**
> `upload falhou (rc=1): 'C:\Users\Marcus' não é reconhecido como um comando interno ou externo, um programa operável ou um arquivo em lotes.`

**Causa raiz:**
`app/mega_uploader.py` invocava o `.bat` do MEGAcmd via `["cmd.exe", "/c", str(bat), *args]`. Quando o caminho do `.bat` contém espaço (no PC do Marcus o usuário Windows é `Marcus Vinicius`, então o caminho fica `C:\Users\Marcus Vinicius\AppData\...\mega-put.bat`), o `subprocess` adiciona aspas em torno desse argumento — mas o `cmd.exe /c` tem uma regra de parsing peculiar: quando há mais de um par de aspas na linha, **descarta as aspas externas do primeiro argumento**. Resultado: `cmd.exe` interpreta `C:\Users\Marcus` como o nome do programa e `Vinicius\AppData\...` como argumento, daí o "não reconhecido como comando".

**Solução aplicada (Claude 1):**
- Em `_run_mega` ([app/mega_uploader.py:585-593](app/mega_uploader.py#L585-L593)) e em `_executar_mega_put_streaming` ([app/mega_uploader.py:753-758](app/mega_uploader.py#L753-L758)): em vez de passar lista, montar a linha com `subprocess.list2cmdline([str(bat), *args])` e envolver tudo num par de aspas externas adicional: `f'cmd.exe /c "{linha}"'`. Esse padrão `cmd /c "..."` faz o `cmd.exe` tratar todo o conteúdo entre as aspas externas como uma linha única, preservando as aspas internas dos caminhos.
- `_executar_silencioso` ([app/mega_uploader.py:129](app/mega_uploader.py#L129)): tipo de `comando` ampliado para `list[str] | str` (subprocess no Windows aceita string com `shell=False` e passa direto para `CreateProcessW`).

**Pontos de atenção:**
- Bug nunca aparecia em PCs com nome de usuário sem espaço (Lucas, Rafael, etc.) — só dispara quando o caminho do MEGAcmd tem espaço.
- O fallback de senha em mensagens de erro (`saida_limpa = saida.replace(senha, "***")`) continua igual, sem mudança.
- Sem mudança de comportamento esperada em PCs já em produção.

---

### ✅ 1. Chave Pix por usuário no painel e no desktop (2026-05-01)

**Solução aplicada (Claude 1):**

- **Banco:** coluna `usuarios.chave_pix VARCHAR(255) NULL` criada idempotentemente via `painel/commands/_comum/usuarios_estrutura.php#usuarios_garantir_chave_pix()` — chamada nos endpoints que dependem dela.
- **Validação compartilhada:** `app/validador_pix.py` (Python) + `painel/commands/_comum/pix.php` (PHP) com mesma especificação. Aceita CNPJ(14d+DV), celular BR(10–11d com DDD), e-mail. Recusa CPF (11d sem padrão de celular) com mensagem dedicada e qualquer outro formato.
- **Endpoints novos para o desktop** (auth via `credenciais/api/_auth_cliente.php` — Bearer `user:chave`):
  - `painel/commands/usuarios/api/obter_pix.php` — GET, retorna `{chave_pix, tipo}` do próprio user.
  - `painel/commands/usuarios/api/salvar_pix.php` — POST `{chave_pix:"..."}`. Vazio = limpa.
- **Painel (aba Usuários):**
  - `listar.php` retorna `chave_pix` no JSON.
  - Nova coluna "Chave Pix" entre "R$/hora" e "Status" em `index.php` (colspan ajustado de 6 → 7).
  - `aba-usuarios.js` renderiza célula com `••••••••` por padrão e botão olho (`data-acao-usuario="alternar-pix"`) que revela/oculta o valor sem chamar o servidor (já vem no listar). Sem cadastro = "Não cadastrada" em texto fraco. Tipo (CNPJ/Celular/E-mail) detectado client-side por `classificarTipoPix()`.
- **Desktop (`app/subtarefas.py`):**
  - Botão "Configurar Pix" no rodapé da `JanelaSubtarefas`, ao lado de "Fechar" (e em modo finalização ao lado de "Cancelar"/"Encerrar").
  - Ao clicar abre `Toplevel` modal com campo de entrada. Faz `GET obter_pix.php` em background ao abrir (`threading.Thread`); se vazio, campo vazio; se preenchido, mostra valor em texto aberto pra editar.
  - Salvar valida localmente via `validador_pix.validar_pix()` antes de mandar; backend revalida (`pix_validar()`).
  - HTTP via `urllib.request` standalone — helpers `_http_pix_obter` / `_http_pix_salvar` no topo do módulo.
- **PyInstaller (`CronometroLeve.spec`):** `app.validador_pix` adicionado a `hiddenimports`.
- **`!projeto.md` atualizado** com: novo módulo no mapa do desktop, helpers PHP em `_comum/`, nova rota `usuarios/api/`, e nota de que `usuarios.chave_pix` é criado lazy.

**Critérios de aceite atendidos:**
- ✅ Cadastro pelo desktop em Tarefas da Atividade (Configurar Pix).
- ✅ Aceita CNPJ válido, celular válido, e-mail válido.
- ✅ Recusa CPF (mensagem dedicada).
- ✅ Recusa chave aleatória.
- ✅ Coluna "Chave Pix" oculta por padrão na aba Usuários, com botão olho.
- ✅ Usuário só altera a própria Pix pelo desktop (auth `user:chave` via `_auth_cliente.php`).
- ✅ Validação igual em desktop e backend.
- ✅ `!projeto.md` atualizado.

**Pontos de atenção:**
- A migration roda lazy via `usuarios_garantir_chave_pix()` em `listar.php`/`obter_pix.php`/`salvar_pix.php` — primeira chamada após deploy roda o `ALTER TABLE`. Se preferir, rodar manualmente: `ALTER TABLE usuarios ADD COLUMN chave_pix VARCHAR(255) NULL DEFAULT NULL;`.
- `app/validador_pix.py` e `painel/commands/_comum/pix.php` precisam ser mantidos em sincronia se a regra mudar. A nota está no docstring de cada um e no `!projeto.md`.
