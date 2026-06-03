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

> **Bugs #1–#5 (varredura Claude 1 — horas + pagamentos) → CORRIGIDOS em 2026-06-02.** Movidos para a seção **Concluído** no fim deste arquivo (mantidos os números originais).
>
> Os itens **#6–#16** abaixo (de outras varreduras) seguem **PENDENTES** de correção. Observação: #1 e #4 haviam sido corroborados de forma independente por outra varredura (mesmo arquivo/linha).

---

#### 6. 🟠 Alto (7-8) — Total "A pagar" do Dashboard fica MENOR que a soma real quando um membro foi pago a mais

- **QUANDO ACONTECE:** no Dashboard ("Tempo declarado"), quando pelo menos um membro recebeu pagamento MAIOR que o estimado dele (adiantamento, acerto, bônus). O "A pagar" total no topo aparece menor que a soma dos "A pagar" dos cards de cada membro.
- **ONDE:** `painel/js/aba-graficos.js:1693` (total geral) vs `:1730` (card por membro).
- **SEVERIDADE:** 🟠 Alto 7-8 (dinheiro exibido errado; pode levar a pagar a menos quem ainda tem horas devidas).
- **IMPACTO:** o "excesso" pago a um membro abate indevidamente a dívida com os outros. O admin lê um total a pagar abaixo do real.
- **DETALHE TÉCNICO:** o backend (`relatorio/tempo_trabalhado.php:291`) entrega `valor_pendente = max(0, valor_estimado − total_pago)` clampado **por usuário**, e os cards usam isso. Mas o total geral faz `Math.max(0, total_geral_valor − totalPago)` (l.1693), onde `total_geral_valor` é a soma BRUTA dos `valor_estimado` (sem clamp) e `totalPago` é a soma de TODOS os pagamentos — o clamp por usuário some na agregação. Correto seria somar os `valor_pendente` já clampados. **Confiança: alta (verificado).**

---

#### 7. 🟡 Médio (5-6) — Resumo da Gestão zera "Pago" e "A pagar" quando o membro não tem subtarefa no período

- **QUANDO ACONTECE:** ao abrir a Gestão de um membro e olhar o "Resumo para pagamento". Se naquele filtro (Tudo/30 dias) o membro não tiver nenhuma subtarefa, TODOS os campos (Trabalhado/Declarado/A pagar/Pago) aparecem zerados — mesmo que ele tenha pagamentos lançados e horas de cronômetro. Mais provável no "30 dias".
- **ONDE:** `painel/js/aba-usuarios.js:675` (lê tudo de `subs[0]`) + `painel/commands/atividades_subtarefas/listar.php:225-238` (`total_pago` é anexado por-linha, não como campo de topo).
- **SEVERIDADE:** 🟡 Médio 5-6 (decisão de pagamento com base em valores falsamente zerados).
- **IMPACTO:** o admin pode achar que não há nada pago nem nada a pagar, quando só faltam registros de subtarefa naquele período.
- **DETALHE TÉCNICO:** se `subs.length === 0`, `first = {}` e todo `Number(first.* || 0)` vira 0 — inclusive `total_pago`, que NÃO depende de existir subtarefa. **Confiança: alta (verificado nos dois lados).**

---

#### 8. 🟡 Médio (5-6) — Operações de foco rodam FORA do lock e disputam contadores com pausar/retomar/finalizar

- **QUANDO ACONTECE:** o usuário clica Pausar/Retomar/Finalizar exatamente enquanto o app troca o foco da janela ativa (ou faz flush periódico). É timing entre a thread de fundo e a da interface — acontece sozinho.
- **ONDE:** `app/monitor.py:1549-1567` (loop chama `_fechar_foco`/`_abrir_foco`/`_flush_foco_periodico` sem `with self._trava:`) vs as mesmas chamadas DENTRO do lock em pausar/retomar/zerar/finalizar.
- **SEVERIDADE:** 🟡 Médio 5-6 (corrompe métrica de foco por janela; NÃO afeta o cronômetro principal trab/ocioso/pausado).
- **IMPACTO:** `segundos_em_foco` em `cronometro_foco_janela` pode sair dobrado/zerado/negativo e `_id_foco_aberto` virar stale, sujando os gráficos de foco/timeline individual.
- **DETALHE TÉCNICO:** `_acumular_foco_locked` (nome sugere proteção) é chamado pelo loop SEM o lock, enquanto `pausar()` etc. o chamam COM o lock — como o loop não pega o lock, a exclusão mútua não existe. Viola a regra do projeto ("operações no MonitorDeUso respeitam `with self._trava:`"). **Confiança: alta no lado do loop (verificado); média no impacto exato.**

---

#### 9. 🟡 Médio (5) — Reabrir subtarefa não reverte o abatimento já consumido → saldo do próximo ciclo encolhe

- **QUANDO ACONTECE:** subtarefa concluída e declarada; houve um pagamento que gerou snapshot de abatimento contando aquele saldo; depois o usuário reabre uma subtarefa NÃO bloqueada do mesmo ciclo.
- **ONDE:** `declaracoes_dia.py:1139-1151` (reabrir zera `segundos_gastos`/`concluida`, sem tocar em `pagamento_abatimentos`).
- **SEVERIDADE:** 🟡 Médio 5 (cenário de borda; o usuário "perde" horas reais no saldo futuro).
- **IMPACTO:** o `declarado` cai mas o `abatido` (snapshot imutável) permanece, então o saldo disponível para o próximo ciclo diminui indevidamente.
- **DETALHE TÉCNICO:** `reabrir_subtarefa` só é barrado por `subtarefa_esta_travada` (bloqueada_pagamento=1); subtarefas concluídas mas ainda desbloqueadas passam, desbalanceando `monitorado − declarado − abatido`. **Confiança: média** (exige sequência específica).

---

#### 10. 🟡 Médio (5) — "Declarado não-pago" do Resumo ignora filtro de período e de conclusão

- **QUANDO ACONTECE:** no Resumo/edição da Gestão em modo "30 dias" — o total declarado calculado pela via "não-pago" mistura subtarefas de TODA a história (e até abertas), enquanto cronometrado/ocioso/pago respeitam os 30 dias.
- **ONDE:** `painel/commands/atividades_subtarefas/listar.php:206-212` (`mapaDeclNaoPago` sem `{$filtroResumoRef}` e sem `concluida = 1`), vira `segundos_declarados_total` (l.233).
- **SEVERIDADE:** 🟡 Médio 5 (números de períodos diferentes lado a lado; o Resumo principal usa o campo `_geral`, que está correto).
- **IMPACTO:** onde esse campo é exibido (compatibilidade do modal de edição), "declarado" pode aparecer maior que o esperado para o período.
- **DETALHE TÉCNICO:** `mapaCron` (l.186) e `mapaDecl` (l.200) concatenam `{$filtroResumoRef}`; `mapaDeclNaoPago` (l.206-210) não, e também não filtra `concluida = 1`. **Confiança: alta no código; média no impacto visível** (depende de qual UI consome o campo).

---

#### 11. 🟡 Médio (5) — `finalizar()` lê os segundos do relatório final FORA do lock

- **QUANDO ACONTECE:** ao clicar Finalizar e gravar o relatório da sessão — o snapshot de segundos trabalhados que vai pra `cronometro_relatorios` é lido sem proteção de lock.
- **ONDE:** `app/monitor.py:1428-1433` (lê `_segundos_*_float` após o `with self._trava:` já ter fechado).
- **SEVERIDADE:** 🟡 Médio 5 (mitigado por `_rodando=False`, mas tecnicamente sem barreira).
- **IMPACTO:** se o loop acumular tempo entre o fim do lock e a leitura, o total persistido pode divergir do snapshot. `zerar_sessao()` faz o correto (captura dentro do lock); `finalizar()` não.
- **DETALHE TÉCNICO:** `_parar.set()` só ocorre no bloco seguinte (l.1437-1440), depois da leitura na l.1431. **Confiança: média.**

---

#### 12. 🟢 Baixo (4) — `listar_por_usuario.php` vaza mensagem de erro interna do banco

- **QUANDO ACONTECE:** em qualquer falha de SQL/conexão ao listar pagamentos de um usuário.
- **ONDE:** `painel/commands/pagamentos/listar_por_usuario.php:66`.
- **SEVERIDADE:** 🟢 Baixo 4 (vazamento de info; não mexe em dados/dinheiro).
- **IMPACTO:** expõe estrutura interna/SQL no JSON mesmo em produção, ao contrário dos outros endpoints de pagamento.
- **DETALHE TÉCNICO:** devolve `$e->getMessage()` cru, sem o guard `debug_ativo()` que `criar.php`/`editar.php`/`excluir.php` usam. **Confiança: alta (verificado).**

---

> **Varredura Claude 1 (2026-06-02) — foco: "usuário trabalha e as horas não contam / declaração fica zerada".** Achados NOVOS abaixo (#13-#16), não cobertos por #1-#12 nem pelo `!executar.md`.

---

#### 13. 🟡 Médio (5-6) — Declarar/editar hora pelo PAINEL (Gestão) pode ignorar parte das horas trabalhadas e bloquear a declaração

- **QUANDO ACONTECE:** ao declarar/editar o tempo de uma tarefa **pelo painel web (aba Gestão)** de um usuário que tem horas trabalhadas registradas em formato "antigo". O painel calcula um teto de horas menor do que o real e recusa com "Só tem Xh disponível…", mesmo o usuário tendo trabalhado mais. Pelo **app desktop** a mesma declaração passa normalmente — os dois lados discordam.
- **ONDE:** `painel/commands/atividades_subtarefas/editar.php:109-115` (filtro `referencia_data IS NOT NULL`) vs desktop `declaracoes_dia.py:582-609` (`obter_segundos_monitorados_do_dia` conta também linhas com `referencia_data IS NULL`).
- **SEVERIDADE:** 🟡 Médio 5-6 (bloqueio de declaração de horas reais; sem perda de dados, mas impede concluir a ação pelo painel).
- **IMPACTO:** horas trabalhadas que ficaram gravadas sem a "data de referência" preenchida (registros legados / anteriores ao refator) **somem do teto** quando a declaração é feita pelo painel, mas continuam contando no desktop. O admin vê "saldo disponível" menor que o real e não consegue lançar o tempo.
- **DETALHE TÉCNICO:** a query do painel soma `cronometro_relatorios.segundos_trabalhando WHERE referencia_data IS NOT NULL` — exclui linhas com `referencia_data NULL`. O desktop, na validação anti-fraude (`_validar_tempo_contra_monitoramento` → `obter_segundos_monitorados_do_dia(user_id, None, 0)`), **não** aplica esse filtro e ainda trata explicitamente o ramo `referencia_data IS NULL` (linhas 600-604), o que indica que essas linhas existem/existiram na base. Resultado: teto do painel ≤ teto do desktop. **Confiança: alta no código (verificado nos dois lados); o impacto real depende de existirem linhas com `referencia_data NULL` na base — vale conferir com `SELECT COUNT(*) FROM cronometro_relatorios WHERE referencia_data IS NULL`.**

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

### Concluído:

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

---

