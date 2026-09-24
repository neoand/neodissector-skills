#!/usr/bin/env python3
"""
session.py — gerenciador de sessões de brainstorm do neodissector.

Sessões vivem em `.neodissector/brainstorms/<NNN>-<short-name>/`.
A sessão ativa é `.neodissector/active-brainstorm.json`.

Uso:
    python3 session.py init "minha ideia"          # cria sessão
    python3 session.py resume                     # retoma sessão ativa
    python3 session.py list                        # lista sessões
    python3 session.py status                      # mostra sessão ativa
    python3 session.py close                       # fecha sessão ativa (sem deletar)
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(".neodissector")
BRAINSTORMS = ROOT / "brainstorms"
ACTIVE = ROOT / "active-brainstorm.json"


def slugify(idea: str) -> str:
    """Converte 'Minha Ideia Complexa' → 'minha-ideia-complexa'."""
    s = idea.lower().strip()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")


def next_id() -> str:
    """Próximo ID sequencial (001, 002, ...)."""
    if not BRAINSTORMS.exists():
        return "001"
    nums = []
    for p in BRAINSTORMS.iterdir():
        m = re.match(r"^(\d+)-", p.name)
        if m:
            try:
                nums.append(int(m.group(1)))
            except ValueError:
                pass
    return f"{(max(nums) if nums else 0) + 1:03d}"


def cmd_init(args: argparse.Namespace) -> int:
    if not args.idea:
        print('❌ Forneça uma ideia: `session.py init "minha ideia"`')
        return 1

    idea = args.idea
    slug = slugify(idea)
    if not slug:
        print(f"❌ Não consegui gerar slug a partir de {idea!r}")
        return 1

    session_id = next_id()
    session_dir = BRAINSTORMS / f"{session_id}-{slug}"
    session_dir.mkdir(parents=True, exist_ok=False)

    # README com a ideia original
    (session_dir / "README.md").write_text(
        f"# Brainstorm — {idea}\n\n"
        f"**Sessão**: {session_id}\n"
        f"**Slug**: {slug}\n"
        f"**Iniciada em**: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n\n"
        f"## Ideia original\n\n> {idea}\n\n"
        f"## Pipeline\n\n"
        f"1. Framer   → `framing.md`\n"
        f"2. Explorer → `options.md`\n"
        f"3. Challenger → `risks.md`\n"
        f"4. Arbiter  → `decision.md`\n"
        f"5. Pre-Spec → `pre-spec.md`\n",
        encoding="utf-8",
    )

    # Ativar sessão
    ACTIVE.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE.write_text(
        json.dumps(
            {
                "active_session": f"{session_id}-{slug}",
                "current_agent": "framer",
                "idea": idea,
                "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(f"✓ Sessão criada: {session_dir.relative_to(pathlib.Path('.'))}")
    print(f"  Sessão ativa: {session_id}-{slug}")
    print(f"  Próximo: Modo 1 — Framer (leia a seção 'Modo 1 — Framer' do SKILL.md)")
    print(f"  Quando terminar, diga CONTINUAR para ir ao Modo 2 (Explorer)")
    return 0


def cmd_resume(_args: argparse.Namespace) -> int:
    if not ACTIVE.exists():
        print("❌ Nenhuma sessão ativa. Use `init` primeiro.")
        return 1
    state = json.loads(ACTIVE.read_text(encoding="utf-8"))
    session_name = state["active_session"]
    current = state.get("current_agent", "framer")
    session_dir = BRAINSTORMS / session_name
    if not session_dir.exists():
        print(f"❌ Sessão {session_name} não encontrada no disco.")
        return 1
    print(f"✓ Sessão ativa: {session_name}")
    print(f"  Etapa atual: Modo {current}")
    print(f"  Pasta: {session_dir.relative_to(pathlib.Path('.'))}")
    print(f"\nArtefatos presentes:")
    for p in sorted(session_dir.iterdir()):
        marker = "✓" if p.name != "README.md" and p.suffix == ".md" else "  "
        print(f"  {marker} {p.name}")
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    if not BRAINSTORMS.exists():
        print("(nenhuma sessão)")
        return 0
    sessions = sorted(BRAINSTORMS.iterdir())
    if not sessions:
        print("(nenhuma sessão)")
        return 0
    active_name = None
    if ACTIVE.exists():
        active_name = json.loads(ACTIVE.read_text(encoding="utf-8")).get(
            "active_session"
        )
    print(f"=== Sessões de brainstorm ===\n")
    for s in sessions:
        marker = "→ " if s.name == active_name else "  "
        # Ler README para pegar a ideia
        readme = s / "README.md"
        idea = "(sem README)"
        if readme.exists():
            for line in readme.read_text(encoding="utf-8").splitlines():
                if line.startswith("> "):
                    idea = line[2:].strip()
                    break
        # Listar artefatos
        artifacts = sorted(
            p.name for p in s.iterdir() if p.is_file() and p.name != "README.md"
        )
        print(f"{marker}{s.name} — {idea}")
        for a in artifacts:
            print(f"      • {a}")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    return cmd_resume(_args)


def cmd_close(_args: argparse.Namespace) -> int:
    if not ACTIVE.exists():
        print("❌ Nenhuma sessão ativa.")
        return 1
    session_name = json.loads(ACTIVE.read_text(encoding="utf-8"))["active_session"]
    ACTIVE.unlink()
    print(
        f"✓ Sessão {session_name} fechada. Pasta preservada em {BRAINSTORMS / session_name}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="cria nova sessão")
    p_init.add_argument("idea", nargs="?", help="ideia bruta (string)")
    p_init.set_defaults(func=cmd_init)

    p_resume = sub.add_parser("resume", help="retoma sessão ativa")
    p_resume.set_defaults(func=cmd_resume)

    p_list = sub.add_parser("list", help="lista sessões")
    p_list.set_defaults(func=cmd_list)

    p_status = sub.add_parser("status", help="mostra estado da sessão ativa")
    p_status.set_defaults(func=cmd_status)

    p_close = sub.add_parser("close", help="fecha sessão ativa (preserva pasta)")
    p_close.set_defaults(func=cmd_close)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
