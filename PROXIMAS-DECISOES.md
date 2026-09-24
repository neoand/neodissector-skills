# Próximas Decisões — Neodissector Skills

Esta lista é gerenciada por Anderson. Cada item tem:
- **Status**: proposto | aceito | em-andamento | concluído | cancelado
- **Prioridade**: P0 (crítico) | P1 (alto) | P2 (médio) | P3 (baixo)
- **Estimativa**: rough effort

---

## ✅ 1.0.0 — Lançamento inicial

- **Status**: concluído
- **Data**: 2026-09-24
- **Escopo**: 22 skills + 3 scripts + 5 docs + install.py
- **Detalhes**: ver `CHANGELOG.md`

---

## 🚧 1.1.0 — Próxima sprint (target: 2026-Q4)

### Adicionar `bug_init.py` ao neodissector-bug

- **Status**: proposto
- **Prioridade**: P2
- **Estimativa**: 4h
- **Motivação**: o `neodissector-bug` SKILL.md documenta o schema completo e os 4 modos, mas falta CLI helper para criar `bug.md` com frontmatter válido a partir de um comando.
- **Saída esperada**: `~/.agents/skills/neodissector-bug/resources/scripts/bug_init.py "..."` cria `dissects/<s>/bugs/BUG-YYYYMMDD-XXXX/bug.md` com frontmatter canônico.

### Adicionar `migration_init.py` ao neodissector-migration

- **Status**: proposto
- **Prioridade**: P2
- **Estimativa**: 4h
- **Motivação**: análogo ao bug_init.
- **Saída esperada**: scaffold de `migration/{paradigm_decision.md,curator_decisions.md,strategy.md,target_*.md,parity_specs.md,parity_tests/}` a partir de `extract/components.md`.

### Adicionar testes para `verify-invocation.py` e `legacy_policy.py`

- **Status**: proposto
- **Prioridade**: P1
- **Estimativa**: 8h
- **Motivação**: gates hoje são "testados manualmente". Versão 1.1 deve ter CI com `pytest`/`unittest` que rode em todo PR.
- **Saída esperada**: `tests/test_verify_invocation.py`, `tests/test_legacy_policy.py`, GitHub Actions workflow.

### Hook OpenCode/Claude Code para `legacy_policy`

- **Status**: proposto
- **Prioridade**: P2
- **Estimativa**: 6h
- **Motivação**: o `legacy_policy.py` é gate lógico. Hoje, quem chama `Write`/`Edit` tool é o LLM agent, que pode ignorar. Um `PreToolUse` hook engine-side força a checagem antes da escrita.
- **Saída esperada**: `hooks/pre-tool-use.py` configurável + docs de integração com OpenCode/Claude Code.

### Bump descrição de `system-dissector` com exemplos de uso

- **Status**: proposto
- **Prioridade**: P3
- **Estimativa**: 1h
- **Motivação**: descrição atual é densa mas sem exemplos. Adicionar 2-3 exemplos curtos "Use quando você quer: <X>".

---

## 💭 Backlog (sem data)

- **Multi-repo install**: um projeto pode usar skills de múltiplos sources (ex: neodissector + skills customizadas do time).
- **Skill registry**: API simples para listar skills disponíveis no ecossistema.
- **Migration mode para o `state.json`**: ler `state.json` de dissecações antigas e propor migração para novo schema.
- **Documentação como hub navegável**: mkdocs.yml + GitHub Pages (rejeitado em 2026-09-24 por custo; reavaliar).
- **Visualização Code City 3D**: rejeitada em 2026-09-24; reavaliar se houver demanda.
- **Integração com WA-CLI/Kimi/AGY**: hoje `install.py` é Git-only. Adicionar suporte para baixar de outros fontes.