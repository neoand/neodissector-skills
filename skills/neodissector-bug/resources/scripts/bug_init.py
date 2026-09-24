#!/usr/bin/env python3
"""
bug_init.py — scaffold de bug.md a partir de input mínimo.

Cria `dissects/<contexto>/bugs/<BUG-id>/bug.md` com frontmatter canônico
baseado no schema em `references/bug-schema.md`.

Uso:
    python3 bug_init.py --context <sistema> --title "Título curto" --severity high
    python3 bug_init.py init --context <sistema> --title "Título curto"   (alternativa)
    python3 bug_init.py list --context <sistema>
    python3 bug_init.py --help

Exit codes:
    0 = sucesso
    1 = erro (contexto não existe, ID conflito, permissão)
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import secrets
import sys


VALID_SEVERITY = ("critical", "high", "medium", "low")
VALID_PRIORITY = ("P0", "P1", "P2", "P3")
VALID_VISIBILITY = ("normal", "internal", "restricted", "embargoed")
VALID_ORIGIN = (
    "manual-report",
    "github-issue",
    "gitlab-issue",
    "ci-failure",
    "telemetry",
    "alert",
    "support",
    "customer",
    "security-advisory",
    "inspection",
    "other",
)


def next_bug_id(bugs_root: pathlib.Path, today: datetime.date) -> str:
    """Próximo ID sequencial: BUG-YYYYMMDD-XXXX (XXXX = 4 chars base16)."""
    if not bugs_root.exists():
        return f"BUG-{today.strftime('%Y%m%d')}-{secrets.token_hex(2).upper()}"
    prefix = f"BUG-{today.strftime('%Y%m%d')}-"
    max_seq = -1
    for p in bugs_root.iterdir():
        if p.is_dir() and p.name.startswith(prefix):
            tail = p.name[len(prefix) :]
            try:
                seq = int(tail, 16)
                if seq > max_seq:
                    max_seq = seq
            except ValueError:
                continue
    if max_seq < 0:
        return f"{prefix}{secrets.token_hex(2).upper()}"
    next_seq = max_seq + 1
    return f"{prefix}{next_seq:04X}"


def slugify(text: str, max_len: int = 50) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s[:max_len] if s else "untitled"


def render_template(
    bug_id: str,
    title: str,
    severity: str,
    priority: str,
    visibility: str,
    origin: str,
    today: datetime.date,
) -> str:
    return f"""---
id: {bug_id}
created_at: {today.isoformat()}T00:00:00Z
updated_at: {today.isoformat()}T00:00:00Z

status: open
phase: triaging

severity: {severity}
priority: {priority}
visibility: {visibility}

origin:
  type: {origin}
  external_ref: null

ownership:
  owning_team: unclassified
  codeowners: []
  assignees: []
  reviewers: []

security_suspected: false

closure_policy:
  type: local-software
  requires: [regression-tests-passed]
  satisfied: false
  closed_at: null
---

# {title}

## Resumo

<1-2 frases do problema relatado.>

## Steps to Reproduce

1. <passo>
2. <passo>
3. <observado>

## Mitigation (preencher se severity ∈ {{critical, high}} E sistema em uso)

```yaml
mitigation:
  required: false
  status: none
  kind: null
```

## Reproduction Capsule

```yaml
reproduction:
  status: unknown
  capsule:
    repository: {{ base_commit: null, branch: null }}
    environment: {{ os: null, runtime: null }}
    execution: {{ command: null, exit_code: null, duration_ms: null }}
    determinism:
      attempts: 0
      failures: 0
      reproduction_rate: 0.0
      classification: unknown
```

## Affected code

```yaml
affected_code: []
```

## Root cause (epistemológico)

```yaml
root_cause:
  status: hypothesized
  hypothesis: ""
  evidence: []
  code_refs: []
```

## Relations

```yaml
relationships: []
spec_refs: []
```

## Change set

```yaml
change_set: []
```

## Tests

```yaml
tests:
  reproduction_tests: []
  regression_tests: []
```

## Data impact

```yaml
data_impact:
  assessed: false
  historical_corruption: unknown
  affected_records_estimate: null
data_repair:
  required: false
```

## Spec verdict (obrigatório antes de closure)

```yaml
spec_verdict:
  type: null
  rationale: ""
  approved_by: null
  approved_at: null
```

## Resolution

```yaml
resolution:
  kind: null
  root_cause_status: hypothesized
```

## Closure

```yaml
closure:
  policy_type: local-software
  requires_satisfied: []
  closed_at: null
```
"""


def cmd_init(args: argparse.Namespace) -> int:
    title = args.title or "Untitled bug"

    context_dir = pathlib.Path("dissects") / args.context
    if not context_dir.exists():
        print(f"❌ Contexto {args.context} não existe em dissects/", file=sys.stderr)
        print(
            f"   Criar primeiro: dissect_utils.py init {args.context}", file=sys.stderr
        )
        return 1

    if args.origin not in VALID_ORIGIN:
        print(
            f"❌ origin inválida: {args.origin}. Válidas: {', '.join(VALID_ORIGIN)}",
            file=sys.stderr,
        )
        return 1

    bugs_root = context_dir / "bugs" / "bugs"
    today = datetime.datetime.now(datetime.timezone.utc).date()
    bug_id = next_bug_id(bugs_root, today)
    short = slugify(title)
    bug_dir = bugs_root / f"{bug_id}-{short}"
    bug_dir.mkdir(parents=True, exist_ok=False)

    (bug_dir / "README.md").write_text(
        f"# Bug — {title}\n\n"
        f"**ID**: `{bug_id}`\n"
        f"**Slug**: {short}\n"
        f"**Severidade**: {args.severity} | **Prioridade**: {args.priority}\n"
        f"**Origem**: {args.origin}\n"
        f"**Criado em**: {today.isoformat()}\n\n"
        f"## Pipeline\n\n"
        f"1. intake → `bug.md` (gerado por bug_init.py)\n"
        f"2. fix → reproduction + diagnosis + change_set\n"
        f"3. closure → satisfaction da closure_policy\n",
        encoding="utf-8",
    )

    bug_md = render_template(
        bug_id=bug_id,
        title=title,
        severity=args.severity,
        priority=args.priority,
        visibility=args.visibility,
        origin=args.origin,
        today=today,
    )
    (bug_dir / "bug.md").write_text(bug_md, encoding="utf-8")

    (bug_dir / "evidence").mkdir(exist_ok=True)
    (bug_dir / "fix").mkdir(exist_ok=True)
    (bug_dir / "inspection").mkdir(exist_ok=True)

    print(f"✓ Bug criado: {bug_dir}")
    print(f"  ID: {bug_id}")
    print(
        f"  Próximo passo: preencher `bug.md` (Steps to Reproduce, Mitigation, Reproduction Capsule)"
    )
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    bugs_root = pathlib.Path("dissects") / args.context / "bugs" / "bugs"
    if not bugs_root.exists():
        print(f"(nenhum bug em {args.context})")
        return 0
    bugs = sorted(bugs_root.iterdir())
    if not bugs:
        print(f"(nenhum bug em {args.context})")
        return 0
    print(f"=== Bugs em {args.context} ===\n")
    for b in bugs:
        if not b.is_dir():
            continue
        bug_md = b / "bug.md"
        if not bug_md.exists():
            continue
        text = bug_md.read_text(encoding="utf-8")
        m = re.search(r"^status:\s*(\S+)$", text, re.MULTILINE)
        sev = re.search(r"^severity:\s*(\S+)$", text, re.MULTILINE)
        status = m.group(1) if m else "?"
        severity = sev.group(1) if sev else "?"
        print(f"  {b.name:50s} status={status:10s} severity={severity}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "cmd",
        nargs="?",
        default="init",
        choices=["init", "list"],
        help="init (default) ou list",
    )
    parser.add_argument(
        "--context", required=True, help="nome do contexto (dissects/<context>)"
    )
    parser.add_argument("--title", help="título curto do bug (apenas cmd=init)")
    parser.add_argument(
        "--severity", choices=VALID_SEVERITY, default="medium", help="apenas cmd=init"
    )
    parser.add_argument(
        "--priority", choices=VALID_PRIORITY, default="P2", help="apenas cmd=init"
    )
    parser.add_argument(
        "--visibility",
        choices=VALID_VISIBILITY,
        default="normal",
        help="apenas cmd=init",
    )
    parser.add_argument(
        "--origin",
        choices=VALID_ORIGIN,
        default="manual-report",
        help="apenas cmd=init",
    )

    args = parser.parse_args()
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "list":
        return cmd_list(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
