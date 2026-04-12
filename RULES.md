# Agentes e Skills disponíveis

Este projeto contém um toolkit de agentes especialistas em `agents/`.
Leia os arquivos abaixo **somente quando o contexto da tarefa exigir** — não os carregue por padrão.

## Regras globais (leia sempre que relevante)

- `agents/deploy.md` — segurança: nunca commitar credenciais, API keys ou secrets
- `agents/aviso.md` + `agents/tokens.md` — ao finalizar uma tarefa, executar `agents/aviso.py <tokens>`

## Agentes disponíveis (leia só quando for usar aquele especialista)

| Quando a tarefa envolver | Leia |
|---|---|
| UI, componentes, React, Next.js, CSS, Tailwind | `agents/fullstack/frontend-specialist.md` |
| API, backend, Node.js, lógica de negócio | `agents/fullstack/backend-specialist.md` |
| Banco de dados, schema, SQL, Prisma | `agents/fullstack/database-architect.md` |
| App mobile (iOS, Android, React Native) | `agents/Mobile/mobile-developer.md` |
| Criar um projeto do zero (scaffolding) | `agents/fullstack/app-builder/SKILL.md` |
| Design UI/UX, cores, tipografia, animações | `agents/fullstack/frontend-design/SKILL.md` |
| Código legado, refatoração | `agents/fullstack/code-archaeologist.md` |
| Documentação | `agents/fullstack/documentation-writer.md` |
| Arquitetura geral do toolkit | `agents/ARCHITECTURE.md` |

> Carregar um agente = ler o arquivo dele + os arquivos que ele referenciar internamente, conforme necessário.

# Comportamento de cada agente de IA

Se você for o Codex da OpenAI ou Antigravity, faça o seguinte:

- Seu objetivo aqui é apenas ler o projeto e atualizar o arquivo `!executar.md`.
- É proibido modificar arquivos do programa.
- Toda vez que for alterar o arquivo `!executar.md` ou o arquivo `!projeto.md`, adicione na primeira linha o comentário `AGUARDE ALTERANDO` para o outro agente saber que você está mexendo nele.
- Ao terminar a alteração, apague a informação `AGUARDE ALTERANDO`.

Se você for o Claude, faça o seguinte:

- Leia o arquivo `!executar.md`.
- Se houver alguma alteração pendente ou não concluída, execute o que estiver descrito lá.
- Todo arquivo que estiver atualizando deve receber na primeira linha o comentário `AGUARDE ALTERANDO` para o outro agente saber que ele está sendo alterado.
- Ao finalizar, apague o comentário `AGUARDE ALTERANDO` para o outro agente saber que foi concluído.

## Regra de ouro — Banco de dados

- **Nenhuma IA pode alterar o banco de dados (CREATE, ALTER, DROP, INSERT, UPDATE, DELETE) sem permissão explícita do usuário.**
- Isso inclui migrações, seeds, alterações de schema, correções de dados e qualquer operação destrutiva ou construtiva.
- A IA deve descrever a alteração proposta e aguardar confirmação antes de executar.

---

## Pasta debug/ — Depuração isolada de bugs complexos

A pasta `debug/` serve para isolar e reproduzir bugs sem rodar o pipeline completo.

### Como funciona
- `debug.py` — na raiz do projeto, script executável que testa a funcionalidade com bug em isolamento.
- `debug/` — pasta com os arquivos de teste necessários (vídeos, áudios simulados, etc).
- O script gera automaticamente os arquivos de teste (beeps, vídeos de barras) dentro de `debug/` quando necessário.

### Quando usar
- Quando um bug envolve interação com o Premiere e precisa de testes iterativos rápidos.
- Quando o bug é complexo demais para depurar rodando o pipeline inteiro (transcrição, TTS, revisão...).
- Quando o usuário pedir para usar, ou quando o agente achar necessário.

### Fluxo de uso
1. Adaptar `debug/debug.py` para reproduzir o cenário do bug.
2. Colocar na pasta os arquivos de teste necessários (ou gerar via ffmpeg).
3. Executar `python debug/debug.py` com o Premiere aberto.
4. Observar o resultado na timeline e comparar com o esperado.
5. Corrigir o código, rodar debug.py de novo até o bug sumir.
6. Só depois testar com o pipeline real.
