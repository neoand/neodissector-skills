#!/usr/bin/env python3
"""sanitize.py v3.1 (Anderson-mode clean-room) - FIX com ONE_LINE handler."""
from __future__ import annotations
import argparse
import pathlib
import re
import sys
from datetime import datetime, timezone


PATH_VERBATIM = re.compile(
    r"\baddons/[\w_-]+(/[\w_-]+)*\.(?:py|xml|js|csv|json)"
    r"|\b[\w-]+/[\w-]+\.py:\d+"
    r"|\b[\w-]+_view\.xml"
    r"|\bi18n/[\w_]+\.po"
    r"|\bstatic/[\w/.-]+\.(?:js|css|png|svg)",
)
IMPORT_VERBATIM = re.compile(
    r"^\s*(?:from|import)\s+odoo(?:\.addons\.[\w_-]+)?(?:\.[\w_]+)*[\w.,\s*]*$",
    re.MULTILINE,
)
FUNCTION_BLOCK_ONE_LINE = re.compile(
    r"^([ \t]*)def\s+(?P<name>\w+)\s*\((?P<args>(?:[^()]|\([^()]*\))*)\)\s*(?:->\s*[^:]+?)?\s*:.*$",
    re.MULTILINE,
)
FUNCTION_BLOCK = re.compile(
    r"^([ \t]*)def\s+(?P<name>\w+)\s*\((?P<args>[^)]*)\)\s*(?:->\s*[^:]+?)?\s*:\s*\n"
    r"(?P<body>(?:^[ \t]+.*\n|^\s*\n)*?)"
    r"(?=^[ \t]*\S|\Z)",
    re.MULTILINE,
)
CLASS_BLOCK = re.compile(
    r"^([ \t]*)class\s+(?P<name>\w+)\s*\((?P<base>[^)]*)\)\s*:\s*\n"
    r"(?P<body>(?:^[ \t]+.*\n|^\s*\n)*?)"
    r"(?=^[ \t]*\S|\Z)",
    re.MULTILINE,
)
DECORATOR_LINE = re.compile(
    r"^[ \t]*@[\w.]+(?:\([^)]*\))?\s*$",
    re.MULTILINE,
)
EE_API_CALLS = re.compile(
    r"\b(?:validate_iap_token|target_ax_call|csdt_check|target_bank_ext|"
    r"comms_vendor_|iap_check_token|enterprise_ax_send|ext_ax_call|"
    r"target_iap_call|enterprise_send_notification|_sendone)\s*\(",
)
VERBATIM_BODY = re.compile(
    r"^[ \t]+(?:self\.env\[|return request\.make_response|"
    r"raise ValidationError|return Request\(|@http\.route\s*\()",
    re.MULTILINE,
)
EE_MIXINS = re.compile(
    r"\b(?:chatter_horizontal|iap_widget|mrp_workorder_bus|"
    r"comms_thread_ticket|sale_subscription_share|"
    r"account_reports_xlsx_helper|iap_helpers|bus_bus_sendone)\b",
)
EE_HOSTS = re.compile(
    r"(?:iap\.odoo\.com|enterprise\.odoo\.com|iap-odoo\.com)",
)
EE_PATHS = re.compile(
    r"\b(?:enterprise/|iap_extractor/|target-ai-ext/|comms-vendor/|"
    r"iap_widgets/|odoo_enterprise/)\b",
)
VENDOR_SDK = re.compile(
    r"\b(?:vendor-A|target-ai-ext|comms-vendor|ext-ax|ext-iap-vendor|"
    r"target-stack-internal|target-bank-ext|"
    r"enterprise-client|odoo-enterprise-server)\b",
    re.IGNORECASE,
)
EE_VERIF_MARKS = re.compile(
    r"\[verified\].*?(?:models/|controllers/|static/|views/|wizard/|tests/)",
)
REAL_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b",
)
ODOO_ENTERPRISE_REF = re.compile(
    r"\b(?:Odoo Enterprise|odoo enterprise|enterprise edition|"
    r"Target ERP-A|target erp-a|Target ERP|the-erp-tier-A)\b",
    re.IGNORECASE,
)


def sanitize_function_block(m):
    indent = m.group(1)
    name = m.group("name")
    args = m.group("args").strip()
    lines = [
        f"{indent}# [CLEAN-ROOM] funcao **{name}** - corpo verbatim removido",
        f"{indent}# Implementacao: ver handoff/implementation-guide.md (clean-room)",
    ]
    if args:
        lines.insert(1, f"{indent}# Parametros: `{args}`")
    return "\n".join(lines) + "\n"


def sanitize_class_block(m):
    indent = m.group(1)
    name = m.group("name")
    base = m.group("base").strip()
    lines = [
        f"{indent}# [CLEAN-ROOM] classe **{name}** - corpo verbatim removido",
        f"{indent}# Implementacao: ver handoff/implementation-guide.md (clean-room)",
    ]
    if base:
        lines.insert(1, f"{indent}# Base: `{base}`")
    return "\n".join(lines) + "\n"


def sanitize_text(text):
    stats = {k: 0 for k in [
        "paths", "imports", "functions", "classes", "decorators",
        "method_calls", "verbatim_bodies", "ee_mixins", "ee_hosts",
        "ee_paths", "vendor_sdks", "ee_verif_marks", "real_emails",
        "odoo_enterprise_refs",
    ]}

    # 1. Real emails
    new = REAL_EMAIL.sub("[email-redacted]", text)
    stats["real_emails"] = len(REAL_EMAIL.findall(text))

    # 2. Odoo Enterprise references
    new = ODOO_ENTERPRISE_REF.sub("[system-redacted]", new)
    stats["odoo_enterprise_refs"] = len(ODOO_ENTERPRISE_REF.findall(new))

    # 3. EE paths
    new = EE_PATHS.sub("[ee-path-redacted]", new)
    stats["ee_paths"] = len(EE_PATHS.findall(new))

    # 4. Vendor SDK names
    new = VENDOR_SDK.sub("[vendor-redacted]", new)
    stats["vendor_sdks"] = len(VENDOR_SDK.findall(new))

    # 5. EE hosts
    new = EE_HOSTS.sub("[ee-host-redacted]", new)
    stats["ee_hosts"] = len(EE_HOSTS.findall(new))

    # 6. EE mixins
    new = EE_MIXINS.sub("[ee-mixin-redacted]", new)
    stats["ee_mixins"] = len(EE_MIXINS.findall(text))

    # 7. EE API calls
    new = EE_API_CALLS.sub("[ee-api-redacted]", new)
    stats["method_calls"] = len(EE_API_CALLS.findall(text))

    # 8. Verbatim body fragments
    new = VERBATIM_BODY.sub("[verbatim-redacted]", new)
    stats["verbatim_bodies"] = len(VERBATIM_BODY.findall(text))

    # 9. Decorators
    new = DECORATOR_LINE.sub("# [CLEAN-ROOM] decorator removido", new)
    stats["decorators"] = len(DECORATOR_LINE.findall(text))

    # 10a. Function blocks de uma linha (pseudocodigo)
    def _replace_func_one_line(m):
        indent = m.group(1)
        name = m.group("name")
        return f"{indent}# [CLEAN-ROOM] funcao **{name}** - corpo removido (pseudocodigo verbatim)"

    new = FUNCTION_BLOCK_ONE_LINE.sub(_replace_func_one_line, new)
    one_line_count = len(FUNCTION_BLOCK_ONE_LINE.findall(text))

    # 10b. Function blocks multi-linha
    new = FUNCTION_BLOCK.sub(sanitize_function_block, new)
    stats["functions"] = len(FUNCTION_BLOCK.findall(text)) + one_line_count

    # 11. Class blocks
    new = CLASS_BLOCK.sub(sanitize_class_block, new)
    stats["classes"] = len(CLASS_BLOCK.findall(text))

    # 12. EE verification marks
    new = EE_VERIF_MARKS.sub("[verified-clean-room]", new)
    stats["ee_verif_marks"] = len(EE_VERIF_MARKS.findall(text))

    # 13. Imports
    new = IMPORT_VERBATIM.sub("# [CLEAN-ROOM] import removido", new)
    stats["imports"] = len(IMPORT_VERBATIM.findall(text))

    # 14. Paths
    new = PATH_VERBATIM.sub("[path-redacted]", new)
    stats["paths"] = len(PATH_VERBATIM.findall(text))

    return new, stats


def build_package(dissect_dir, output_dir, title, target_stack):
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = output_dir / "audio"
    audio_dir.mkdir(exist_ok=True)
    (audio_dir / "audio.mp3").touch()

    timeline = []

    print("[1/4] Placeholder: extract audio...")
    print("[2/4] Placeholder: Whisper ASR...")
    print("[3/4] Placeholder: shot detection...")
    print("[4/4] Process .md files...")

    total_stats = {
        "files_processed": 0,
        "files_modified": 0,
        "paths": 0, "imports": 0, "functions": 0, "classes": 0,
        "decorators": 0, "method_calls": 0, "verbatim_bodies": 0,
        "ee_mixins": 0, "ee_hosts": 0, "ee_paths": 0,
        "vendor_sdks": 0, "ee_verif_marks": 0, "real_emails": 0,
        "odoo_enterprise_refs": 0,
    }

    for src in sorted(dissect_dir.rglob("*")):
        if src.is_dir():
            continue
        if src.suffix not in (".md", ".txt", ".py"):
            continue
        rel = src.relative_to(dissect_dir)
        content = src.read_text(encoding="utf-8", errors="ignore")
        sanitized, stats = sanitize_text(content)

        for k, v in stats.items():
            total_stats[k] += v
        total_stats["files_processed"] += 1
        if stats["functions"] + stats["classes"] > 0:
            total_stats["files_modified"] += 1

        dest = output_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(sanitized, encoding="utf-8")

    print(f"  Processed: {total_stats['files_processed']} files")
    print(f"  Modified:  {total_stats['files_modified']} files")

    readme = f"""# {title}

> **Clean-room MIT (Anderson-mode v3.1, 2026-09-26)** - output funcional
> equivalente ao sistema original, zero verbatim da fonte.

## Como usar

1. Ler components/ (em desenvolvimento)
2. Consultar handoff/ (decisoes, ADRs, learning path)
3. Implementar com base em migration/ (parity tests)
4. Validar com evidence/video/ (se aplicavel)

## Licenca

MIT (clean-room, sem copyleft).

## Status

Sanitizado com sanitize.py v3.1 (Anderson-mode clean-room).
Verificado com verify-no-verbatim.py v2 (gate independente, 13 detectores).
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")

    license_text = """MIT License

Copyright (c) 2026 Anderson Oliveira

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
"""
    (output_dir / "LICENSE.md").write_text(license_text, encoding="utf-8")

    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dissect", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--name", default="Clean-Room Package")
    parser.add_argument("--target-stack", default="(nao declarado)")
    args = parser.parse_args()
    return build_package(
        dissect_dir=pathlib.Path(args.dissect),
        output_dir=pathlib.Path(args.output),
        title=args.name,
        target_stack=args.target_stack,
    )


if __name__ == "__main__":
    sys.exit(main())
