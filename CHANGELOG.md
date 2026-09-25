# Changelog — Neodissector Skills

Todas as mudanças notáveis neste repo são documentadas aqui. O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e este projeto segue [Semantic Versioning](https://semver.org/lang/pt-BR/).

## [1.3.0] — 2026-09-25

### Adicionado

- `skills/playwright-re/SKILL.md` — nova skill companion para automação browser (Playwright + Chromium).
- `skills/playwright-re/resources/scripts/discover-api.py` — descoberta automática de OpenAPI/Swagger/GraphQL em URLs canônicas. Tenta 17 caminhos.
- `skills/playwright-re/resources/scripts/capture-network.py` — captura HAR completo + console logs via Playwright.
- `skills/playwright-re/resources/scripts/crawl-spa.py` — crawler para SPAs (React/Angular/Vue) com screenshots.
- `skills/playwright-re/resources/references/playwright-recipes.md` — 7 padrões prontos.
- `skills/system-dissector/resources/scripts/prompts/triage-ui-only.md` — **NOVO 6º sub-agent prompt** (`triage-ui-only`) com workflow guiado 4-1-3:
  - 4 fontes de informação (A=API doc, B=site docs, C=demo, D=Playwright)
  - Usuário escolhe combinação
  - Uma opção por vez (sem wall-of-text)
  - Outputs padronizados em `evidence/`
- Adicionado `ui` como novo `VALID_TIPOS` em `dissect_utils.py`.

### Cenário target

Sistemas SaaS /proprietários SEM código-fonte nem binário (só UI + API pública).
Antes: usava-se `triage-protocol` (Wireshark puro) ou fall-back para análise manual.
Agora: workflow guiado completo + Playwright + Chromium + auto-discovery de API.

### Pipeline exemplo

```bash
# 1. Sub-agent invoca o workflow guiado
# 2. Usuário responde com credenciais ou URL canônica
# 3. Auto-discovery encontra API
python3 ~/.agents/skills/playwright-re/resources/scripts/discover-api.py \
  --base-url https://app.vendor.com --output-dir evidence/api-spec
# 4. Login + HAR capture
python3 ~/.agents/skills/playwright-re/resources/scripts/capture-network.py \
  --url https://app.vendor.com/login --username demo@vendor.com --password demo123
# 5. SPA crawl
python3 ~/.agents/skills/playwright-re/resources/scripts/crawl-spa.py \
  --base-url https://app.vendor.com --max-depth 3 --output-dir evidence/web
# 6. Phase 2-5 seguem normalmente com surface data
# 7. Sanitize → consumer-package → verify-no-verbatim gate
```

### Compatibilidade

100% compatível com v1.2.0. Skills existentes (23) inalteradas. Apenas adição.

## [1.2.0] — 2026-09-25

### Adicionado

- `skills/neodissector-sanitizer/SKILL.md` — nova skill para gerar pacote clean-room a partir de dissects.
- `skills/neodissector-sanitizer/resources/scripts/sanitize.py` — CLI que transforma `dissects/<s>/` (verbatim interno) em `<consumer-package>/` (sanitizado para DEV).
- `skills/neodissector-sanitizer/resources/scripts/verify-no-verbatim.py` — gate CI que assert zero verbatim no pacote.
- `skills/neodissector-sanitizer/resources/references/sanitization-rules.md` — catálogo das 7 categorias de regras.

### Transformações validadas (closed-erp-patterns-2026 — target ERP-A 19.0)

Sanitizou 1743 arquivos internos em 940 arquivos de pacote:
- 1.419 paths verbatim → descrições conceituais
- 326 function signatures → "Função que <verbo> (parâmetros: ...)"
- 16 class names → "# <kind> do módulo"
- 696 vendor refs (vendor-A) → "[vendor-marker-redacted]"
- 4 hosts internos → "[host-redacted]"
- TOTAL: 2.461 transformações. Pacote LIMPO (verify-no-verbatim.py exit 0).

### Motivação

Anderson 2026-09-25: "tudo é ouro" no dissecação, mas a entrega ao DEV tem que
ser desnaturalizada. O DEV reproduz fielmente SEM saber COMO nem DE ONDE vem.
A meta final = produto Odoo 19 próprio, em produção, livre de licenciamento enterprise.

### Compatibilidade

100% compatível com v1.1.1. Skills existentes (22) inalteradas. Apenas adição.

## [1.1.1] — 2026-09-24

### Corrigido

- install.py: erro "VERSION is not a directory" em sparse-checkout. Substituído por clone raso (mais robusto, repo é pequeno ~5MB).

## [1.1.0] — 2026-09-24

### Adicionado

- `skills/neodissector-bug/resources/scripts/bug_init.py` — CLI helper que cria `dissects/<contexto>/bugs/<BUG-YYYYMMDD-XXXX>/bug.md` com frontmatter canônico + skeleton completo (10 seções). Suporta `--list` para listar bugs.
- `skills/neodissector-migration/resources/scripts/migration_init.py` — CLI helper que scaffold os 8 arquivos do Time de Migração (paradigm_decision.md, curator_decisions.md, strategy.md, target_*.md, parity_specs.md, parity_tests/) sob `dissects/<contexto>/migration/`.

### Compatibilidade

- 100% compatível com v1.0.0. Sem breaking changes.
- Skills existentes (22) inalteradas.

### Motivação

Itens 1 e 2 do backlog `PROXIMAS-DECISOES.md` (estimativa original: 4h + 4h = 8h). Entregues como parte da continuação do hardening 2026-09-24.

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