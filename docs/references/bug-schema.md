# Bug Schema (v1) — neodissector-bug

> Schema canônico para `dissects/<contexto>/bugs/<id>/bug.md`.
> Inspirado em `sandeco/reversa` (parecer_bugs) com simplificações agnósticas.

## Frontmatter canônico

```yaml
---
id: BUG-20260924-A7K3
display_number: 42                          # humano, opcional
created_at: 2026-09-24T15:30:00Z
updated_at: 2026-09-24T15:30:00Z

# Estado
status: open                                # open | active | resolved
phase: triaging                             # ver tabela abaixo

# Classificação
severity: high                              # critical | high | medium | low
priority: P1                                # P0 | P1 | P2 | P3
visibility: normal                          # normal | internal | restricted | embargoed

# Origem
origin:
  type: manual-report                       # ver tabela abaixo
  external_ref:                             # opcional
    provider: github
    id: "#317"

# Ownership (inferir de CODEOWNERS quando possível)
ownership:
  owning_team: unclassified
  codeowners: []
  assignees: []
  reviewers: []

# Segurança
security_suspected: false                   # se true, pedir confirmação humana

# Closure
closure_policy:
  type: local-software                      # ver tabela abaixo
  requires: [regression-tests-passed]
  satisfied: false
  closed_at: null
---

# <título do bug>

## Resumo
<1-2 frases do problema relatado>

## Steps to Reproduce
1. <passo>
2. <passo>
3. <observado>

## Mitigation (se aplicável)
```yaml
mitigation:
  required: true
  status: applied
  kind: rollback
  applied_at: 2026-09-24T15:35:00Z
  temporary: true
```

## Reproduction Capsule
```yaml
reproduction:
  status: confirmed                         # confirmed | intermittent | not-reproduced | unknown
  capsule:
    repository:
      base_commit: a1b2c3d4
      branch: main
    environment:
      os: darwin
      runtime: python-3.12
    execution:
      command: pytest tests/checkout/test_discount.py -x
      exit_code: 1
      duration_ms: 1420
    determinism:
      attempts: 5
      failures: 5
      reproduction_rate: 1.0
      classification: deterministic          # deterministic | intermittent | environment-dependent
      suspected_triggers: []
    evidence:
      trace: evidence/reproduction/trace.json
      stdout: evidence/reproduction/stdout.log
```

## Affected code (onde aparece)
```yaml
affected_code:
  - file: src/checkout/fechamento.py
    symbol: checkout.fechar_pedido
    line: 142
    commit: a1b2c3d
```

## Root cause (onde nasceu) — epistemológico
```yaml
root_cause:
  status: confirmed                         # hypothesized | supported | confirmed | rejected
  confidence: 0.94
  hypothesis: "O cupom é reaplicado durante a fase de fechamento"
  causal_path:
    - cart.apply_coupon
    - order.close
    - apply_adjustments
    - apply_coupon                          # ← duplicação
  evidence:
    - run: RUN-004
      observation: total 90 -> 81
    - trace: TRACE-002
      observation: apply_coupon called twice
  code_refs:
    - file: src/checkout/fechamento.py
      symbol: checkout.fechar_pedido
      commit: a1b2c3d
      blob_sha: 718f...
```

## Relations (outros bugs / specs)
```yaml
relationships:
  - type: caused-by
    target: BUG-20260920-X9Y2
    status: confirmed                       # proposed | supported | confirmed | rejected
    confidence: 0.91
    evidence: [TRACE-044]
  - type: spec-ref
    target: SPEC-DOMAIN-0042
    status: confirmed
spec_refs:                                   # IDs estáveis do system-dissector
  - id: SPEC-DOMAIN-0042
```

## Change set (Correction Change Set — tipado)
```yaml
change_set:
  - id: CHG-001
    kind: test                              # test | code | configuration | migration | data-repair | dependency | specification | observability
    artifact: tests/repro/test_bug_42.py
    purpose: prove-defect
  - id: CHG-002
    kind: code
    artifact: src/checkout/fechamento.py
    purpose: eliminate-root-cause
  - id: CHG-003
    kind: data-repair
    artifact: scripts/repair_duplicate_orders.py
    purpose: heal-historical-state
```

## Tests
```yaml
tests:
  reproduction_tests:
    - id: BRT-001
      artifact: tests/repro/test_bug_42.py
      proves: reported-manifestation
  regression_tests:
    - id: REG-001
      artifact: tests/payment/test_idempotency.py
      protects: SPEC-PAYMENT-0042
```

## Data impact (separação code healed ≠ system healed)
```yaml
data_impact:
  assessed: true
  historical_corruption: confirmed
  affected_records_estimate: 38421
  external_state_affected: false
data_repair:
  required: true
  strategy: reconciliation-script
  dry_run: passed
  backup_verified: true
  idempotent: true
  rollback_available: true
  artifact: scripts/repair_duplicate_orders.py
```

## Change risk
```yaml
change_risk:
  score: 45
  classification: medium                     # low | medium | high
  blast_radius:
    affected_symbols: 3
    transitive_callers: 12
  public_api_change: false
  database_change: true
  external_contract_change: false
```

## Regression analysis (se houver suspeita)
```yaml
regression_analysis:
  suspected: true
  last_known_good: 718ac31
  first_known_bad: ff82d14
  bisect:
    attempted: true
    automated: true
    culprit_commit: b921af2
  introduced_by:
    commit: b921af2
    pull_request: 118
```

## Spec verdict (obrigatório antes de closure)
```yaml
spec_verdict:
  type: spec-correta                         # spec-correta | spec-desatualizada | spec-gap
  rationale: "spec já definia desconto único; código divergiu"
  approved_by: <user>
  approved_at: 2026-09-24T16:00:00Z
# Se desatualizada ou gap:
# addendum_ref: _addenda/bug-BUG-20260924-A7K3-v001.md
```

## Resolution
```yaml
resolution:
  kind: fixed                               # fixed | wontfix | duplicate | instrumentation-required
  root_cause_status: confirmed
  change_set_applied: [CHG-001, CHG-002, CHG-003]
  diffs:
    - CHG-001.diff
    - CHG-002.diff
  tests_proof:
    red: [BRT-001 fails]
    green: [BRT-001 passes, REG-001 passes]
  spec_verdict: spec-correta
```

## Closure
```yaml
closure:
  policy_type: local-software
  requires_satisfied: [regression-tests-passed]
  closed_at: 2026-09-24T16:30:00Z
  post_fix_observation:
    window:
      started_at: null                      # obrigatório para production-service
      duration: null
    signals: []
    verdict: null                           # verified | failed | inconclusive
```

---

## Tabelas de referência

### Status

| Valor | Significado |
|---|---|
| `open` | Registrado, ainda não iniciado |
| `active` | Em trabalho (qualquer phase ≠ triaging/finalizada) |
| `resolved` | closure_policy satisfeita |

### Phase (separada de status)

`triaging` → `mitigating` → `reproducing` → `diagnosing` → `planning` → `testing` → `patching` → `reviewing` → `ci-verifying` → `merging` → `releasing` → `deploying` → `observing` → `awaiting-human` → `done`

### Origin

`manual-report` | `github-issue` | `gitlab-issue` | `ci-failure` | `telemetry` | `alert` | `support` | `customer` | `security-advisory` | `inspection` | `other`

### Closure policy

| Type | Requires |
|---|---|
| `local-software` | `[regression-tests-passed]` |
| `package` | `[merged, fixed-version-published]` |
| `production-service` | `[merged, deployed, observation-window-passed]` |

### Resolution kind

`fixed` | `wontfix` | `duplicate` | `instrumentation-required` | `cannot-reproduce` | `external-cause`

### Visibility

`normal` | `internal` | `restricted` (segurança, sem detalhes em views públicas) | `embargoed` (não enviar a harness externo)

---

## Validação (gate)

`neodissector-bug` deve recusar bug.md inválido se:
- ID não segue `BUG-YYYYMMDD-XXXX`
- Status `resolved` mas `closure.satisfied: false`
- Status `resolved` mas `closure_policy.requires` não está em `closure.requires_satisfied`
- `root_cause.status: confirmed` mas sem evidence list
- `change_set` vazio (para kind: fixed)
- `spec_verdict` ausente em `resolution`
- `visibility: restricted` mas aparecer em `generated/graph.html` público