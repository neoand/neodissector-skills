#!/usr/bin/env python3
"""
legacy_policy.py — gate de permissão de escrita no projeto alvo.

Função: carregar `.neodissector/config.json` (ou `neodissector.config.json`)
e responder se um path específico está liberado para escrita pelo neodissector.

Inspirado em `reversa-config.json` do framework `sandeco/reversa`
(spec: legacy-code-edition.md, escore 88/100). Diferenças:

  - **Agnóstico de stack**: o schema não menciona stack específico.
  - **Fail-safe**: erro de leitura = bloqueado (nunca liberado).
  - **Documentação canônica**: este script é o ÚNICO lugar onde a
    decisão "permitir/negar" é tomada.

Uso programático:
    from legacy_policy import Policy
    policy = Policy.load(project_root)
    decision = policy.check("src/main.py", action="write")
    if decision.allowed:
        # ok
    else:
        # recusar com decision.reason

Uso CLI:
    python3 legacy_policy.py check <path> [--action read|write|delete]
    python3 legacy_policy.py status [--project-root <path>]
    python3 legacy_policy.py init [--project-root <path>] [--allow-all]

Exit codes:
    0 = permitido
    1 = negado
    2 = erro (config ausente/inválido — fail-safe)
"""

from __future__ import annotations

import argparse
import dataclasses
import fnmatch
import json
import pathlib
import sys
from typing import Literal


# Territórios próprios do neodissector — sempre graváveis, independente da config.
NEODISSECTOR_TERRITORIES = (
    ".neodissector/",
    "dissects/",
    "neodissector-sdd/",
    "neodissector_docs/",
    "neodissector_forward/",
    "neodissector_bugs/",
    "neodissector_refactor/",
    "_neodissector_sdd/",
    "_neodissector_forward/",
)

CONFIG_PATHS = (
    ".neodissector/config.json",
    "neodissector.config.json",
)


@dataclasses.dataclass(frozen=True)
class Decision:
    """Resultado de uma consulta de policy."""

    allowed: bool
    reason: str
    config_path: pathlib.Path | None
    action: str
    target: str


@dataclasses.dataclass(frozen=True)
class Policy:
    """Snapshot imutável da policy de um projeto."""

    allow_legacy_edits: bool
    allowed_paths: tuple[str, ...]
    config_path: pathlib.Path | None

    @classmethod
    def load(cls, project_root: pathlib.Path) -> Policy:
        """Carrega config do projeto.

        - Config presente e válida → Policy com os campos do JSON.
        - Config presente mas inválida → raise PolicyLoadError.
        - Config ausente → Policy default (allow=false, lista vazia,
          config_path=None). Territórios próprios continuam funcionando
          via check().
        """
        for candidate in CONFIG_PATHS:
            p = project_root / candidate
            if p.exists():
                try:
                    raw = p.read_text(encoding="utf-8")
                    data = json.loads(raw)
                except (OSError, json.JSONDecodeError) as e:
                    raise PolicyLoadError(f"config inválida em {p}: {e}") from e

                allow = bool(data.get("allowLegacyEdits", False))
                paths_raw = data.get("allowedPaths", [])
                if not isinstance(paths_raw, list):
                    raise PolicyLoadError(
                        f"`allowedPaths` deve ser lista, recebeu {type(paths_raw).__name__}"
                    )
                paths = tuple(str(p) for p in paths_raw)
                return cls(allow_legacy_edits=allow, allowed_paths=paths, config_path=p)
        return cls(allow_legacy_edits=False, allowed_paths=(), config_path=None)

    @classmethod
    def require_load(cls, project_root: pathlib.Path) -> Policy:
        """Como load(), mas raise PolicyNotConfiguredError se ausente."""
        for p in CONFIG_PATHS:
            if (project_root / p).exists():
                return cls.load(project_root)
        raise PolicyNotConfiguredError(
            f"nenhuma config encontrada em {project_root}. Procurado: {', '.join(CONFIG_PATHS)}. "
            f"Para criar: `python3 legacy_policy.py init --project-root {project_root}`"
        )

    def is_in_territory(self, target: str) -> bool:
        """Verifica se target está num território próprio do neodissector."""
        target_norm = self._normalize(target)
        for territory in NEODISSECTOR_TERRITORIES:
            t_norm = self._normalize(territory).rstrip("/")
            if target_norm == t_norm or target_norm.startswith(t_norm + "/"):
                return True
        return False

    def is_path_allowed(self, target: str) -> bool:
        """Verifica se target casa com algum glob em allowedPaths."""
        target_norm = self._normalize(target)
        for pattern in self.allowed_paths:
            pattern_norm = self._normalize(pattern)
            if self._glob_match(pattern_norm, target_norm):
                return True
        return False

    @staticmethod
    def _normalize(path: str) -> str:
        """Normaliza path: backslashes → forward slashes; remove APENAS `./` literal do início.

        Não usa lstrip('./') porque isso removeria o `.` de paths como
        `.neodissector/` (que distingue de `neodissector-sdd/`).
        """
        norm = path.replace("\\", "/")
        if norm.startswith("./"):
            norm = norm[2:]
        return norm

    @staticmethod
    def _glob_match(pattern: str, path: str) -> bool:
        """Glob matcher que entende `**` recursivo e `*` single-level."""
        if "**" not in pattern and "*" not in pattern and "?" not in pattern:
            return pattern == path
        if "**" in pattern:
            parts = pattern.split("**")
            if len(parts) == 2:
                prefix, suffix = parts
                prefix = prefix.rstrip("/")
                suffix = suffix.lstrip("/")
                if prefix and not path.startswith(prefix + "/") and path != prefix:
                    return False
                if suffix:
                    if "/" in suffix:
                        if suffix not in path:
                            return False
                    else:
                        if not (path.endswith("/" + suffix) or path.endswith(suffix)):
                            return False
                return True
        return fnmatch.fnmatch(path, pattern)

    def check(
        self,
        target: str,
        action: Literal["read", "write", "delete"] = "write",
    ) -> Decision:
        """Decide se `target` pode sofrer `action` sob esta policy.

        Ordem:
        1. Território próprio → sempre permitido (mesmo sem config).
        2. Sem config → BLOQUEADO fail-safe.
        3. allowLegacyEdits=false → BLOQUEADO.
        4. allow=true + allowedPaths vazio → BLOQUEADO.
        5. allow=true + target casa com allowedPaths → permitido.
        6. Caso contrário → BLOQUEADO.
        """
        # 1. Territórios próprios: sempre liberado, mesmo sem config.
        if self.is_in_territory(target):
            return Decision(
                allowed=True,
                reason="target em território próprio do neodissector",
                config_path=self.config_path,
                action=action,
                target=target,
            )

        # 2. Sem config → fail-safe
        if self.config_path is None:
            return Decision(
                allowed=False,
                reason=(
                    "nenhuma config encontrada — fail-safe. "
                    "Para liberar, crie com `python3 legacy_policy.py init` "
                    "e adicione o path à `allowedPaths`"
                ),
                config_path=None,
                action=action,
                target=target,
            )

        # 3. allowLegacyEdits=false
        if not self.allow_legacy_edits:
            return Decision(
                allowed=False,
                reason=(
                    "allowLegacyEdits=false (default seguro). "
                    f"Para liberar, edite {self.config_path} "
                    "e adicione o path à `allowedPaths`"
                ),
                config_path=self.config_path,
                action=action,
                target=target,
            )

        # 4. allow=true mas lista vazia
        if not self.allowed_paths:
            return Decision(
                allowed=False,
                reason=(
                    "allowLegacyEdits=true mas `allowedPaths` está vazio. "
                    "Por segurança, sem lista = sem liberação. "
                    "Adicione globs específicos em `allowedPaths`"
                ),
                config_path=self.config_path,
                action=action,
                target=target,
            )

        # 5. match
        if self.is_path_allowed(target):
            return Decision(
                allowed=True,
                reason="target casa com allowedPaths",
                config_path=self.config_path,
                action=action,
                target=target,
            )

        # 6. fallback
        return Decision(
            allowed=False,
            reason="target NÃO casa com nenhum padrão em allowedPaths",
            config_path=self.config_path,
            action=action,
            target=target,
        )


class PolicyLoadError(Exception):
    """Config existe mas é inválida."""


class PolicyNotConfiguredError(Exception):
    """Nenhuma config encontrada no projeto."""


# ───────────────────────── CLI ─────────────────────────


def cmd_check(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root or ".").resolve()
    try:
        policy = Policy.load(project_root)
    except PolicyLoadError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 2

    decision = policy.check(args.path, action=args.action)
    marker = "✓" if decision.allowed else "✗"
    print(f"{marker} {args.action:6s} {args.path}")
    print(f"  reason: {decision.reason}")
    print(f"  config: {decision.config_path}")
    return 0 if decision.allowed else 1


def cmd_status(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root or ".").resolve()
    print(f"=== Neodissector Legacy Policy — status ===\n")
    print(f"Project root: {project_root}")
    print(f"Config paths procurados: {', '.join(CONFIG_PATHS)}")
    print(f"Territórios próprios (sempre graváveis):")
    for t in NEODISSECTOR_TERRITORIES:
        print(f"  - {t}")

    try:
        policy = Policy.require_load(project_root)
    except PolicyNotConfiguredError as e:
        print(f"\n⚠ {e}")
        print(f"  Estado atual: BLOQUEADO (fail-safe).")
        print(f"  Para inicializar: python3 legacy_policy.py init")
        return 0
    except PolicyLoadError as e:
        print(f"\n❌ Config inválida: {e}")
        print(f"  Estado: BLOQUEADO (fail-safe). Corrija o JSON e rode novamente.")
        return 2

    print(f"\n✓ Config carregada de: {policy.config_path}")
    print(f"  allowLegacyEdits: {policy.allow_legacy_edits}")
    print(f"  allowedPaths: {len(policy.allowed_paths)} padrão(ões)")
    for p in policy.allowed_paths:
        print(f"    - {p}")

    if policy.allow_legacy_edits and not policy.allowed_paths:
        print(f"\n⚠ allowLegacyEdits=true com allowedPaths VAZIO.")
        print(
            f"  Estado efetivo: BLOQUEADO. Adicione globs ou use --allow-all no init."
        )
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    project_root = pathlib.Path(args.project_root or ".").resolve()
    target = project_root / CONFIG_PATHS[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not args.force:
        print(f"❌ Config já existe em {target}. Use --force para sobrescrever.")
        return 1

    config: dict[str, object] = {
        "version": 1,
        "allowLegacyEdits": False,
        "allowedPaths": [],
    }

    if args.allow_all:
        config["allowLegacyEdits"] = True
        config["allowedPaths"] = ["**"]
        config["_warning"] = (
            "LIBERAÇÃO IRRESTRITA — todo o projeto pode ser editado. Use com parcimônia."
        )
    elif args.allow_paths:
        config["allowLegacyEdits"] = True
        config["allowedPaths"] = list(args.allow_paths)

    target.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"✓ Config criada em {target}")
    print(f"  allowLegacyEdits: {config['allowLegacyEdits']}")
    print(f"  allowedPaths: {config['allowedPaths']}")
    if args.allow_all:
        print(f"\n⚠ Liberação IRRESTRITA habilitada.")
    print(f"\nDocumentação: ~/.agents/skills/system-dissector/NEODISSECTOR-CONFIG.md")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="verifica se um path pode ser editado")
    p_check.add_argument("path", help="path relativo ao project_root")
    p_check.add_argument(
        "--action", choices=["read", "write", "delete"], default="write"
    )
    p_check.add_argument("--project-root", default=".")
    p_check.set_defaults(func=cmd_check)

    p_status = sub.add_parser("status", help="mostra estado atual da policy")
    p_status.add_argument("--project-root", default=".")
    p_status.set_defaults(func=cmd_status)

    p_init = sub.add_parser("init", help="cria config inicial")
    p_init.add_argument("--project-root", default=".")
    p_init.add_argument(
        "--force", action="store_true", help="sobrescrever config existente"
    )
    p_init.add_argument(
        "--allow-all", action="store_true", help="liberação irrestrita (cuidado)"
    )
    p_init.add_argument(
        "--allow-paths", nargs="+", metavar="GLOB", help="globs a liberar"
    )
    p_init.set_defaults(func=cmd_init)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
