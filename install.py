#!/usr/bin/env python3
"""
install.py — instala uma versão específica do neodissector-skills em
~/.agents/skills/ (ou outro diretório via --target).

Inspirado em `npx reversa install` do framework `sandeco/reversa`,
adaptado para Python + convenção de skills user-level.

Uso:
    python3 install.py                  # última versão (main)
    python3 install.py --version 1.0.0 # tag específica
    python3 install.py --dry-run       # só mostra o que faria
    python3 install.py --target DIR    # instala em DIR
    python3 install.py --update        # atualiza para última, preserva customizações
    python3 install.py --ref main      # branch específica (default: main)
    python3 install.py --repo URL      # remote customizado (default: github.com/neoand/neodissector-skills)

Por padrão, instala em ~/.agents/skills/ e usa o repo público em
github.com/neoand/neodissector-skills. Para forks ou mirrors internos,
use --repo.

Exit codes:
    0 = sucesso (ou dry-run sem mudanças)
    1 = erro (rede, permissão, conflito)
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Literal


DEFAULT_REPO = "https://github.com/neoand/neodissector-skills.git"
DEFAULT_REF = "main"
DEFAULT_TARGET = pathlib.Path.home() / ".agents" / "skills"


def log(msg: str) -> None:
    """Log com prefixo `[* neodissector-install]`."""
    print(f"[* neodissector-install] {msg}")


def err(msg: str) -> None:
    """Erro com prefixo `[!]` para stderr."""
    print(f"[! neodissector-install] {msg}", file=sys.stderr)


def run_git(
    *args: str, cwd: pathlib.Path | None = None, check: bool = True
) -> subprocess.CompletedProcess:
    """Wrapper de git com mensagens claras."""
    result = subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        err(f"git {' '.join(args)} falhou (exit {result.returncode})")
        if result.stdout:
            err(f"stdout: {result.stdout}")
        if result.stderr:
            err(f"stderr: {result.stderr}")
        raise subprocess.CalledProcessError(result.returncode, ["git"] + list(args))
    return result


def fetch_version(repo: str, ref: str) -> str:
    """Lê VERSION do remote via clone raso."""
    log(f"Consultando VERSION do remote ({repo}@{ref})...")
    with tempfile.TemporaryDirectory(prefix=".tmp-clone-") as tmpdir:
        tmp = pathlib.Path(tmpdir)
        # Clone raso: repo é pequeno (~5MB) e isso é robusto.
        # (sparse-checkout com VERSION-arquivo falha: 'is not a directory'.)
        run_git(
            "clone",
            "--depth=1",
            "--branch",
            ref,
            repo,
            str(tmp),
            check=True,
        )
        version_file = tmp / "VERSION"
        if not version_file.exists():
            err(f"VERSION não encontrado em {repo}@{ref}")
            sys.exit(1)
        version = version_file.read_text(encoding="utf-8").strip()
        log(f"VERSION encontrada: {version}")
        return version


def install_skills(
    repo: str,
    ref: str,
    target: pathlib.Path,
    version: str | None = None,
    dry_run: bool = False,
    update: bool = False,
) -> int:
    """Instala skills em target. Se update=True, faz git pull no destino."""

    target.mkdir(parents=True, exist_ok=True)

    # Caso 1: instalação nova (target vazio ou não é repo git)
    is_existing_repo = (target / ".git").exists()

    if update and not is_existing_repo:
        err(f"--update requer que {target} já seja um clone do neodissector-skills")
        err("Rode sem --update primeiro para criar o clone inicial.")
        return 1

    if not update and not is_existing_repo:
        # Clone inicial
        log(f"Clonando {repo}@{ref} → {target}")
        if dry_run:
            log(f"[DRY-RUN] git clone --branch {ref} {repo} {target}")
            return 0
        # Se target não está vazio, abortar
        if any(target.iterdir()):
            err(
                f"{target} já existe e não é vazio. Use --update ou apague manualmente."
            )
            return 1
        run_git("clone", "--branch", ref, repo, str(target))
        log(f"✓ Instalado em {target}")
        return 0

    if update and is_existing_repo:
        # Update via fetch + reset
        log(f"Atualizando {target} para {ref}...")
        if dry_run:
            log(f"[DRY-RUN] git fetch origin && git reset --hard origin/{ref}")
            return 0
        run_git("fetch", "origin", cwd=target)
        run_git("reset", "--hard", f"origin/{ref}", cwd=target)
        log(f"✓ Atualizado em {target}")
        return 0

    # Caso 2: target já existe mas não é clone (intervenção manual?)
    if not update and is_existing_repo:
        # Verificar se é o mesmo remote
        try:
            remote_url = run_git(
                "remote", "get-url", "origin", cwd=target, check=False
            ).stdout.strip()
        except subprocess.CalledProcessError:
            remote_url = ""
        if "neodissector-skills" not in remote_url:
            err(
                f"{target} é um clone mas não é do neodissector-skills (remote={remote_url!r})"
            )
            err("Para forçar: apague manualmente e rode sem --update.")
            return 1
        # Mesmo remote, oferece update
        log(f"{target} já é um clone válido do neodissector-skills")
        log("Use --update para atualizar.")
        return 0

    return 0


def verify_install(target: pathlib.Path) -> bool:
    """Roda verify-invocation.py no target instalado. Retorna True se APROVADO."""
    verify_script = (
        target / "system-dissector" / "resources" / "scripts" / "verify-invocation.py"
    )
    if not verify_script.exists():
        err(f"verify-invocation.py não encontrado em {verify_script}")
        return False
    log(f"Rodando verify-invocation.py em {target}...")
    result = subprocess.run([sys.executable, str(verify_script)], cwd=target)
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="tag/versão específica (e.g., 1.0.0, v1.0.0)")
    parser.add_argument(
        "--ref", default=DEFAULT_REF, help=f"branch/ref (default: {DEFAULT_REF})"
    )
    parser.add_argument(
        "--repo", default=DEFAULT_REPO, help=f"URL do repo (default: {DEFAULT_REPO})"
    )
    parser.add_argument(
        "--target",
        type=pathlib.Path,
        default=DEFAULT_TARGET,
        help=f"diretório alvo (default: {DEFAULT_TARGET})",
    )
    parser.add_argument("--dry-run", action="store_true", help="só mostra o que faria")
    parser.add_argument(
        "--update", action="store_true", help="atualizar clone existente"
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="pula verify-invocation.py após install",
    )
    parser.add_argument(
        "--force", action="store_true", help="sobrescreve target não-vazio (perigoso)"
    )

    args = parser.parse_args()

    # Ref resolvida: --version sobrescreve --ref
    ref = args.version if args.version else args.ref

    # Pré-flight: git instalado?
    if not shutil.which("git"):
        err("git não encontrado no PATH. Instale git antes de usar install.py.")
        return 1

    log(f"Repo: {args.repo}")
    log(f"Ref:  {ref}")
    log(f"Target: {args.target}")
    log(f"Modo: {'DRY-RUN' if args.dry_run else 'REAL'}")
    log("")

    # Determinar versão que vai ser instalada
    if not args.update:
        try:
            version = fetch_version(args.repo, ref)
            log(f"Versão a instalar: {version}")
        except (subprocess.CalledProcessError, OSError) as e:
            err(f"Falha ao consultar VERSION: {e}")
            return 1
    else:
        version = "(atualização)"

    # Confirmar se target não-vazio e --update ausente (a menos que --force)
    if not args.update and not args.force and args.target.exists():
        if any(args.target.iterdir()):
            err(f"{args.target} já existe e não é vazio.")
            err(
                "Use --update para atualizar OU --force para sobrescrever (perigoso, apaga customizações)."
            )
            return 1

    # Instalar
    rc = install_skills(
        repo=args.repo,
        ref=ref,
        target=args.target,
        version=version,
        dry_run=args.dry_run,
        update=args.update,
    )
    if rc != 0:
        return rc

    # Validar com verify-invocation.py (a menos que skip)
    if not args.dry_run and not args.skip_verify:
        if not verify_install(args.target):
            err("Install OK mas verify-invocation.py FALHOU. Veja saída acima.")
            err(
                "Reporte o problema em https://github.com/neoand/neodissector-skills/issues"
            )
            return 1

    log("")
    log("✓ Pronto. Use `system-dissector` ou qualquer companion para começar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
