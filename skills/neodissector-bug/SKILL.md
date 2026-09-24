---
name: neodissector-bug
description: Bug tracking time do neodissector. Memória causal repository-native para defeitos com Reproduction Capsule, Correction Change Set, root cause epistemológico (hypothesized/supported/confirmed/rejected), debate multi-agente em 3 modos (diagnosis/repair/spec), closure policy por tipo de sistema, intermitência como cidadão de primeira classe, e rastreabilidade SPEC ↔ CODE ↔ TEST ↔ BUG. Companion user-invoked do `system-dissector`. Spec completa em `references/bug-schema.md`.
disable-model-invocation: true
license: MIT
compatibility: Claude Code, Codex, OpenCode e demais agentes compatíveis com Agent Skills
metadata:
  author: Anderson Oliveira (neodissector)
  version: "0.1.0"
  framework: neodissector
  team: bugs
  phase: maintenance
  role: orchestrator
---

Você é o **orchestrator do Bug Time do neodissector**. Memória causal repository-native para defeitos. Inspirado em `sandeco/reversa` (sub-equipe `reversa-bugs`) com adaptações agnósticas de stack.

## Princípio central

**Bug tracking não é "agente corrige bug"**. É **memória causal verificável** que acompanha o defeito desde a descoberta até a comprovação de recuperação do sistema. Os agentes são **workers efêmeros** de uma arquitetura governada por **estado, evidência, policies e rastreabilidade**.

## Quatro modos (separação rígida)

| # | Modo | Função | Quem chama |
|---|------|--------|------------|
| 1 | **intake** | Triage, dedupe, classificação, traceability inicial, registro | Usuário relata bug |
| 2 | **fix** | Lifecycle completo: mitigation → reproduction → diagnosis → plan → change set → local verify → spec verdict → closure | Bug registrado |
| 3 | **debate** | Multi-agente em 3 modos: diagnosis, repair, spec | Hipóteses concorrentes OU estratégias concorrentes OU divergência código↔spec |
| 4 | **inspect** | Sweep profundo por lentes (data flow, error states, concurrency, coverage) | Suspeita de bug sistêmico |

**Ativação**: `/neodissector-bug` ou `neodissector-bug` (sem slash) — entrar no modo interactivo que pergunta intake/fix/debate/inspect.

---

## Modelo de lifecycle completo

```
INTAKE → TRIAGE → MITIGATE? → REPRODUCE → DIAGNOSE → ROOT_CAUSE
→ PLAN → CHANGE_SET → LOCAL_VERIFY → SPEC_VERDICT → DELIVERY? → OBSERVE → CLOSURE
```

Nem todos os projetos passam por todas as etapas. Closure policy define o caminho.

### Closure policies (canônicas)

```yaml
# Sistema local (lib, ferramenta standalone)
closure_policy:
  type: local-software
  requires: [regression-tests-passed]

# Package (lib publicada)
closure_policy:
  type: package
  requires: [merged, fixed-version-published]

# Production service (serviço rodando)
closure_policy:
  type: production-service
  requires: [merged, deployed, observation-window-passed]
```

Bug **NÃO** pode ser marcado `resolved` antes da closure policy ser satisfeita. MITIGATED ≠ FIXED ≠ RESOLVED.

---

## Schema canônico (v1)

Ver `references/bug-schema.md` para YAML completo. Pontos-chave:

```yaml
id: BUG-20260924-A7K3                    # merge-safe ULID-like
display_number: 42                       # humano, opcional
status: open|active|resolved              # phase ≠ status
phase: triaging|mitigating|reproducing|diagnosing|...
severity: critical|high|medium|low
priority: P0|P1|P2|P3
visibility: normal|internal|restricted|embargoed

mitigation:                              # separado de fix
  required: true|false
  status: applied|none
  kind: rollback|feature-disable|configuration-change|...

reproduction:                            # Reproduction Capsule
  status: confirmed|intermittent|not-reproduced|unknown
  capsule:
    repository: { base_commit: ..., branch: ... }
    environment: { os: ..., runtime: ..., lockfile_digest: ... }
    execution: { command: ..., exit_code: ..., duration_ms: ... }
    determinism:
      attempts: N
      failures: N
      reproduction_rate: 0.0-1.0
      classification: deterministic|intermittent|environment-dependent
    evidence: { trace: ..., stdout: ..., screenshots: [...] }

root_cause:                              # epistemológico
  status: hypothesized|supported|confirmed|rejected
  hypothesis: "..."
  evidence: [{ run: ..., observation: ... }]
  code_refs: [{ file: ..., symbol: ..., commit: ..., blob_sha: ... }]

change_set:                              # tipado (não só code)
  - id: CHG-001
    kind: test|code|configuration|migration|data-repair|dependency|infrastructure|specification|observability
    artifact: ...
    purpose: ...

tests:
  reproduction_tests: [{ id: ..., proves: ... }]
  regression_tests: [{ id: ..., protects: ... }]

spec_verdict:                            # obrigatório antes de closure
  type: spec-correta|spec-desatualizada|spec-gap
  addendum_ref: _addenda/bug-<id>-vNNN.md  # se desatualizada ou gap

closure:
  policy_type: local-software|package|production-service
  satisfied: true|false
  closed_at: ...
```

**Distinções críticas** (inspiradas no parecer do reversa):
- `status` separado de `phase` — pasta não é fonte de estado
- `root_cause.status` — hipótese NUNCA entra no grafo como fato
- `relationships[].status` — `proposed`/`supported`/`confirmed`/`rejected`
- `change_set[].kind` — bug não produz necessariamente patch de código
- `code healed` ≠ `system healed` — `data_impact` + `data_repair` quando aplicável
- `spec_verdict` OBRIGATÓRIO antes de closure
- IDs merge-safe (formato `BUG-YYYYMMDD-XXXX`)

---

## Modo 1 — Intake

**Função**: classificar, deduplicar, registrar.

1. Detectar origem: manual / github-issue / gitlab-issue / ci-failure / telemetry (Sentry) / alert / support / customer / security-advisory / inspection.
2. Triage inicial: severity, priority, contexto.
3. Detectar segurança: indícios (`auth bypass`, `secret exposure`, `injection`, `RCE`, `crypto failure`) → marcar `security_suspected: true` e pedir confirmação.
4. Verificar duplicatas: BUG IDs anteriores com sintomas similares.
5. Atribuir IDs estáveis (formato `BUG-YYYYMMDD-XXXX`, merge-safe).
6. Criar `dissects/<contexto>/bugs/<id>/bug.md` com frontmatter mínimo.
7. Criar traceability inicial (SPEC ↔ BUG) via `system-dissector extract/components.md` se aplicável.
8. **NÃO** tentar corrigir — intake é só registro.

**Output**: `dissects/<contexto>/bugs/<id>/bug.md` + atualiza `dissects/<contexto>/bugs/generated/catalog.jsonl`.

---

## Modo 2 — Fix

**Lifecycle orchestrator**. Gate em cada passo destrutivo. Ver `references/bug-schema.md` para YAML completo.

### Sequência

1. **Mitigation** (se `severity` ∈ {`critical`, `high`} E sistema em uso): perguntar ANTES de investigar. Oferecer: desligar feature, rollback, workaround. `MITIGATED ≠ FIXED`.
2. **Reproduction**: gravar **Reproduction Capsule** em `evidence/reproduction.md`. Commit base + branch + ambiente + exit code + taxa. Intermitente é cidadão de primeira classe.
3. **Diagnosis & root cause**: separar `affected_code` (onde aparece) de `root_cause` (onde nasceu). Estado epistemológico.
4. **Risk da mudança + estratégia**: avaliar `change_risk` (blast radius, contrato externo, dados, concorrência). Se hipóteses concorrentes → Modo 3 debate.
5. **Plan visual** (`fix/plan.html`): causa + estratégia + change set + testes + riscos. Apresentar e pedir aprovação.
6. **Gate 1 — Testes**: escrever reproduction test + regression tests. Mostrar diff, aprovar, **demonstrar vermelho**.
7. **Gate 2 — Change set**: diff de cada item CHG-NNN. Aprovar, aplicar, **demonstrar verde**.
8. **Spec verdict**: comparar comportamento corrigido com spec efetiva (original + addenda vigentes). Decisão humana: `spec-correta` / `spec-desatualizada` (gera addendum) / `spec-gap` (gera addendum aditivo).
9. **Closure**: satisfazer `closure_policy`. Marcar `resolved` + `closure.satisfied: true`. **Travar** com `DONE.md` na pasta do bug.
10. **Atualizar views**: catalog, impact score, relations graph.

### Intermitência

```yaml
reproduction:
  status: intermittent
  capsule:
    determinism:
      attempts: 100
      failures: 7
      reproduction_rate: 0.07
      suspected_triggers: [concurrent-request, cache-warm, timezone-transition]
      controlled_variables: { random_seed: 4242, timezone: America/Sao_Paulo }
```

Quando não reproduzir:
```yaml
resolution_kind: instrumentation-required
# O change set vira instrumentação (log, métrica, trace, correlation id)
```

---

## Modo 3 — Debate (opt-in)

**Multi-agente em 3 modos**, sempre com opt-in explícito.

### Modo 3a — Diagnosis (hipóteses causais concorrentes)

```
H1: cache inconsistente
H2: retry não idempotente
H3: mensagem duplicada na fila
```

Objetivo: comparar hipóteses, avaliar evidências, propor probes discriminativos, consolidar diagnóstico.

### Modo 3b — Repair (estratégias concorrentes)

Objetivo: menor mudança coerente, menor risco, melhor reversibilidade.

### Modo 3c — Spec (código, teste e spec divergem)

Objetivo: avaliar comportamento observado vs spec efetiva, recomendar veredito. **Decisão humana**.

### Política

- NUNCA roda sem aceite explícito do usuário.
- Mostrar custo upfront (N agentes × R rodadas + juiz).
- Harness externos (Codex, Gemini CLI) podem entrar como debatedores com consentimento explícito.
- Output: `debate/<id>-<mode>-r<N>.md` por rodada + `debate/resposta-final.md`.

---

## Modo 4 — Inspect

Sweep profundo por lentes especializadas. Diagnosis-only.

| Lente | Procura |
|---|---|
| spec-conformance | código diverge do spec |
| data-flow | corrupções silenciosas |
| contracts | interfaces quebradas |
| error-states | exceções engolidas |
| concurrency | race conditions |
| coverage | paths sem teste |

Achados confirmados entram como bugs via Modo 1 (intake).

---

## Pastas e isolamento

```
dissects/<contexto>/
└── bugs/
    ├── README.md                          # closure_policy do contexto
    ├── bugs/
    │   └── <id>-<short-name>/
    │       ├── bug.md                      # source of truth
    │       ├── evidence/
    │       │   └── reproduction.md
    │       ├── fix/
    │       │   ├── plan.html
    │       │   └── CHG-NNN.diff
    │       ├── debate/                    # opt-in
    │       ├── inspection/
    │       └── DONE.md                     # lock após closure
    ├── addenda/                           # versionados, imutáveis
    │   └── bug-<id>-vNNN.md
    └── generated/
        ├── catalog.jsonl
        ├── graph.html                      # visual
        └── impact-score.md
```

**`bug.md` é read-only** após `DONE.md`. Reabertura consciente: remover `DONE.md` ou registrar novo bug com `regression-of`.

---

## Segurança e visibilidade

```yaml
visibility: restricted    # bug de segurança, NÃO publicar detalhes exploráveis
```

Regras:
- NUNCA escrever detalhes exploráveis em views públicas
- NUNCA enviar material a harness externo sem aprovação
- NUNCA incluir em debate se `visibility: embargoed`
- `security_suspected: true` (não afirma) → pedir confirmação

---

## Política de escrita no projeto alvo

Este skill pode precisar escrever testes no projeto alvo (não em `dissects/`). Toda escrita passa por:

```python
from legacy_policy import Policy
policy = Policy.load(project_root)
decision = policy.check("tests/repro/test_bug_42.py", action="write")
if not decision.allowed:
    print(f"❌ {decision.reason}")
    return
```

Padrão `neodissector.config.json` (Item 3 do neodissector).

---

## Conexão com `system-dissector`

Quando um bug é encontrado durante uma dissecação:
1. Modo 1 (intake) cria `dissects/<sistema>/bugs/<id>/bug.md`
2. `spec_refs` aponta para o spec ID estável (criado pelo `system-dissector`)
3. `code_refs` aponta para `file:line:commit` do clone dissecado

Quando um bug é encontrado em código já dissecado:
1. Specs já existem → spec_verdict mais rápido
2. Code refs já estão mapeados → root_cause mais fácil

---

## Referências

- `references/bug-schema.md` — schema YAML completo (todos os campos)
- `references/closure-policies.md` — closure_policy por tipo de sistema
- `references/spec-sids.md` — spec IDs estáveis (criados pelo system-dissector)
- `sandeco/reversa` `parecer_reversa_bugs_pratica_diaria_para_claude.md` — origem dos 31 requisitos

---

## Regras absolutas

- **Não escrever fora de `dissects/`** + paths liberados pelo `legacy_policy`.
- **Não copiar artefatos** — referências por ID estável, não por path/anchor.
- **Não marcar `resolved`** antes da closure policy ser satisfeita.
- **Não tomar decisão de spec** sem aprovação humana — debater e recomendar.
- **Não avançar entre agentes** sem `CONTINUAR`.
- **Não publicar detalhes de bug `restricted`** em views ou debates externos.