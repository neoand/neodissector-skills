#!/usr/bin/env python3
"""
migration_init.py — scaffold de arquivos da Time de Migração.

Cria `dissects/<contexto>/migration/` com skeleton para os 5 modos
(Paradigm Advisor, Curator, Strategist, Designer, Inspector).

Uso:
    python3 migration_init.py --context <sistema> --target-stack "Python|24|FastAPI"
    python3 migration_init.py --context <sistema> --from-extract     # lê de extract/components.md

Exit codes:
    0 = sucesso
    1 = erro (contexto não existe, migration já existe)
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import sys


def render_paradigm_decision(target_stack: str) -> str:
    return f"""# Paradigm Decision — (preencher via Modo 1)

## Legado detectado
- **Paradigma**: ?
- **Confiança**: 🟡 (a refinar)

## Stack alvo declarada
```
{target_stack}
```

## Paradigma natural da stack alvo
- **Paradigma inferido**: (preencher via catálogo `references/paradigm-catalog.md`)

## Gap detectado
**(preencher após análise)**

### Implicação 1: (título)
**No legado**: (exemplo concreto citando componentes)
**No paradigma alvo**: (o que muda)

### Implicação 2: ...

(mínimo 4 implicações concretas)

## 3 opções (sempre apresentar)

1. **Adotar paradigma natural** (transformacional)
2. **Forçar similar ao legado** (conservador)
3. **Híbrido** (equilibrado)

## Decisão do usuário
- **Escolha**: 1 / 2 / 3
- **Justificativa**: (texto livre)
- **Derived appetite**: transformational | balanced | conservative

---

> Gerado em {datetime.datetime.now(datetime.timezone.utc).isoformat()} via `migration_init.py`
"""


def render_curator_decisions() -> str:
    return """# Curator — decisões por componente

| ID | Componente | Decisão | Justificativa | Risco |
|----|------------|---------|---------------|-------|
| BR-001 | ? | MIGRATE | ? | ? |
| BR-002 | ? | DISCARD | lib externa cobre | low |
| BR-003 | ? | HUMAN-DECISION | depende de LGPD | high |

> Decisões geradas pelo Modo 2 — Curator. Cada regra do domínio legado
> precisa de uma decisão explícita antes de prosseguir.
"""


def render_strategy() -> str:
    return """# Strategy — (preencher via Modo 3)

## Recomendação
**Estratégia**: Strangler Fig | Big Bang | Parallel Run | Branch by Abstraction

## Justificativa
(baseado nos componentes MIGRATE/DISCARD/HUMAN-DECISION e no gap de paradigma)

## Fases da estratégia
1. ?
2. ?
3. ?

## Critério de cutover
- Métrica primária: ?
- Janela de observação: ?
"""


def render_target_architecture(target_stack: str) -> str:
    return f"""# Target Architecture — (preencher via Modo 4)

## Stack alvo
```
{target_stack}
```

## Módulos da arquitetura destino

| Módulo | Responsabilidade | Dependências | Notas |
|--------|-------------------|---------------|-------|
| ? | ? | ? | ? |

## Integrações externas

| Sistema | Protocolo | Auth | Justificativa |
|---------|-----------|------|---------------|

## Restrições arquiteturais

- ?
"""


def render_target_domain_model() -> str:
    return """# Target Domain Model — (preencher via Modo 4)

## Aggregates

| Aggregate | Root | Entities | Value Objects | Invariantes |
|-----------|------|----------|---------------|-------------|
| ? | ? | ? | ? | ? |

## Repositórios

| Interface | Implementação | Banco/Storage |
|-----------|---------------|---------------|
"""


def render_target_data_model() -> str:
    return """# Target Data Model — (preencher via Modo 4)

## Schema do banco destino

| Tabela/Collection | Coluna/Field | Tipo | Constraint | Origem (legado) |
|--------------------|---------------|------|------------|-----------------|

## Mapping legado → destino

| Campo legado | Tabela origem | Campo destino | Transformação |
|--------------|---------------|---------------|---------------|
"""


def render_data_migration_plan() -> str:
    return """# Data Migration Plan — (preencher via Modo 4)

## Ordem de execução

1. ?
2. ?
3. ?

## Estratégia por tabela

| Tabela origem | Tabela destino | Estratégia | Volume estimado | Downtime |
|---------------|---------------|------------|----------------|----------|
| ? | ? | full-load / incremental / streaming | ? | ? |

## Dry-run + Rollback

- **Dry-run obrigatório**: sim/não
- **Backup verificado**: sim/não
- **Rollback strategy**: ?
"""


def render_parity_specs() -> str:
    return """# Parity Specs — (preencher via Modo 5)

## Estratégia geral
- **Shadow mode** / **Characterization tests** / **Contract tests** / **Data parity**

## Critério de cutover

- **Métrica primária**: (ex: índice de divergência < 0.01% em 30 dias)
- **Janela de observação**: ?
- **Critério de bloqueio**: ?

## Cobertura adaptada ao paradigma

(ver tabela em `references/migration-team.md`)
"""


def cmd_init(args: argparse.Namespace) -> int:
    context = args.context
    context_dir = pathlib.Path("dissects") / context
    if not context_dir.exists():
        print(f"❌ Contexto {context} não existe em dissects/", file=sys.stderr)
        return 1

    migration_dir = context_dir / "migration"
    if migration_dir.exists() and any(migration_dir.iterdir()):
        print(
            f"❌ {migration_dir} já existe e não está vazio. Apague manualmente se quiser refazer.",
            file=sys.stderr,
        )
        return 1

    migration_dir.mkdir(parents=True, exist_ok=True)
    (migration_dir / "parity_tests").mkdir(exist_ok=True)

    target_stack = args.target_stack or "(declarar conforme brief do usuário)"
    (migration_dir / "paradigm_decision.md").write_text(
        render_paradigm_decision(target_stack), encoding="utf-8"
    )
    (migration_dir / "curator_decisions.md").write_text(
        render_curator_decisions(), encoding="utf-8"
    )
    (migration_dir / "strategy.md").write_text(render_strategy(), encoding="utf-8")
    (migration_dir / "target_architecture.md").write_text(
        render_target_architecture(target_stack), encoding="utf-8"
    )
    (migration_dir / "target_domain_model.md").write_text(
        render_target_domain_model(), encoding="utf-8"
    )
    (migration_dir / "target_data_model.md").write_text(
        render_target_data_model(), encoding="utf-8"
    )
    (migration_dir / "data_migration_plan.md").write_text(
        render_data_migration_plan(), encoding="utf-8"
    )
    (migration_dir / "parity_specs.md").write_text(
        render_parity_specs(), encoding="utf-8"
    )
    (migration_dir / "parity_tests" / "README.md").write_text(
        "# Parity Tests\n\nCada fluxo crítico vira um arquivo `.feature` em Gherkin.\n",
        encoding="utf-8",
    )

    print(f"✓ Migration scaffold criado em {migration_dir}")
    print(f"  8 arquivos + 1 pasta (parity_tests/)")
    print(
        f"  Próximo passo: preencher paradigm_decision.md (Modo 1 — Paradigm Advisor)"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--context", required=True, help="nome do contexto (dissects/<context>)"
    )
    parser.add_argument(
        "--target-stack", help="stack alvo (ex: 'Python 3.12|FastAPI|SQLAlchemy')"
    )
    args = parser.parse_args()
    return cmd_init(args)


if __name__ == "__main__":
    sys.exit(main())
