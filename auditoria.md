# Bugs críticos descobertos — varredura colaborativa multi-IA

> **Como usar este arquivo:**
> - Múltiplas IAs estão varrendo a plataforma em paralelo procurando bugs e problema de segurança.
> - **Antes de adicionar um bug/problema**, faça `grep` aqui pra ver se já está documentado (mesmo arquivo/linha/sintoma).
> - **Critério "crítico":** mistura dados entre tenants, dado que deveria salvar e não salva, dado que deveria ser deletado e fica órfão, estados incoerentes, botões que não funcionam, falhas de segurança.
> - **Ignorar:** bugs já listados em `!executar.md` e os que estão como "concluído" aqui.
> - Cada bug deve descrever **QUANDO acontece** (linguagem leiga), arquivo/linha, severidade, e detalhe técnico opcional, e **qual o impacto** disso no usuário.
> - **Não corrigir nada** aqui — só catalogar pro humano testar e então pedir explicitamente depois para corrigir o bug.
> - **Status** Bugs achados devem colocar como pendente de correção e bugs arrumados colocar status concluido

---

## Convenção de severidade
> Cada um recebe uma nota onde nota 0 = indiferente não vai mudar nada pro usuario final nem pra segurança do sistema e 10 = Crítico ou muito grave para o sistema onde vai impedir o uso correto da plataforma.

- 🔴 **Crítico — Nota 9-10**
  Bugs que colocam o sistema, os dados ou os usuários em risco grave.  
  Inclui: vazamento ou mistura de dados entre tenants/usuários, falhas de segurança exploráveis, perda permanente de dados, arquivos/dados que deveriam ser excluídos e permanecem no banco/servidor, valores monetários incorretos, cobranças erradas, ações importantes que parecem funcionar mas não persistem, dados que somem do sistema, corrupção de dados ou qualquer falha que possa gerar prejuízo financeiro, jurídico ou de segurança.

- 🟠 **Alto — Nota 7-8**
  Bugs que quebram funcionalidades importantes em cenários comuns, mas sem causar vazamento grave, perda permanente de dados ou risco crítico imediato.  
  Inclui: botões ou fluxos principais que não funcionam, usuário impedido de concluir uma ação importante, dados exibidos de forma errada mas recuperável, permissões incorretas sem vazamento crítico, falhas frequentes em produção, erros que exigem intervenção manual, duplicação de registros, race conditions ativas com impacto real, ou bugs que afetam muitos usuários.

- 🟡 **Médio — Nota 5-6**
  Bugs que causam inconsistência, confusão ou falha parcial, mas possuem contorno simples e não impedem o uso principal do sistema.  
  Inclui: edge cases reproduzíveis, validações incompletas, mensagens de erro ruins, filtros/paginação/ordenação com falhas pontuais, dados temporariamente inconsistentes, problemas visuais que atrapalham um pouco, falhas que ocorrem apenas em combinações específicas de ações, ou comportamentos errados que não causam perda de dados, falha de segurança ou bloqueio do usuário.

- 🟢 **Baixo — Nota 0-4**
  Bugs pequenos, cosméticos ou de baixa prioridade, sem impacto relevante no usuário final, na segurança, nos dados ou no funcionamento principal do sistema.  
  Inclui: textos errados, desalinhamentos visuais leves, ícones incorretos, pequenos problemas de espaçamento, logs desnecessários, mensagens pouco claras mas não bloqueantes, inconsistências visuais raras ou melhorias que não afetam o uso real.

Regra geral:
A nota deve considerar o pior impacto realista do bug, não apenas o erro visível na tela.

Se envolver segurança, dinheiro, perda de dados, mistura de dados entre usuários/tenants ou falha de exclusão/persistência de dados sensíveis, a severidade deve subir automaticamente para Alto ou Crítico.

Se o bug tiver contorno simples, afetar poucos usuários e não envolver dados sensíveis, segurança ou dinheiro, a severidade pode ser reduzida.

---

## Bugs em catalogação:

### Pendente de correção:

---

> **Bugs #1–#5 → CORRIGIDOS em 2026-06-02** (seção Concluído, números originais).
> **Bugs #6, #7, #8, #10, #11, #12 → CORRIGIDOS em 2026-06-02 (Claude 1)** — movidos para a seção **Concluído**.
>
> Seguem **PENDENTES**: **#9** (aguarda decisão do usuário — abatimento é snapshot imutável por design), **#14** (pendente), **#15** (won't-fix), **#16** (baixo). Observação: #1 e #4 haviam sido corroborados por outra varredura.

---

#### 9. 🟡 Médio (5) — Reabrir subtarefa não reverte o abatimento já consumido → saldo do próximo ciclo encolhe

- **QUANDO ACONTECE:** subtarefa concluída e declarada; houve um pagamento que gerou snapshot de abatimento contando aquele saldo; depois o usuário reabre uma subtarefa NÃO bloqueada do mesmo ciclo.
- **ONDE:** `declaracoes_dia.py:1139-1151` (reabrir zera `segundos_gastos`/`concluida`, sem tocar em `pagamento_abatimentos`).
- **SEVERIDADE:** 🟡 Médio 5 (cenário de borda; o usuário "perde" horas reais no saldo futuro).
- **IMPACTO:** o `declarado` cai mas o `abatido` (snapshot imutável) permanece, então o saldo disponível para o próximo ciclo diminui indevidamente.
- **DETALHE TÉCNICO:** `reabrir_subtarefa` só é barrado por `subtarefa_esta_travada` (bloqueada_pagamento=1); subtarefas concluídas mas ainda desbloqueadas passam, desbalanceando `monitorado − declarado − abatido`. **Confiança: média** (exige sequência específica).
- **DECISÃO DO USUÁRIO (2026-06-02): won't-fix por ora — manter documentado.** O `pagamento_abatimentos` é um snapshot **imutável por design** (chave `(user_id, id_pagamento, id_atividade)`, NÃO por subtarefa — não dá pra "estornar" a parcela de uma sub específica). O gatilho é estreito (sub concluída+declarada, NÃO bloqueada, fora de período travado) e o impacto é **contra o próprio usuário** (encolhe o saldo declarável futuro, não gera pagamento a mais). Fica registrado; reabrir só se o usuário pedir. Opções avaliadas: bloquear reabertura no ciclo abatido / recomputar abatimento / aceitar (escolhida).

---

> **Varredura Claude 1 (2026-06-02) — foco: "usuário trabalha e as horas não contam / declaração fica zerada".** Achados NOVOS abaixo (#13-#21), não cobertos por #1-#12 nem pelo `!executar.md`. **#13, #17, #18, #19, #20, #21 → CORRIGIDOS** (ver seção Concluído). **#14, #15, #16 seguem como estão** (#14 pendente; #15 won't-fix; #16 baixo).

---

#### 14. 🟡 Médio (5-6) — Sessão que vira a meia-noite distribui as horas entre os dias pelo relógio, não pelo trabalho real (pode jogar horas no ciclo de pagamento errado)

- **QUANDO ACONTECE:** quando uma única sessão fica aberta cruzando a meia-noite (ex.: trabalha à noite, deixa a máquina ligada, volta a trabalhar no dia seguinte). As horas trabalhadas são repartidas entre os dois dias **na proporção do tempo de relógio em cada dia**, e não conforme em qual dia o trabalho realmente aconteceu.
- **ONDE:** `app/win32_utils.py:232-245` (`dividir_tempos_por_dia` — `frac = seg_dia / total_segundos`, onde `seg_dia` é o tempo de relógio do dia) chamado por `app/monitor.py:1246-1256`.
- **SEVERIDADE:** 🟡 Médio 5-6 (o total geral é preservado; o problema é a distribuição por dia/ciclo).
- **IMPACTO:** se um pagamento cair entre os dois dias, horas que foram trabalhadas no dia anterior podem ser atribuídas ao dia seguinte (ou vice-versa) e cair no ciclo de pagamento errado — reaparecendo como "disponível" ou desaparecendo do ciclo. Também distorce o "monitorado por dia" exibido. Relacionado em tema ao #2, mas é **mecanismo diferente** (lá é o `criado_em`; aqui é a regra de rateio por dia).
- **DETALHE TÉCNICO:** ex.: sessão das 22h às 10h (relógio = 12h), com 2h reais trabalhadas antes da meia-noite e 2h depois (resto ocioso/pausado). O rateio dá `frac_dia1 = 2/12 ≈ 0,167` → ~0h40 no dia 1 e ~3h20 no dia 2, quando o real era 2h/2h. A soma (4h) continua certa, mas a quebra por dia fica errada. **Confiança: alta no código; média no impacto (depende de sessões longas cruzando a meia-noite + pagamento no intervalo).**

---

#### 15. 🟡 Médio (5) — Sessão "maratona" nunca finalizada para de contar horas ao bater 30h (silenciosamente)

- **QUANDO ACONTECE:** quando o usuário **nunca clica em Finalizar/Zerar** e mantém a mesma sessão por vários dias (cenário "máquina sempre ligada" descrito no `reminder.md`). Ao atingir 30h de trabalho acumulado na sessão, o cronômetro **para de somar** novas horas trabalhadas — o usuário continua trabalhando, mas as horas não contam mais.
- **ONDE:** `app/monitor.py:226-237` (cap `LIMITE_HORAS_MAXIMO`) + `app/config.py:344` (`LIMITE_HORAS_MAXIMO = 30 * 3600`).
- **SEVERIDADE:** 🟡 Médio 5 (perde horas reais em sessões longas; sem aviso ao usuário).
- **IMPACTO:** o contador `segundos_trabalhando` da sessão satura em 30h e qualquer trabalho além disso é descartado em silêncio. Quando o usuário finalmente declara, falta tempo no teto — "trabalhei mais, mas o sistema não deixa declarar". O cap só zera ao **Iniciar nova sessão** (ou Zerar/Finalizar); pausar/retomar **não** reinicia a contagem.
- **DETALHE TÉCNICO:** o cap é aplicado por sessão sobre o acumulador em memória; em `_acumular_tempo_ate_agora_locked`, quando `_segundos_trabalhando_float >= LIMITE_HORAS_MAXIMO` o `+= delta` é pulado. Foi pensado como anti-runaway de hibernação, mas pune o uso legítimo de quem não finaliza a sessão por dias. **Confiança: alta no código; média na frequência (precisa de 30h de trabalho ativo numa sessão sem finalizar).**
- **DECISÃO DO USUÁRIO (2026-06-02):** o teto de 30h é **intencional** (proteção anti-runaway) e foi mantido, inclusive deixado **simétrico** para o ocioso (ver #5 em Concluído). Este item fica como **won't-fix por ora** — reabrir só se o usuário decidir repensar a regra do teto.

---

#### 16. 🟢 Baixo (3-4) — Travada longa do app/banco (>60s) descarta o tempo trabalhado daquele intervalo

- **QUANDO ACONTECE:** se o loop interno do cronômetro ficar parado por mais de 60s seguidos — não só por hibernação, mas também sob carga pesada de CPU ou quando uma operação de rede/banco trava perto do timeout — o tempo trabalhado durante aquela janela é descartado.
- **ONDE:** `app/monitor.py:215-217` (`_MAX_DELTA_TEMPO_SEGUNDOS = 60.0` — `if delta > 60: descarta`).
- **SEVERIDADE:** 🟢 Baixo 3-4 (na operação normal o loop roda a cada 0,2s e nunca chega perto de 60s; só dispara em travadas longas).
- **IMPACTO:** ao detectar um intervalo > 60s entre dois "marcos", o código assume hibernação e zera o delta inteiro, sem distinguir uma travada real de trabalho. Em quedas de conexão com timeout alto (combina com o cenário offline do #3), o intervalo do trabalho pode ser perdido.
- **DETALHE TÉCNICO:** mesmo padrão de cap existe no foco (`_MAX_DELTA_FOCO_SEGUNDOS`) e no scan de apps. Não há como diferenciar "PC dormiu" de "loop atrasou 60s" — ambos caem no mesmo descarte. **Confiança: alta no código; baixa na frequência real.**

---

> ✅ **RECONCILIAÇÃO DE NUMERAÇÃO (2026-06-02, Claude 1):** a 2ª passada tinha catalogado #17/#18 (concluir-lock / horas_mes), colidindo com os #17/#18 de outra varredura (relatório zerado / declaração recusada, em Concluído). Para resolver, **renumerei os meus dois achados para #26 e #27** (números livres) e os movi para a seção **Concluído** — ambos já CORRIGIDOS. Não toquei nas entradas alheias.

> **Auto-revisão Claude 1 (2026-06-02) — "minhas correções introduziram bug?"** Revisão adversarial das mudanças que apliquei (#17/relatório, #18/congelado, #19/ocioso, #20/dupla-contagem, #21/foco). Achei 1 risco real (#22, já CORRIGIDO acima) + 3 notas de comportamento abaixo (#23-#25).

#### 23. 🟢 Baixo (2-3) — `tempo_trabalhado.php`: coluna "Trabalhado" agora inclui horas de ciclos JÁ PAGOS

- **QUANDO ACONTECE:** sempre, na aba Relatório, após a correção #17. Ao trocar a fonte de `registros_tempo` (vazia) para `cronometro_relatorios`, o filtro `id_pagamento IS NULL` (que excluía horas pagas) foi removido — essa coluna não existe em `cronometro_relatorios`.
- **ONDE:** `painel/commands/relatorio/tempo_trabalhado.php:135-143` (query da seção 2).
- **SEVERIDADE:** 🟢 Baixo 2-3 (NÃO afeta cálculo de dinheiro — valor estimado/pendente vêm de declarado + `Pagamentos`; só a coluna informativa "Trabalhado" e o selo de divergência, que fica mais permissivo).
- **IMPACTO:** "Trabalhado" passa a refletir o total trabalhado no período, inclusive horas de ciclos já pagos. Como o filtro antigo era inócuo (tabela vazia), na prática isso só "ligou" a coluna. Provavelmente é o comportamento desejado, mas é mudança vs a intenção original. Se for preciso excluir horas pagas, teria que cruzar com `pagamento_abatimentos` (não há `id_pagamento` por linha em `cronometro_relatorios`). **Confiança: alta (introduzido por mim na #17).**

#### 24. 🟢 Baixo (2-3) — `tempo_trabalhado.php`: total "Trabalhado" por usuário conta só dias COM declaração + mapa `$trab_por_usuario` é código morto

- **QUANDO ACONTECE:** na aba Relatório, após a #17. O relatório itera sobre as linhas **declaradas** e busca o trabalhado por `user|dia`; dias trabalhados mas **sem declaração** não viram linha nem entram no total de trabalhado do usuário.
- **ONDE:** `painel/commands/relatorio/tempo_trabalhado.php:232-283` (loop sobre `$linhas_raw` declaradas) + `$trab_por_usuario` (l.147-153) computado e nunca usado.
- **SEVERIDADE:** 🟢 Baixo 2-3 (limitação estrutural **pré-existente** — o relatório sempre foi orientado a declaração; antes o trabalhado era sempre 0, então não se notava).
- **IMPACTO:** o "Trabalhado total" por usuário pode subcontar (ignora dias trabalhados-sem-declarar). Não afeta a detecção de fraude (dia sem declaração não tem o que comparar). Correção possível: usar o `$trab_por_usuario` (já calculado, total real por usuário) para o total por usuário — mas isso criaria divergência entre o total e a soma das linhas por dia; decisão de produto. **Confiança: alta (verificado que `$trab_por_usuario` não é usado na resposta).**

#### 25. 🟢 Baixo (1-2) — I/O extra no banco: cada declaração/reload/fechamento agora dispara um upsert do relatório parcial

- **QUANDO ACONTECE:** após as correções #18/#19/#20, cada declaração, cada "Atualizar" da janela de tarefas e cada fechamento/logout chamam `_upsert_relatorio_parcial` (flush da sessão no banco).
- **ONDE:** `app/subtarefas.py::_sincronizar_e_obter_adicional` + `app/monitor.py::pausar_e_preservar_sessao`.
- **SEVERIDADE:** 🟢 Baixo 1-2 (sem impacto funcional; só mais escritas, frequência comparável ao flush periódico de 5min do loop, agora também sob ação do usuário).
- **IMPACTO:** leve aumento de escritas em `cronometro_relatorios`. Mitigado: o upsert agora é serializado por lock (#22) e é idempotente (UPDATE quando a linha já existe). **Confiança: alta (consequência direta das correções).**

---

> **Varredura Claude 1 (2026-06-06) — foco: "erro ao baixar do MEGA" + "pasta declarada não aparece em Selecionar existente".** Causa-raiz comum: a **sanitização de nomes** (`_sanitizar_caminho_mega`, remove `< > | ? * "`) era aplicada de forma **inconsistente** entre criar pasta / listar / baixar / comparar na sync. Achados #28–#31 → **TODOS CORRIGIDOS 2026-06-06** (ver Concluído).

---

### Concluído:

#### 28. 🟠 Alto (8) — Pastas declaradas com `?` `"` `*` `<` `>` `|` no título SOMIAM de "Selecionar existente" (sync diária as inativava por erro de comparação) — CORRIGIDO 2026-06-06 (Claude 1)

- **Era:** a sincronização diária comparava `nome_pasta` (cru, com `?`) contra a listagem do MEGA (onde a pasta existe já sanitizada, sem `?`) usando só `_normalizar_nome_pasta_mega` — nunca batia → marcava como inativa. Como o canal é cheio de títulos em pergunta, atingia a maioria. **Confirmado no banco: 10 inativas com caractere sanitizado, 9 ativas em risco.**
- **ONDE estava:** `app/mega_sync.py:151-159`; filtro de exibição em `painel/commands/mega/pasta_logica_listar.php:24` (`p.ativo=1`).
- **Solução aplicada:** a comparação agora aceita match contra o nome **cru OU o sanitizado** (`_sanitizar_caminho_mega` importado em `mega_sync.py`) — cobre pastas criadas das duas formas; só inativa se nenhuma das duas existir no MEGA. `py_compile` OK. **(2026-06-06, parte 2)** `_normalizar_nome_pasta_mega` passou a remover **ponto/espaço final** (`.rstrip(" .")`) nos dois lados da comparação — o Windows/MEGAcmd descarta o ponto no fim (ex.: "03 - O MAIOR ERRO de Einstein.") e isso inativava a pasta indevidamente. **Confirmado ao vivo:** Fala Sacani 01/02/03 (ids 32, 34, 39) tinham sumido de "Selecionar existente"; reativadas.
- **⚠️ DEPENDE DE BUILD NOVO:** as correções estão no código Python do app desktop. **O app que o usuário roda ainda tem o sync ANTIGO**, que re-inativa as pastas a cada start. Enquanto não gerar/deployar um build novo, qualquer reativação no banco é desfeita no próximo start do app.
- **Reativação (autorizada pelo usuário, 2026-06-06):** `UPDATE mega_pasta_logica SET ativo=1` nas **5 vítimas legítimas** (ids 30, 31, 35, 95, 98 — têm uploads e sem gêmea ativa). **NÃO reativadas** (pendente decisão do usuário): id=47 (Artemis 3?, 6 uploads, mas gêmea ativa id=51); ids 89/99/100 (0 uploads, duplicatas vazias de 93/105); id=110 (`""asdasd`, lixo de teste).

#### 29. 🟠 Alto (7) — Download falhava ("Couldn't find"/rc=53) em itens cujo nome FÍSICO no MEGA contém `?` `"` etc. (download removia o caractere e procurava nome inexistente) — CORRIGIDO 2026-06-06 (Claude 1)

- **Era:** lado espelhado do #28. `baixar_arquivo`/`baixar_pasta` sempre sanitizavam o caminho; se o MEGA tivesse a pasta com o caractere físico (criada fora do app / versão antiga), o download procurava a versão "limpa" que não existe → rc=53. Caso provável: Asteróide (id=98).
- **ONDE estava:** `_sanitizar_caminho_mega` (`mega_uploader.py:129`) em `baixar_arquivo`/`baixar_pasta`; caminho montado em `painel/commands/mega/desktop_obter_status_pasta.php:104`.
- **Solução aplicada:** `baixar_arquivo`/`baixar_pasta` ganharam parâmetro `sanitizar: bool=True`; com `False` pulam a sanitização. `app/subtarefas.py::_op` agora tenta uma lista de **candidatos** (caminho atual e legado × sanitizado e cru), com dedup pelo caminho efetivo, parando no 1º sucesso e só avançando em erro "não encontrado". Cobre as duas falhas (subpasta `/<user_id>/` ausente E caractere especial físico). `py_compile` OK.
- **Blindagem da geração de link (2026-06-06):** o mesmo problema afetava `mega-export` (geração de link público), que não achava pastas com caractere físico. `_run_mega` ganhou `sanitizar: bool=True`; `MegaUploader.exportar_link` (`mega_uploader.py`) e o script `tools/sync_mega_links.py` agora tentam o caminho **sanitizado E o cru**. Assim toda pasta (inclusive com `?`/`"`) consegue gerar/recuperar o link. `py_compile` OK; testes 79/82 (3 pré-existentes).

#### 30. 🟡 Médio (5) — Caracteres `%` `&` `^` não sanitizados podiam quebrar o comando `cmd.exe` no upload/download/sync — CORRIGIDO 2026-06-06 (Claude 1)

- **Era:** `_MEGA_CHARS_PROIBIDOS` só tratava `< > | ? * "`. O comando roda como `cmd.exe /c "..."`, então `%` (expansão), `&` (separador) e `^` (escape) podiam corromper a linha. Latente hoje (sem `% &` no banco).
- **ONDE estava:** `mega_uploader.py:119`.
- **Solução aplicada:** adicionados `% & ^` ao mapa de remoção (mkdir/put/get/ls usam a mesma sanitização → nome casa nos dois lados). `:` e `\` **não** entraram (já existem em pastas no MEGA — removê-los quebraria o casamento). `py_compile` OK.

#### 31. 🟠 Alto (7) — Download de arquivos enviados ANTES de 2026-05-17 falhava ("Couldn't find") porque o caminho montava a subpasta `/<user_id>/` que não existia — CORRIGIDO 2026-06-06 (Claude 1)

- **Era:** a subpasta por usuário no MEGA passou a existir no upload em 2026-05-17 (commit `4464923`); a função de baixar foi criada em 2026-06-05 (`af543de`) montando o caminho **sempre** com `/<user_id>/`. Arquivos enviados antes de 17/05 ficam soltos na raiz da pasta lógica (sem o nível do user), então o `mega-get` procurava num nível inexistente → rc=53. Confirmado no banco: pasta "03 - O MAIOR ERRO de Einstein." (id=39), uploads do user `alex` em 2026-05-06.
- **ONDE estava:** `app/subtarefas.py` (`_baixar_arquivo_da_pasta` → `_op`); caminho vem de `painel/commands/mega/desktop_obter_status_pasta.php:104` (`/<raiz>/<nome_pasta>/<user_id>/<arquivo>`).
- **Solução aplicada:** em `app/subtarefas.py::_op`, fallback automático: tenta o caminho com a subpasta do usuário e, se falhar com "não encontrado" (`Couldn't find`/`not found`/`rc=53`), refaz no **caminho legado** sem o nível `/<user_id>/` (helpers `_caminho_legado` e `_eh_nao_encontrado`). Só cai no fallback nesse erro específico; cancelamento e outros erros propagam. Não migra nada no MEGA nem no banco. `py_compile` OK. **NÃO resolve o #29** (caractere `?` no nome físico do MEGA) — só o caso da subpasta.

#### 6. 🟠 Alto (7-8) — Total "A pagar" do Dashboard ficava MENOR que a soma real quando um membro foi pago a mais — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** o total geral fazia `Math.max(0, total_geral_valor − totalPago)` somando o `valor_estimado` BRUTO e subtraindo o pago total; o excedente pago a um membro abatia a dívida com os outros, subestimando o total a pagar.
- **Solução aplicada:** em `painel/js/aba-graficos.js` (`renderizarTempoDeclarado`), o "A pagar" total passou a ser a **soma dos `valor_pendente` já clampados por usuário** (`max(0, valor_estimado − total_pago)`, mesmo valor exibido nos cards), via `reduce` sobre `dados.totais_por_usuario`. Agora o total bate com a soma dos cards. Backend (`tempo_trabalhado.php:292`) já fornecia `valor_pendente` por usuário.

#### 7. 🟡 Médio (5-6) — Resumo da Gestão zerava "Pago"/"A pagar" quando o membro não tinha subtarefa no período — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** o frontend lia todos os agregados de `subs[0]`; com a lista de subtarefas vazia (ex.: filtro "30 dias"), tudo zerava — inclusive "Pago", que não depende de existir subtarefa.
- **Solução aplicada:** `painel/commands/atividades_subtarefas/listar.php` agora calcula os agregados do usuário filtrado mesmo sem subtarefas (adiciona o `user_id` a `$userIds`) e devolve um campo de topo `resumo`. `painel/js/aba-usuarios.js::carregarResumoHorasPagamento` lê `rSub.resumo` com fallback para `subs[0]`. `php -l` OK.

#### 8. 🟡 Médio (5-6) — Operações de foco do loop rodavam FORA do lock (race com pausar/retomar/finalizar) — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** o loop chamava `_fechar_foco`/`_abrir_foco`/`_flush_foco_periodico` sem `self._trava`, enquanto pausar/retomar/finalizar/zerar mexem nos mesmos contadores (`_id_foco_aberto`, `_segundos_em_foco_atual`) segurando o lock → race que sujava `cronometro_foco_janela`.
- **Solução aplicada:** em `app/monitor.py::_loop`, o bloco de foco foi envolvido em `with self._trava:` (mesmo padrão do `_salvar_estado_local_locked` logo acima). Os `_locked` helpers não readquirem o lock — sem risco de deadlock. `py_compile` OK; 79/82 testes (as 3 falhas são pré-existentes, de texto de mensagem, não relacionadas).

#### 10. 🟡 Médio (5) — "Declarado não-pago" do Resumo ignorava o filtro de período — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** `mapaDeclNaoPago` (vira `segundos_declarados_total`) não concatenava `{$filtroResumoRef}`, ao contrário de `mapaCron`/`mapaDecl`; no modo "30 dias" misturava todo o histórico. Consumidor real (`aba-gerenciar-tarefas.js`, modo "tudo") deixava o defeito dormente.
- **Solução aplicada:** adicionado `{$filtroResumoRef}` à query de `mapaDeclNaoPago` em `painel/commands/atividades_subtarefas/listar.php`. Mantida a semântica "não pago" (`bloqueada_pagamento = 0`, sem `concluida = 1`) para não divergir do teto anti-fraude do `editar.php`. `php -l` OK; em modo "tudo" o filtro é vazio → sem mudança de comportamento.

#### 11. 🟡 Médio (5) — `finalizar()` lia os segundos do relatório final FORA do lock — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** `finalizar()` lia `_segundos_*_float`/`_id_sessao`/`_user_id` depois do lock já liberado, ao contrário de `zerar_sessao()` que captura snapshots dentro do lock.
- **Solução aplicada:** em `app/monitor.py::finalizar`, os valores passaram a ser capturados em variáveis snapshot **dentro do lock** (`_id_snap`, `_uid_snap`, `_seg_*_snap`, `_ref_data_snap`) e usados no evento/UPDATE/`_upsert_relatorio_com_snapshots`. `py_compile` OK.

#### 12. 🟢 Baixo (4) — `listar_por_usuario.php` vazava mensagem de erro interna do banco — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** devolvia `$e->getMessage()` cru no JSON mesmo em produção, sem o guard `debug_ativo()`.
- **Solução aplicada:** `painel/commands/pagamentos/listar_por_usuario.php` passou a usar `debug_ativo() ? ['erro' => $e->getMessage()] : null`, alinhado a `criar.php`/`editar.php`/`excluir.php`. `php -l` OK.

#### 1. 🔴 Crítico (9-10) — Painel deixava declarar/editar horas JÁ PAGAS (anti-fraude do painel não subtraía abatimentos) — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** `editar.php` calculava o teto como `trabalhado_total` (soma de toda a vida) menos só o declarado do ciclo atual, **sem subtrair `pagamento_abatimentos`**. Após um pagamento, as horas já pagas continuavam no teto → dava pra declarar/editar e ser pago de novo por elas (pagamento em dobro).
- **Solução aplicada:** em `painel/commands/atividades_subtarefas/editar.php` (bloco de validação de `segundos`), passou a ler `SUM(pagamento_abatimentos.segundos_abatidos)` do usuário (com try/catch caso a tabela não exista) e usar `disponivel_total = max(0, trabalhado_total − abatido_total)` como teto, espelhando o desktop (`_validar_tempo_contra_monitoramento`). A mensagem de erro e o payload agora incluem `segundos_abatidos_total`. `php -l` OK.

#### 2. 🟠 Alto (7-8) — `criado_em` do relatório sobrescrito a cada salvamento parcial deslocava horas entre ciclos — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** o UPDATE parcial em `cronometro_relatorios` reescrevia `criado_em = NOW()` a cada save; numa sessão longa que cruza um pagamento, horas de dias anteriores "pulavam" para o ciclo novo.
- **Solução aplicada:** removido `criado_em = %s` do UPDATE em `app/monitor.py` (`_upsert_relatorio_com_snapshots`). `criado_em` agora é definido **só no INSERT** (criação da linha) e preservado nos updates, voltando a ser uma âncora de ciclo estável.

#### 3. 🟠 Alto (7-8) — Falha ao gravar fila offline / estado local era engolida silenciosamente — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** `_salvar_fila_offline` e `_salvar_estado_local_locked` usavam `except Exception: pass`; falha de I/O (disco cheio, AV, permissão) descartava eventos offline / sessão em aberto sem nenhum rastro.
- **Solução aplicada:** em `app/monitor.py`, os dois `except` agora registram o erro via `LOG_TEC.log(...)` (com a exceção e o tamanho da fila), tornando a falha diagnosticável. O retorno 0/silencioso de antes deixou de ser invisível. (Retry/persistência robusta fica como melhoria futura, mas a perda silenciosa foi eliminada.)

#### 4. 🟡 Médio (5-6) — Leituras de tempo retornavam 0 em erro de banco sem log (bloqueio enganoso) — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** 4 funções de leitura em `declaracoes_dia.py` faziam `except Exception: return 0` sem log; um erro de banco virava "0 horas" e disparava a mensagem enganosa "Não existe tempo monitorado disponível".
- **Solução aplicada:** adicionado `logger = logging.getLogger("cronometro.declaracoes")` e `logger.warning(..., exc_info=True)` em `obter_segundos_monitorados_do_dia`, `obter_segundos_cronometrados_atividade`, `obter_abatimento_total_atividade` e `obter_segundos_declarados_desbloqueados`. Mantido o retorno 0 (resiliência da UI, pois `obter_resumo_do_dia` consome essas funções), mas o erro deixou de ser invisível.

#### 5. 🟡 Médio (5-6) — Tempo OCIOSO acumulava sem o teto de 30h aplicado ao trabalhado — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** o cap `LIMITE_HORAS_MAXIMO` (30h) era aplicado só ao ramo `trabalhando`; o `ocioso` somava sem limite, distorcendo "Cronometradas" em sessões esquecidas.
- **Solução aplicada:** em `app/monitor.py::_acumular_tempo_ate_agora_locked`, o ramo `ocioso` passou a aplicar o mesmo `min(..., LIMITE_HORAS_MAXIMO)` do `trabalhando` (teto simétrico).
- **Decisão do usuário (2026-06-02):** o teto de 30h é **intencional** (proteção anti-runaway) e fica simétrico. Isso torna o **#15 (pendente) um won't-fix por ora** — ver nota no #15.

#### 13. 🟡 Médio (5-6) — Declarar/editar hora pelo PAINEL (Gestão) ignorava horas com `referencia_data NULL` (teto menor que o desktop) — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** `editar.php` somava `cronometro_relatorios.segundos_trabalhando WHERE referencia_data IS NOT NULL`, excluindo linhas legadas com `referencia_data NULL`. O desktop (fonte da verdade, `obter_segundos_monitorados_do_dia`) conta **todas** as linhas. Em bases com linhas NULL, o teto do painel ficava menor que o do desktop e podia bloquear a declaração de horas reais.
- **Verificação antes de corrigir:** o defeito de código existia, mas estava **dormente** — `SELECT COUNT(*) ... WHERE referencia_data IS NULL` retornou **0** em produção (222 linhas no total, 0 NULL). Sem impacto ativo hoje, mas a divergência de código permanecia.
- **Solução aplicada:** removido o filtro `AND referencia_data IS NOT NULL` da query de `$trabalhado_total` em `painel/commands/atividades_subtarefas/editar.php` — agora soma todas as linhas do usuário, alinhado ao desktop. Comentário explicativo adicionado. `php -l` OK. Com 0 linhas NULL, sem mudança de comportamento em produção; correção é defensiva (impede o bug de ativar se linhas NULL voltarem).

#### 17. 🟠 Alto (7-8) — Aba "Relatório de Tempo Trabalhado" mostrava "Trabalhado = 00:00:00" para todos (lia de tabela legada vazia) — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** o relatório somava horas trabalhadas de `registros_tempo`, tabela **legada e vazia** (o desktop nunca grava nela — grava em `cronometro_relatorios`). Resultado: a coluna "Trabalhado" aparecia zerada para todo mundo e o selo de divergência anti-fraude (declarado > trabalhado +10%) **nunca disparava**, pois depende de `trabalhado > 0`.
- **ONDE estava:** `painel/commands/relatorio/tempo_trabalhado.php:135-143` (query da seção 2) + consumo em `painel/js/aba-relatorio.js`.
- **Solução aplicada:** query da seção 2 trocada para `cronometro_relatorios` (`SUM(segundos_trabalhando)`), a fonte real usada por `listar.php`/`graficos.php`/`editar.php`. Agrupamento/filtro por `COALESCE(referencia_data, DATE(criado_em))` (mesmo critério do `graficos.php`) para não perder linhas com data nula. Removido o bloco de detecção da coluna `id_pagamento` (não existe em `cronometro_relatorios`). Estrutura de saída (`$mapa_trab`/`$trab_por_usuario`) preservada — frontend inalterado. `php -l` OK.

#### 18. 🟡 Médio (5) — Declaração legítima recusada no início da sessão (tempo trabalhado da sessão ficava congelado na abertura da janela) — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** ao abrir "Declarar Tarefa", o tempo trabalhado da sessão era capturado **uma vez** (`JanelaSubtarefas.__init__`) e nunca atualizado. Se o usuário trabalhasse poucos minutos antes do 1º salvamento automático (5min) e tentasse declarar, sem histórico anterior, o sistema recusava com "Não existe tempo monitorado disponível no cronômetro".
- **ONDE estava:** `app/subtarefas.py` (`self._segundos_trabalhando` capturado só no `__init__`, usado nos 3 fluxos de declaração).
- **Solução aplicada:** corrigido em conjunto com o #20. A janela agora recebe o `monitor` e, antes de validar/calcular saldo, chama `_sincronizar_e_obter_adicional()` (em background) → faz flush da sessão atual no banco e lê o valor fresco dali. O snapshot estático virou apenas fallback (sem monitor, ex.: testes). Cobre os 3 fluxos (`_recarregar_dados`, form legado, form MEGA). `py_compile` OK.

#### 19. 🟡 Médio (5-6) — Fechar app / logout / auto-update estando OCIOSO não consolidava a sessão — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** `pausar_e_preservar_sessao()` só chamava `pausar()`, que tem early-return quando a situação é "ocioso". Ao fechar/sair/atualizar com o PC ocioso (>5min parado), não gravava o parcial no banco, não fechava foco/apps e não atualizava o status — o painel podia ficar com status preso e os parciais defasados (no auto-update vem `sys.exit(0)` logo depois).
- **ONDE estava:** `app/monitor.py::pausar_e_preservar_sessao` (chamado por `app_shell.py` no fechar/logout/auto-update) + early-return em `pausar()` (`monitor.py:1129-1130`).
- **Solução aplicada:** `pausar_e_preservar_sessao()` agora, **após** o `pausar()`, força persistência idempotente: `_upsert_relatorio_parcial()` (consolida tempo no banco) + sob lock `_salvar_estado_local_locked()` + `_atualizar_status_atual_locked()`. Funciona mesmo no caminho ocioso. O early-return de `pausar()` foi mantido (ele protege o uso normal). `py_compile` OK.

#### 20. 🟠 Alto (7) — Tempo da sessão atual era contado EM DOBRO na validação da declaração (liberava mais horas que o real) — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** `_validar_tempo_contra_monitoramento` somava o total do banco (`obter_segundos_monitorados_do_dia`, que já inclui o parcial flushado da sessão atual a cada 5min) **e ainda somava por cima** o total cheio da sessão atual (`segundos_monitorados_adicionais`). Quanto mais longa a sessão antes de declarar, mais "tempo fantasma" liberado → dava pra declarar mais horas do que o trabalhado. Mecanismo distinto do #1 (lá era abatimento não-subtraído no painel).
- **ONDE estava:** `declaracoes_dia.py:730-731` + `app/subtarefas.py` passando `self._segundos_trabalhando` como adicional.
- **Solução aplicada:** banco virou a **fonte autoritativa**. Novo método `MonitorDeUso.sincronizar_relatorio_parcial()` (wrapper do flush). A janela chama `_sincronizar_e_obter_adicional()` antes de validar: faz o flush (banco fica completo e fresco) e passa `segundos_monitorados_adicionais=0` — sem dupla contagem. Mesmo helper resolve o #18. `declaracoes_dia.py` **não** foi alterado (o `+= adicional` continua válido; agora recebe 0). `py_compile` OK; 79/82 testes passando (as 3 falhas são pré-existentes, de texto de mensagem em `declaracoes_dia.py`, não tocado).

#### 21. 🟠 Alto (7-8) — Tempo de foco por janela quase nunca era contado (truncava a cada 0,2s) — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** `_acumular_foco_locked` fazia `self._segundos_em_foco_atual += int(delta)`. Como o loop roda a cada ~0,2s, `int(0.2) == 0` e o tempo de foco era descartado tick a tick (só contava se o loop atrasasse ≥1s). `cronometro_foco_janela.segundos_em_foco` ficava ~0; gráficos de foco/timeline individual mostravam quase nada (e o saneamento de registros pós-crash fechava com duração ~zero). **Não afeta pagamento** (que usa só `segundos_trabalhando`). Bug distinto do #8 (lá é race condition por rodar fora do lock; aqui é o truncamento do delta).
- **ONDE estava:** `app/monitor.py:682` (`+= int(delta)`).
- **Solução aplicada:** `_segundos_em_foco_atual` passou a ser **float** (init/resets `0.0`) e o acúmulo agora é `+= delta` (preserva a fração; carry entre ticks). As gravações no banco já faziam `int(...)`, então só convertem no momento certo. `py_compile` OK.

#### 22. 🟡 Médio (4-5) — Risco de linha DUPLICADA em `cronometro_relatorios` (race no upsert sem chave única) — CORRIGIDO 2026-06-02 (Claude 1)

- **Era:** `_upsert_relatorio_com_snapshots` faz `SELECT id_relatorio WHERE id_sessao AND referencia_data` → se não acha, `INSERT` (sem UNIQUE KEY, por decisão de não alterar o banco). Dois upserts concorrentes para o mesmo `(id_sessao, dia)` podiam ambos "não achar" e inserir → **linha duplicada**, que **dobraria as horas daquele dia** em TODAS as somas (teto de declaração, `listar.php`, gráficos, relatório). Race pré-existente (loop a cada 5min vs `pausar`/`zerar`/`finalizar`), **amplificada** ao adicionar flush sob demanda em cada declaração/reload/fechamento (correções #18/#19/#20).
- **ONDE estava:** `app/monitor.py::_upsert_relatorio_com_snapshots` (SELECT-then-INSERT por dia).
- **Solução aplicada:** novo lock dedicado `self._trava_upsert_relatorio` (separado de `self._trava` para não bloquear o loop principal). O corpo do worker é serializado com `acquire()` antes do `try` + `release()` no `finally` — assim o check-and-write nunca roda concorrente: o 2º chamador encontra a linha já criada e faz UPDATE em vez de INSERT. Sem alteração de banco. `py_compile` OK; 79/82 testes passando (3 falhas pré-existentes em `declaracoes_dia.py`, não tocado).

#### 26. 🟡 Médio (6, sobe para Alto se houver trabalho não pago) — Concluir tarefa no dia de um pagamento ANTIGO (havendo um pagamento mais novo) travava-a como "já paga" → trabalhador nunca recebia por ela — CORRIGIDO 2026-06-02 (Claude 1)

> _(catalogado originalmente como "#17 da 2ª passada"; renumerado para #26 por colisão — ver nota de reconciliação na seção Pendente.)_

- **Era:** em `concluir_subtarefa`, ao decidir se a tarefa recém-concluída deveria ser marcada como `bloqueada_pagamento` (já paga), comparava a criação da tarefa contra o `criado_em` do pagamento **mais recente** do usuário (`obter_datetime_ultimo_pagamento`), e não contra o pagamento que **efetivamente trava** aquela data (o mais antigo que cobre a referência, retornado por `_obter_pagamento_que_trava_data`). Com 2+ pagamentos, tarefas criadas/declaradas **entre** um pagamento antigo e um novo eram marcadas como pagas pelo antigo (que não as cobriu) → excluídas dos pagamentos futuros → trabalho real nunca pago.
- **ONDE estava:** `declaracoes_dia.py` (`concluir_subtarefa`, bloco de marcação `bloqueada_pagamento`) + helper `_obter_pagamento_que_trava_data` (não retornava `criado_em`).
- **Solução aplicada:** (1) `_obter_pagamento_que_trava_data` passou a selecionar também `p.criado_em`. (2) `concluir_subtarefa` agora usa `dt_pagamento = pagamento.get("criado_em")` (o pagamento que trava), com parsing robusto str→`datetime` (fallback `None`), em vez de `obter_datetime_ultimo_pagamento`. Assim `marcar = criada_em <= dt_pagamento` compara contra o pagamento correto: tarefas criadas depois do pagamento que trava **não** são mais marcadas como pagas por ele. O outro uso do helper (linha ~481) só lê `id_pagamento` — coluna extra é aditiva, sem efeito colateral. `py_compile`/`ast.parse` OK.

#### 27. 🟢 Baixo (2) — Endpoint `status/horas_mes.php` lia horas do mês de tabela legada vazia (retornava sempre 00:00) — CORRIGIDO 2026-06-02 (Claude 1)

> _(catalogado originalmente como "#18 da 2ª passada"; renumerado para #27 por colisão — ver nota de reconciliação na seção Pendente.)_

- **Era:** `horas_mes.php` somava `registros_tempo.segundos` por `situacao` — `registros_tempo` é tabela **legada e vazia** (o desktop grava em `cronometro_relatorios`), então retornaria 00:00 pra qualquer mês. Endpoint estava **órfão** (sem consumidor), mas o defeito ficaria latente para qualquer reuso. Mesmo problema-raiz do #17 (relatório).
- **ONDE estava:** `painel/commands/status/horas_mes.php` (query lia de `registros_tempo`).
- **Solução aplicada:** query trocada para `cronometro_relatorios` somando `segundos_trabalhando`/`segundos_ocioso`/`segundos_pausado`, com o mês derivado de `DATE_FORMAT(COALESCE(referencia_data, DATE(criado_em)), '%Y-%m')` (mesmo critério de `tempo_trabalhado.php`/`graficos.php`). Removida a detecção da coluna `id_pagamento` (inexistente em `cronometro_relatorios`); o filtro "excluir horas pagas" não se aplica — retorno é o cronometrado do mês. Formato da resposta (`segundos: {trabalhando, ocioso, pausado}`) preservado. `php -l` OK + validado contra o banco (maio/2026 ≈ 205h trabalhando, antes 0).

---

