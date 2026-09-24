#!/usr/bin/env python3
"""
verify-invocation.py — gate de CI para o eixo model-invoked vs user-invoked
NO ESCOPO DO NEODISSECTOR.

Escopo: 22 skills canônicas (21 user-invoked + 1 model-invoked).
O ecossistema `~/.agents/skills/` tem ~1300 skills de outros frameworks —
elas ficam FORA deste gate.

Regras verificadas (R1-R8 aplicadas SÓ no escopo do neodissector):
  R1. Frontmatter YAML válido.
  R2. Campos `name` + `description` presentes e não-vazios.
  R3. Campo `disable-model-invocation` explícito (true/false).
  R4. Skills em USER_INVOKED têm flag = true.
  R5. Skills em MODEL_INVOKED têm flag = false (ausente ou "false").
  R6. Flag = true SEM estar em USER_INVOKED/MODEL_INVOKED → falha.
  R7. `description` de user-invoked NÃO contém frase-gatilho de modelo
      ("use when", "use this skill when", "digitar '/").
  R8. Toda skill listada em USER_INVOKED/MODEL_INVOKED existe no disco.

Exit code 0 = APROVADO, 1 = violações.

Uso:
    python3 verify-invocation.py [--quiet]
    python3 verify-invocation.py --json
"""

from __future__ import annotations
import argparse
import json
import pathlib
import re
import sys
from typing import NamedTuple

SKILLS_DIR = pathlib.Path("/Users/andersongoliveira/.agents/skills")

# Escopo canônico do neodissector — atualizado em 2026-09-24 (Items 1, 2-8).
# Adicionar nova skill aqui é INTENCIONAL — força revisão.
USER_INVOKED = frozenset(
    {
        # RE skills (origem)
        "reverse-engineer",
        "binary-ninja",
        "binary-analysis-patterns",
        "protocol-reverse-engineering",
        "malware-analyst",
        "firmware-analyst",
        "memory-forensics",
        "dwarf-expert",
        "anti-reversing-techniques",
        "ai-assisted-re",
        "mobile-re",
        "variant-analysis",
        "audit-context-building",
        "wiki-researcher",
        "neodoo-integrate",
        # Companion skills (neodissector Items 2-8 — 2026-09-24)
        "neodissector-reconstructor",
        "neodissector-brainstorm",
        "neodissector-bug",
        "neodissector-migration",
        "neodissector-refactor",
        "neodissector-pricing",
    }
)

MODEL_INVOKED = frozenset(
    {
        "system-dissector",
    }
)

ALL_KNOWN = USER_INVOKED | MODEL_INVOKED

MODEL_TRIGGERS = (
    "use when",
    "use this skill when",
    "digitar '/",
)


class Violation(NamedTuple):
    skill: str
    rule: str
    detail: str


def parse_frontmatter(raw: str) -> tuple[dict[str, str] | None, str]:
    if raw.startswith("\ufeff"):
        raw = raw.lstrip("\ufeff")
    m = re.match(r"^---\n(.*?)\n---\n", raw, re.DOTALL)
    if not m:
        return None, "frontmatter ausente ou inválido"
    fm_str = m.group(1)
    fields: dict[str, str] = {}
    current_key: str | None = None
    for line in fm_str.splitlines():
        if not line.strip():
            continue
        m2 = re.match(r"^([a-zA-Z_-]+):\s*(.*)$", line)
        if m2:
            current_key = m2.group(1)
            fields[current_key] = m2.group(2).strip()
        elif current_key:
            fields[current_key] = (fields[current_key] + " " + line.strip()).strip()
    return fields, ""


def verify_skill(skill_name: str) -> list[Violation]:
    violations: list[Violation] = []
    path = SKILLS_DIR / skill_name / "SKILL.md"

    if not path.exists():
        return [Violation(skill_name, "R0", "SKILL.md ausente no disco")]

    raw = path.read_text(encoding="utf-8")
    fm, err = parse_frontmatter(raw)
    if fm is None:
        return [Violation(skill_name, "R1", err)]

    # R2 — name + description
    if "name" not in fm or not fm["name"]:
        violations.append(Violation(skill_name, "R2", "campo `name` ausente ou vazio"))
    if "description" not in fm or not fm["description"]:
        violations.append(
            Violation(skill_name, "R2", "campo `description` ausente ou vazio")
        )

    # R3 — flag explícita
    flag_raw = fm.get("disable-model-invocation", None)
    if flag_raw is None:
        violations.append(
            Violation(
                skill_name,
                "R3",
                "`disable-model-invocation` ausente (true/false obrigatório)",
            )
        )
        flag = None
    elif flag_raw.lower() == "true":
        flag = True
    elif flag_raw.lower() == "false":
        flag = False
    else:
        violations.append(
            Violation(
                skill_name, "R3", f"`disable-model-invocation` inválido: {flag_raw!r}"
            )
        )
        flag = None

    # R4/R5 — coerência
    if skill_name in USER_INVOKED and flag is not True:
        violations.append(
            Violation(
                skill_name, "R4", f"deveria ser user-invoked mas flag={flag_raw!r}"
            )
        )
    if skill_name in MODEL_INVOKED and flag is True:
        violations.append(
            Violation(skill_name, "R5", f"deveria ser model-invoked mas flag=true")
        )

    # R6 — flag=true sem classificação
    if flag is True and skill_name not in ALL_KNOWN:
        violations.append(
            Violation(
                skill_name,
                "R6",
                "flag=true mas skill não está em USER_INVOKED/MODEL_INVOKED",
            )
        )

    # R7 — description sem gatilho de modelo (em user-invoked)
    if flag is True and "description" in fm:
        desc_lower = fm["description"].lower()
        for trigger in MODEL_TRIGGERS:
            if trigger in desc_lower:
                violations.append(
                    Violation(
                        skill_name,
                        "R7",
                        f"description contém gatilho de modelo: {trigger!r}",
                    )
                )
                break

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="só resumo final")
    parser.add_argument("--json", action="store_true", help="output em JSON")
    args = parser.parse_args()

    all_violations: list[Violation] = []
    by_skill: dict[str, list[Violation]] = {n: [] for n in sorted(ALL_KNOWN)}

    # R8 — toda skill canônica existe no disco
    missing = sorted(n for n in ALL_KNOWN if not (SKILLS_DIR / n / "SKILL.md").exists())
    for m in missing:
        v = Violation(m, "R8", "skill canônica listada mas SKILL.md ausente no disco")
        all_violations.append(v)
        by_skill[m].append(v)

    # Verificar skills existentes no escopo
    for skill_name in sorted(ALL_KNOWN):
        if (SKILLS_DIR / skill_name / "SKILL.md").exists():
            violations = verify_skill(skill_name)
            by_skill[skill_name] = violations
            all_violations.extend(violations)

    if args.json:
        out = {
            "scope": sorted(ALL_KNOWN),
            "skills_verified": len(ALL_KNOWN),
            "approved": sum(1 for v in by_skill.values() if not v),
            "violations_total": len(all_violations),
            "violations": [
                {"skill": v.skill, "rule": v.rule, "detail": v.detail}
                for v in all_violations
            ],
            "result": "APPROVED" if not all_violations else "REJECTED",
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if not all_violations else 1

    print(
        f"=== Neodissector — Invocation Axis Gate (escopo: {len(ALL_KNOWN)} skills) ===\n"
    )

    if not args.quiet:
        for skill_name in sorted(ALL_KNOWN):
            kind = "USER-invoked" if skill_name in USER_INVOKED else "MODEL-invoked"
            violations = by_skill[skill_name]
            if not violations:
                print(f"  ✓ {skill_name:35s} ({kind})")
            else:
                print(f"  ✗ {skill_name:35s} ({kind})")
                for v in violations:
                    print(f"      {v.rule}: {v.detail}")

    approved = sum(1 for v in by_skill.values() if not v)
    print(f"\n=== RESUMO ===")
    print(f"  Skills no escopo : {len(ALL_KNOWN)}")
    print(f"  Skills aprovadas  : {approved}")
    print(f"  Total violações   : {len(all_violations)}")

    if all_violations:
        print(f"\n❌ RESULTADO: REPROVADO")
        by_rule: dict[str, int] = {}
        for v in all_violations:
            by_rule[v.rule] = by_rule.get(v.rule, 0) + 1
        for rule, count in sorted(by_rule.items()):
            print(f"    {rule}: {count}")
        return 1

    print(f"\n✅ RESULTADO: ✓ APROVADO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
