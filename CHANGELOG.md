# Changelog — Neodissector Skills

Todas as mudanças notáveis neste repo são documentadas aqui. O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e este projeto segue [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.0.0] — 2026-09-24

### Adicionado

- 22 skills no escopo do neodissector:
  - **Core (1)**: `system-dissector`
  - **RE adjacentes (15)**: `reverse-engineer`, `binary-ninja`, `binary-analysis-patterns`, `protocol-reverse-engineering`, `malware-analyst`, `firmware-analyst`, `memory-forensics`, `dwarf-expert`, `anti-reversing-techniques`, `ai-assisted-re`, `mobile-re`, `variant-analysis`, `audit-context-building`, `wiki-researcher`, `neodoo-integrate`
  - **Companion (6)**: `neodissector-reconstructor`, `neodissector-brainstorm`, `neodissector-bug`, `neodissector-migration`, `neodissector-refactor`, `neodissector-pricing`
- 3 scripts Python compartilhados:
  - `scripts/verify-invocation.py` — gate de CI para o eixo model/user-invoked (8 regras, R1-R8)
  - `scripts/legacy_policy.py` — gate de permissão de escrita no projeto alvo
  - `scripts/session.py` — gerenciador de sessões de brainstorm
- 5 docs canônicos:
  - `docs/INVOCATION-POLICY.md` — política de invocação (user vs model)
  - `docs/NEODISSECTOR-CONFIG.md` — schema do `.neodissector/config.json`
  - `docs/neodissector.config.json.example` — template de config
  - `docs/references/bug-schema.md` — schema YAML do bug tracking
  - `docs/references/market-benchmarks.md` — tabela de benchmarks de preço
- `install.py` — CLI para baixar e instalar versão em `~/.agents/skills/`
- `verify-invocation.py` validado: **22/22 skills aprovadas, 0 violações**
- Hardening aplicado em todas as 22 skills: `disable-model-invocation` explícito (model-invoked=system-dissector, user-invoked=21 demais)

### Economia

- Contexto permanente: ~7.000 chars (antes) → **~374 chars (depois)**
- Tokens permanentes: ~1.750 → **~94**
- **−94% tokens** economizados por requisição

### Compatibilidade

- Workflow agnóstico de stack (Phase 5 refactor de 2026-09-22 mantido)
- `neodoo-integrate` continua opt-in para um stack específico do Anderson (NeoAI/NeoAISystems)
- Companion skills (`neodissector-*`) agnósticas por padrão

### Inspiração

- `sandeco/reversa` (paper ArXiv, MIT, framework npm-installable) — patterns chupados, scripts Python próprios
- Hindsight pilot (2026-09-22) — caso real que validou a arquitetura

[1.0.0]: https://github.com/neoand/neodissector-skills/releases/tag/v1.0.0