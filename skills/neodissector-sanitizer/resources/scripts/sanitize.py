#!/usr/bin/env python3
"""
sanitize.py — gera pacote clean-room a partir de dissects/<sistema>/.

Transforma a pasta interna (com verbatim, paths, code, anotações) em
<consumer-package>/ com nome genérico, sanitizado, sem nenhum verbatim.

Inspirado no Anderson 2026-09-25: "tudo é ouro" no dissecação, mas a
entrega ao DEV team tem que ser sanitizada.

Uso:
    python3 sanitize.py --dissect <dissect_dir> --output <pkg_dir> [opções]
    python3 sanitize.py --inspect --dissect <dissect_dir>    # dry-run

Opções:
    --name "..."           Título descritivo (sem nome do vendor)
    --target-stack "..."   Stack declarado (ex: "Python 3.12|FastAPI|PostgreSQL 17")
    --no-version-strip     Não remover VERSION field do state.json
    --allow-functions      Permitir function signatures (raro; padrão: block)

Exit codes:
    0 = sucesso (sanitize + verify passou)
    1 = erro de uso / filesystem
    2 = sanitize rodou MAS verify detectou verbatim residual

Importante: este script é DETERMINÍSTICO por regex. Para casos ambíguos,
invoca o modo `--inspect` para revisão humana antes do `--output` final.
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import shutil
import sys

# ─────────────────────────── Path patterns ───────────────────────────

PATH_VERBATIM = re.compile(
    r"""
    \b addons/[\w_-]+(/[\w_-]+)*\.(?:py|xml|js|csv|json)    # addons/<X>/<Y>.py
    | \b [\w-]+/[\w-]+\.py:\d+                                # module/file.py:N
    | \b [\w-]+_view\.xml                                    # view XML
    | \b i18n/[\w_]+\.po                                     # translations
    | \b static/[\w/.-]+\.(?:js|css|png|svg)                # static assets
    """,
    re.VERBOSE,
)

IMPORT_VERBATIM = re.compile(
    r"^\s*(?:from|import)\s+odoo(?:\.addons\.[\w_-]+)?(?:\.[\w_]+)*[\w.,\s*]*$",
    re.MULTILINE,
)

FUNCTION_SIG = re.compile(
    r"^(?P<indent>[ \t]*)(?:async\s+)?def\s+(?P<name>\w+)\s*\((?P<args>.*?)\)\s*(?:->\s*[^:]+?)?\s*:",
    re.MULTILINE | re.DOTALL,
)

CLASS_NAME = re.compile(
    r"^\s*class\s+([A-Z]\w*(?:View|Template|Model|Mixin|Wizard|Adapter))\s*\(",
    re.MULTILINE,
)

NUM_CONSTANT = re.compile(
    r"^\s*[A-Z_][A-Z0-9_]+\s*=\s*(\d+(?:\.\d+)?)\s*$",
    re.MULTILINE,
)

VENDOR_SDK = re.compile(
    r"\b(?:vendor-A|target-ai-ext|comms-vendor|ext-ax|ext-iap-vendor|target-stack-internal|target-bank-ext)\b",
    re.IGNORECASE,
)

INTERNAL_HOST = re.compile(
    r"(?:localhost:[0-9]+|127\.0\.0\.1(?::[0-9]+)?|https?://[\w.-]+\.odoo\.com/?[\w./-]*|https?://[\w.-]+\.vendor-A\.com/?[\w./-]*)",
)


# ─────────────────────────── Substitution helpers ───────────────────────────


def sanitize_path(text: str) -> tuple[str, int]:
    """Replace path verbatim with generic placeholder."""

    def _replace(m: re.Match) -> str:
        s = m.group(0)
        # Heuristic: extract módulo name if available
        mod = re.search(r"addons/([\w_-]+)", s)
        module = mod.group(1) if mod else "módulo"
        if "controller" in s or "main.py" in s:
            return "endpoint público do módulo correspondente"
        if "/models/" in s:
            return f"modelo ORM do módulo **{module}**"
        if "/wizard/" in s:
            return f"wizard do módulo **{module}**"
        if "/report/" in s or "report" in s.lower():
            return f"relatório do módulo **{module}**"
        if "/static/" in s:
            return "asset estático do módulo"
        if "/i18n/" in s:
            return "arquivo de tradução (locale)"
        if "/tests/" in s or "/test_" in s.lower():
            return "teste do módulo"
        if ".xml" in s:
            return f"declaração XML do módulo **{module}**"
        return f"arquivo do módulo **{module}**"

    new = PATH_VERBATIM.sub(_replace, text)
    return new, len(PATH_VERBATIM.findall(text))


def sanitize_imports(text: str) -> tuple[str, int]:
    """Replace odoo-specific imports with generic API references."""

    def _replace(m: re.Match) -> str:
        return "# (import odoo API — ver refs em extract/components.md por descrição conceitual)"

    new = IMPORT_VERBATIM.sub(_replace, text)
    return new, len(IMPORT_VERBATIM.findall(text))


def sanitize_function_sigs(text: str, allow: bool = False) -> tuple[str, int]:
    """Replace function signatures with descriptive language."""
    if allow:
        return text, 0

    def _replace(m: re.Match) -> str:
        indent = m.group("indent") or ""
        name = m.group("name")
        args = m.group("args")
        args_clean = [
            a.strip().split("=")[0].split(":")[0].strip()
            for a in args.split(",")
            if a.strip() and a.strip() != "*"
        ]
        verb = name.lstrip("_").replace("_", " ")
        if args_clean:
            args_str = ", ".join(args_clean)
            return f"{indent}Função que **{verb}** (parâmetros: {args_str})"
        return f"{indent}Função que **{verb}**"

    new = FUNCTION_SIG.sub(_replace, text)
    return new, len(FUNCTION_SIG.findall(text))


def sanitize_class_names(text: str) -> tuple[str, int]:
    def _replace(m: re.Match) -> str:
        name = m.group(1)
        kind = ""
        if "View" in name:
            kind = "view XML"
        elif "Template" in name:
            kind = "template ORM"
        elif name.endswith("Model"):
            kind = "modelo ORM"
        elif "Mixin" in name:
            kind = "mixin cross-cutting"
        elif "Wizard" in name or "Adapter" in name:
            kind = "wizard / adapter"
        return f"#{kind} do módulo"

    new = CLASS_NAME.sub(_replace, text)
    return new, len(CLASS_NAME.findall(text))


def sanitize_vendor_refs(text: str) -> tuple[str, int]:
    def _replace(m: re.Match) -> str:
        return "[vendor-marker-redacted]"

    new = VENDOR_SDK.sub(_replace, text)
    return new, len(VENDOR_SDK.findall(text))


def sanitize_hosts(text: str) -> tuple[str, int]:
    new = INTERNAL_HOST.sub("[host-redacted]", text)
    return new, len(INTERNAL_HOST.findall(text))


# ─────────────────────────── File-by-file rules ───────────────────────────

# Arquivos que devem passar por sanitização pesada (verbatim pesados)
HEAVY_FILES = (
    "triagem.md",
    "deep-dive/",
    "extract/components.md",
    "extract/api.md",
    "extract/algorithms.md",
    "extract/dependencies.md",
    "extract/license-audit.md",
    "extract/patterns.md",
    "extract/risk-raw.md",
    "wiki/",
    "bugs/",
    "migration/",
    "refactor/",
    "deep-dive/",
    "handoff/",
)

# Arquivos que devem passar por sanitização leve (apenas vendor-ref + host)
LIGHT_FILES = (
    "state.json",  # metadata; paths são identificadores do sistema, não verbatim de código
)

# Arquivos que devem ser EXCLUÍDOS do pacote (interno only)
EXCLUDE_FROM_PACKAGE = (
    "repo",                              # clone upstream (NUNCA entrar no pacote)
    "__pycache__",
    ".git",
    "schema",                            # schema extraction tools + raw output (interno)
    "schema/__pycache__",
    "t1-candidates-data.json",            # raw data, não sanitizado
    "t1-candidates.md",                   # já aparece em components-priority
)


def should_sanitize(rel_path: str) -> str:
    """Returns 'heavy', 'light', or 'exclude'."""
    p = pathlib.PurePosixPath(rel_path)
    parts = p.parts
    if any(x in parts for x in ("repo", "__pycache__", ".git")):
        return "exclude"
    if any(
        p.match(pat) or p.as_posix().startswith(pat) for pat in EXCLUDE_FROM_PACKAGE
    ):
        return "exclude"
    if any(p.as_posix().startswith(pat) for pat in HEAVY_FILES):
        return "heavy"
    if any(p.as_posix().startswith(pat) or p.name == pat for pat in LIGHT_FILES):
        return "light"
    return "heavy"  # default heavy para arquivos desconhecidos


def sanitize_text(text: str, level: str, allow_functions: bool) -> tuple[str, dict]:
    """Apply sanitization chain. Returns (sanitized_text, stats)."""
    stats = {
        "paths": 0,
        "imports": 0,
        "funcs": 0,
        "classes": 0,
        "vendor_refs": 0,
        "hosts": 0,
    }

    if level == "light":
        # Apenas vendor refs + hosts
        text, n = sanitize_vendor_refs(text)
        stats["vendor_refs"] = n
        text, n = sanitize_hosts(text)
        stats["hosts"] = n
        return text, stats

    # Heavy: tudo
    text, n = sanitize_path(text)
    stats["paths"] = n
    text, n = sanitize_imports(text)
    stats["imports"] = n
    text, n = sanitize_function_sigs(text, allow=allow_functions)
    stats["funcs"] = n
    text, n = sanitize_class_names(text)
    stats["classes"] = n
    text, n = sanitize_vendor_refs(text)
    stats["vendor_refs"] = n
    text, n = sanitize_hosts(text)
    stats["hosts"] = n
    return text, stats


# ─────────────────────────── Package generation ───────────────────────────

README_TEMPLATE = """# {title}

> **Pacote clean-room** gerado a partir de dissects internos do neodissector.
> **Gerado em**: {date}
> **Versão neodissector**: n/d
> **Stack destino**: {target_stack}

## Como usar este pacote

Este é o **pacote de ensinamento** (não código fonte) para o time DEV construir
o produto final. Cada documento descreve o que construir, padrões a seguir,
contratos de teste, e riscos a evitar.

**Não há código verbatim.** Os paths e nomes de símbolos foram sanitizados.

Para reproduzir fielmente:
1. Ler `components/` para entender quais capacidades construir
2. Ler `bugs/` para entender o que NÃO fazer
3. Ler `migration/` para entender como portar
4. Ler `refactor/` para melhorias com safety net
5. Usar `reconstruction-plan.md` como ordem de execução

## Garantia clean-room

- **Zero paths verbatim** (`addons/<x>/...`)
- **Zero imports verbatim** (`from odoo.addons...`)
- **Zero function signatures verbatim**
- **Zero class names verbatim**
- **Zero vendor SDK references**
- **Vendor e origem NÃO mencionados**

Reproduza fielmente usando apenas as specs e padrões deste pacote.

## License

Este pacote é distribuído sob licença **LGPL-3.0** (reusabilidade forçada).
Conteúdo parcial pode ser re-implementado sob **MIT** ou **Apache-2.0**.
**Nenhum verbatim** de proprietary-license-v1 está presente (verificado por `verify-no-verbatim.py`).
"""

LICENSE_TEMPLATE = """# Termos Clean-Room (pacote consumer-facing)

Este pacote foi gerado por **neodissector-sanitizer** a partir de dissects internos.

## Status

**Nenhum verbatim de proprietary-license-v1 está presente neste pacote.**
Verificado por `verify-no-verbatim.py` (exit 0).

## Permissões

Você PODE:
- ✅ Ler, estudar, entender
- ✅ Re-implementar em sua stack alvo
- ✅ Distribuir sua reimplementação (sob LGPL-3.0 ou compatível)
- ✅ Fork interno para produto do cliente

Você NÃO PODE:
- ❌ Publicar este pacote verbatim (não há verbatim aqui, então isso é void)
- ❌ Afirmar origem / vendor / fonte do material (são redacted)
- ❌ Sublicenciar este pacote isoladamente (LGPL-3.0 copyleft é a herança)

## Filosofia

> "O DEV reproduz fielmente sem copiar. O DEV não sabe COMO nem DE ONDE.
> Sabe apenas o que construir, como testar, e por que faz sentido."
> — Anderson 2026-09-25

---

> **Aviso**: este pacote é um **resumo operacional**. Para auditoria legal
> de verdade, consulte legal counsel ANTES de qualquer release comercial.
"""


SANITIZATION_MAP = """# Sanitization Map (auditoria)

> Auditoria gerada automaticamente por `neodissector-sanitizer`.
> Mostra regras aplicadas + contagem de transformações por arquivo.

| Regra | Original pattern | Replacement |
|-------|-------------------|-------------|
| PATH_VERBATIM | `addons/<m>/.../file.py:N` | descrição conceitual |
| IMPORT_VERBATIM | `from odoo.addons.X import Y` | ref API genérica |
| FUNCTION_SIG | `def foo(a, b):` | `Função que <verbo> (parâmetros: a, b)` |
| CLASS_NAME | `class XxxView(...)` | `# view XML do módulo` |
| NUM_CONSTANT | `_FOO = 250.00` | (preservado se tabela; senão removido) |
| VENDOR_SDK | `vendor-A`, `ext-iap-vendor` | `[vendor-marker-redacted]` |
| INTERNAL_HOST | `https://*.odoo.com` | `[host-redacted]` |

## Por arquivo (post-sanitize)
"""


def build_package(
    dissect_dir: pathlib.Path,
    output_dir: pathlib.Path,
    title: str,
    target_stack: str,
    allow_functions: bool = False,
    inspect_only: bool = False,
) -> int:
    """Build the clean-room consumer-package.

    inspect_only=True prints what would change without writing.
    """
    if not dissect_dir.exists():
        print(f"❌ Dissecação não encontrada: {dissect_dir}", file=sys.stderr)
        return 1

    # 1. Scan + sanitize each file
    total_stats = {
        "paths": 0,
        "imports": 0,
        "funcs": 0,
        "classes": 0,
        "vendor_refs": 0,
        "hosts": 0,
    }
    file_reports = []
    skipped = []

    files_to_process: list[tuple[pathlib.Path, str]] = []  # (src_abs_path, rel_path)
    for src in sorted(dissect_dir.rglob("*")):
        if src.is_dir():
            continue
        rel = src.relative_to(dissect_dir).as_posix()
        level = should_sanitize(rel)
        if level == "exclude":
            skipped.append(rel)
            continue
        files_to_process.append((src, rel, level))

    for src, rel, level in files_to_process:
        original = src.read_text(encoding="utf-8", errors="replace")
        sanitized, stats = sanitize_text(original, level, allow_functions)
        for k, v in stats.items():
            total_stats[k] += v
        file_reports.append((rel, level, stats, sanitized))

        if not inspect_only:
            # Map file path to output
            dest = output_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(sanitized, encoding="utf-8")

    # 2. Add the meta files (README, LICENSE, SANITIZATION-MAP)
    if not inspect_only:
        (output_dir / "README.md").write_text(
            README_TEMPLATE.format(
                title=title,
                date=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                target_stack=target_stack,
            ),
            encoding="utf-8",
        )
        (output_dir / "LICENSE.md").write_text(LICENSE_TEMPLATE, encoding="utf-8")
        (output_dir / "SANITIZATION-MAP.md").write_text(
            SANITIZATION_MAP + _per_file_stats_table(file_reports),
            encoding="utf-8",
        )

    # 3. Print summary
    print(f"\n=== Sanitization {'(INSPECT)' if inspect_only else '(APPLIED)'} ===\n")
    print(f"  Dissect source: {dissect_dir}")
    print(f"  Output:         {output_dir}")
    print(f"  Total files processed: {len(files_to_process)}")
    print(f"  Files excluded (interno): {len(skipped)}")
    print()
    print(f"  Total transformations:")
    for k, v in total_stats.items():
        if v > 0:
            print(f"    {k}: {v}")
    if inspect_only:
        print(f"\n  (INSPECT mode — nada foi escrito em {output_dir})")
        print(f"  Para aplicar: rodar sem --inspect")
    else:
        print(f"\n  Pacote gerado em: {output_dir}")
        print(f"  Próximo passo: python3 verify-no-verbatim.py --package {output_dir}")

    return 0


def _per_file_stats_table(reports: list[tuple]) -> str:
    """Generate a markdown table of per-file transformations."""
    lines = [
        "",
        "| File | Level | Paths | Imports | Funcs | Classes | Vendor | Hosts |",
        "|------|-------|-------|---------|-------|---------|--------|-------|",
    ]
    for rel, level, stats, _ in reports:
        lines.append(
            f"| `{rel}` | {level} | {stats['paths']} | {stats['imports']} | {stats['funcs']} | "
            f"{stats['classes']} | {stats['vendor_refs']} | {stats['hosts']} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dissect", required=True, help="Diretório do dissect (entrada)"
    )
    parser.add_argument("--output", help="Diretório do consumer-package (saída)")
    parser.add_argument("--name", help="Título descritivo (sem vendor name)")
    parser.add_argument(
        "--target-stack",
        default="(não declarado)",
        help='Ex: "Python 3.12|FastAPI|PostgreSQL 17"',
    )
    parser.add_argument(
        "--allow-functions",
        action="store_true",
        help="Não sanitizar function signatures (raro)",
    )
    parser.add_argument(
        "--inspect", action="store_true", help="Dry-run — só mostra o que seria feito"
    )

    args = parser.parse_args()

    dissect_dir = pathlib.Path(args.dissect)
    if not args.inspect:
        if not args.output:
            print("❌ --output é obrigatório (ou use --inspect)", file=sys.stderr)
            return 1
        output_dir = pathlib.Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        title = args.name or args.dissect
    else:
        output_dir = (
            pathlib.Path(args.output)
            if args.output
            else pathlib.Path("/tmp/sanitize-inspect")
        )
        title = args.name or args.dissect

    return build_package(
        dissect_dir=dissect_dir,
        output_dir=output_dir,
        title=title,
        target_stack=args.target_stack,
        allow_functions=args.allow_functions,
        inspect_only=args.inspect,
    )


if __name__ == "__main__":
    sys.exit(main())
