#!/usr/bin/env python3
"""
verify-no-verbatim.py v2 — gate CI independente para o pacote consumer-facing.

Diferente da v1, este NÃO confia no sanitizer. Tem seus próprios detectores
independentes para garantir que NENHUM verbatim da fonte (Enterprise,
OEEL-1, etc.) escape no pacote consumer-facing.

Anderson 2026-09-26 — analogia Compaq/IBM.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import NamedTuple


# ═══════════════ DETECTORS (INDEPENDENTES do sanitizer) ═══════════════

# Detector 1 — Python body verbatim (corpo de método, decorators, etc.)
PYTHON_BODY = re.compile(
    r"^[ \t]+(?:self\.env\[|return [\w_]+\(|return request\.|"
    r"raise ValidationError|@http\.route|@api\.constrains)\s*[(]",
    re.MULTILINE,
)

# Detector 2 — EE-specific mixin names (chatter_horizontal, iap_widget, etc.)
EE_MIXINS = re.compile(
    r"\b(?:chatter_horizontal|iap_widget|mrp_workorder_bus|"
    r"comms_thread_ticket|sale_subscription_share|"
    r"account_reports_xlsx_helper|iap_helpers)\b",
)

# Detector 3 — EE-specific paths (enterprise/, iap_extractor/, etc.)
EE_PATHS = re.compile(
    r"\b(?:enterprise/|iap_extractor/|target-ai-ext/|comms-vendor/|"
    r"iap_widgets/|odoo_enterprise/)\b",
)

# Detector 4 — EE verification marks ([verified] + path verbatim)
EE_VERIF_MARKS = re.compile(
    r"\[verified\].*?(?:models/|controllers/|static/|views/|wizard/|tests/)",
)

# Detector 5 — EE-specific hosts (iap.odoo.com, etc.)
EE_HOSTS = re.compile(
    r"(?:iap\.odoo\.com|enterprise\.odoo\.com|iap-odoo\.com)",
)

# Detector 6 — Function signatures (def _foo() private + def foo() public)
FUNCTION_SIG = re.compile(
    r"^def\s+\w+\s*\(",
    re.MULTILINE,
)

# Detector 7 — Class definitions verbatim
CLASS_SIG = re.compile(
    r"^\s*class\s+([A-Z]\w*)\s*\(",
    re.MULTILINE,
)

# Detector 8 — EE-specific API calls
EE_API_CALLS = re.compile(
    r"\b(?:validate_iap_token|target_ax_call|csdt_check|target_bank_ext|"
    r"comms_vendor_|iap_check_token|enterprise_ax_send)\s*\(",
)

# Detector 9 — Vendor SDK names
VENDOR_SDK = re.compile(
    r"\b(?:vendor-A|target-ai-ext|comms-vendor|ext-ax|ext-iap-vendor|"
    r"target-stack-internal|target-bank-ext)\b",
    re.IGNORECASE,
)

# Detector 10 — Original source paths (addons/)
PATHS_VERBATIM = re.compile(
    r"\baddons/[\w_-]+(/[\w_-]+)*\.(?:py|xml|js|csv|json)"
    r"|\b[\w-]+/[\w-]+\.py:\d+",
)

# Detector 11 — Imports verbatim
IMPORTS_VERBATIM = re.compile(
    r"^\s*(?:from|import)\s+odoo(?:\.addons\.[\w_-]+)?(?:\.[\w_]+)*[\w.,\s*]*$",
    re.MULTILINE,
)


# Detector 12 — Real emails (D5 — leak detection)
REAL_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b",
)

# Detector 13 — Odoo Enterprise reference (B5 — leak)
ODOO_ENTERPRISE_REF = re.compile(
    r"\b(?:Odoo Enterprise|odoo enterprise|enterprise edition)\b",
    re.IGNORECASE,
)


DETECTORS = {
    "PYTHON_BODY": PYTHON_BODY,
    "EE_MIXINS": EE_MIXINS,
    "EE_PATHS": EE_PATHS,
    "EE_VERIF_MARKS": EE_VERIF_MARKS,
    "EE_HOSTS": EE_HOSTS,
    "FUNCTION_SIG": FUNCTION_SIG,
    "CLASS_SIG": CLASS_SIG,
    "EE_API_CALLS": EE_API_CALLS,
    "VENDOR_SDK": VENDOR_SDK,
    "PATHS_VERBATIM": PATHS_VERBATIM,
    "IMPORTS_VERBATIM": IMPORTS_VERBATIM,
    "REAL_EMAIL": REAL_EMAIL,
    "ODOO_ENTERPRISE_REF": ODOO_ENTERPRISE_REF,
}


# Pastas que devem ser EXCLUÍDAS do scan
ALLOWLIST_FILES = {
    "README.md",
    "LICENSE.md",
    "SANITIZATION-MAP.md",
}
ALLOWLIST_DIRS = {
    ".git",
}


class Violation(NamedTuple):
    file: str
    line_no: int
    pattern: str
    excerpt: str


def scan_file(path: pathlib.Path) -> list[Violation]:
    """Scan a single file for all detectors."""
    violations = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return violations

    for line_no, line in enumerate(text.splitlines(), start=1):
        for pattern_name, pattern in DETECTORS.items():
            if pattern.search(line):
                excerpt = line.strip()
                if len(excerpt) > 100:
                    excerpt = excerpt[:97] + "..."
                violations.append(
                    Violation(
                        file=path.name,
                        line_no=line_no,
                        pattern=pattern_name,
                        excerpt=excerpt,
                    )
                )
    return violations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, help="Pacote consumer-facing")
    parser.add_argument("--json", action="store_true", help="Output em JSON")
    parser.add_argument("--quiet", action="store_true", help="Só resumo")
    args = parser.parse_args()

    pkg = pathlib.Path(args.package)
    if not pkg.exists():
        print(f"ERROR: {pkg} not found", file=sys.stderr)
        return 1

    all_violations: list[Violation] = []
    files_scanned = 0

    for src in sorted(pkg.rglob("*")):
        if src.is_dir():
            if any(part in ALLOWLIST_DIRS for part in src.parts):
                continue
            continue
        if not src.is_file():
            continue
        if src.name in ALLOWLIST_FILES:
            continue
        if any(part in ALLOWLIST_DIRS for part in src.parts):
            continue
        files_scanned += 1
        violations = scan_file(src)
        for v in violations:
            all_violations.append(
                Violation(
                    file=v.file,
                    line_no=v.line_no,
                    pattern=v.pattern,
                    excerpt=v.excerpt,
                )
            )

    if args.json:
        out = {
            "package": str(pkg),
            "files_scanned": files_scanned,
            "violations_total": len(all_violations),
            "violations": [v._asdict() for v in all_violations],
            "result": "CLEAN" if not all_violations else "VERBATIM_DETECTED",
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if not all_violations else 2

    print(f"=== Verifying package (Anderson-mode v2 — Compaq/IBM) ===")
    print(f"  Package:        {pkg}")
    print(f"  Files scanned:  {files_scanned}")
    print(
        f"  Allowlisted:    {len(ALLOWLIST_FILES)} (README.md, LICENSE.md, SANITIZATION-MAP.md)"
    )
    print(f"  Detectors:      {len(DETECTORS)} (independent of sanitizer)")
    print()

    if not all_violations:
        print(f"  PACOTE LIMPO - nenhum verbatim detectado")
        print(f"     Safe to deliver to consumer team.")
        return 0

    print(f"  VERBATIM DETECTADO - {len(all_violations)} violações")
    print()

    # Anderson-mode report (B1-B6 + D1-D6 categories)
    by_pattern: dict[str, int] = {}
    for v in all_violations:
        by_pattern[v.pattern] = by_pattern.get(v.pattern, 0) + 1

    # Map detector -> Anderson B/D category
    anderson_mapping = {
        "PYTHON_BODY": "B1 (código verbatim)",
        "EE_API_CALLS": "B1 (method calls EE)",
        "FUNCTION_SIG": "B2 (métodos private _foo)",
        "CLASS_SIG": "B6 (classes EE)",
        "EE_MIXINS": "B6 (mixins EE)",
        "EE_PATHS": "B4 (caminhos enterprise)",
        "PATHS_VERBATIM": "B4 (caminhos verbatim)",
        "EE_VERIF_MARKS": "B4 ([verified] path)",
        "EE_HOSTS": "B5 (origem exposta)",
        "VENDOR_SDK": "B5 (vendor names)",
        "IMPORTS_VERBATIM": "B1 (imports verbatim)",
        "REAL_EMAIL": "D5 (e-mail vazou)",
        "ODOO_ENTERPRISE_REF": "B5 (Enterprise reference)",
    }

    print(f"  Anderson-mode mapping (B1-B6 / D1-D6):")
    for pat, count in sorted(by_pattern.items()):
        category = anderson_mapping.get(pat, "(outros)")
        print(f"    {pat}: {count}  [{category}]")

    print()
    print(f"  Primeiras 5 violações:")
    for v in all_violations[:5]:
        print(f"    [{v.pattern}] {v.file}:{v.line_no}")
        print(f"        {v.excerpt}")

    return 2


if __name__ == "__main__":
    sys.exit(main())
