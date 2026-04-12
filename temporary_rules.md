# Regras Temporárias do Projeto

Este arquivo contém regras específicas e temporárias que se aplicam apenas ao projeto atual.
Diferente do `RULES.md` (regras globais e permanentes), as regras aqui podem ser adicionadas, alteradas ou removidas conforme a necessidade do momento.

---

## Regras ativas

1. **Nunca subir o arquivo `conexao.php` ao comitar e versionar no GitHub.**
   - O arquivo `painel/commands/conexao/conexao.php` contém credenciais de banco de dados.
   - Deve ser mantido no `.gitignore` e nunca incluído em commits.
