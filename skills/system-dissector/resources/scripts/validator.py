"""Quality gates for system-dissector outputs.

Validates every artifact produced by the workflow (Phase 1 → 5) against
the canonical English templates in ``resources/templates/``. Detects
residual placeholders, broken links, hallucinated evidence, rubric
inconsistencies, and state/disk drift.

Subcommands:

* ``check <sistema>`` — full per-artifact validation; exit ``0`` ok,
  ``1`` errors, ``2`` warnings only.
* ``cross <sistema>`` — link integrity, orphan extraction docs,
  duplicate filenames.

Usage as a library::

    from validator import full_validation, cross_validate, ValidationResult

Usage from the shell::

    python validator.py check my-system
    python validator.py cross my-system
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dissect_utils import (
    VALID_TIPOS,
    DissectPaths,
    get_sistema_state,
    validate_sistema_name,
)

LOGGER = logging.getLogger("system-dissector.validator")


# ---------------------------------------------------------------------------
# Exit codes
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_WARNING = 2


# ---------------------------------------------------------------------------
# Canonical template expectations (English, matching the 12 templates)
# ---------------------------------------------------------------------------

# Phase 1 — triagem.md
TRIAGEM_REQUIRED_HEADINGS: tuple[str, ...] = (
    "Header",
    "1. Metadata",
    "2. High-level structure",
    "3. Statistics",
    "4. Initial risk assessment",
    "5. Deep-dive candidates",
    "6. Scope decisions",
    "7. Notes",
    "8. Phase 1 checklist",
)

# Phase 2 — deep-dive/architecture.md
DEEP_DIVE_ARCH_REQUIRED_HEADINGS: tuple[str, ...] = (
    "1. Stack overview",
    "2. Layered model",
    "3. C4 — Container view",
    "4. Process model",
    "5. Module loading / plugin model",
    "6. Request → response data flow",
    "7. Transactional model",
    "8. Cache invalidation strategy",
    "9. Multi-X concerns",
    "10. ORM / data-access internals",
    "11. Notes",
    "12. Phase 2 architecture checklist",
)

# Phase 2 — deep-dive/data-flows.md
DEEP_DIVE_FLOWS_REQUIRED_HEADINGS: tuple[str, ...] = (
    "1. Flow: typical read request",
    "2. Flow: authentication",
    "3. Flow: typical write / mutation",
    "4. Flow: background job",
    "6. Notes",
    "7. Data-flows checklist",
)

# Phase 2 — deep-dive/key-structures.md
DEEP_DIVE_STRUCTURES_REQUIRED_HEADINGS: tuple[str, ...] = (
    "1. Model overview",
    "2. Model details",
    "3. Inheritance & polymorphism",
    "4. Hot data structures",
    "5. Notes",
    "6. Key-structures checklist",
)

# Phase 2 — deep-dive/module-<name>.md (template line 6 / 309)
DEEP_DIVE_MODULE_REQUIRED_HEADINGS: tuple[str, ...] = (
    "1. Overview",
    "2. Domain models",
    "3. Controllers / handlers",
    "4. Views / serializers",
    "5. Dependencies",
    "6. Extendable points (inheritance / plugins)",
    "7. Public API surface",
    "8. Database schema",
    "9. Performance characteristics",
    "10. Security",
    "11. Portability assessment",
    "12. Notes",
    "13. Module deep-dive checklist",
)

# Phase 3 — wiki/index.md
WIKI_INDEX_REQUIRED_HEADINGS: tuple[str, ...] = (
    "Summary",
    "1. Architecture",
    "2. Modules catalog",
    "3. Extraction (Phase 4 output)",
    "5. Phase status",
    "6. Quick navigation (top 5 links)",
    "7. Glossary",
    "8. Index checklist",
)

# Phase 3 — wiki/c4-context.md
WIKI_C4_CONTEXT_REQUIRED_HEADINGS: tuple[str, ...] = (
    "1. System name",
    "2. Personae",
    "3. The system in scope",
    "4. External systems",
    "5. Context diagram",
    "6. Notes",
    "7. C4 context checklist",
)

# Phase 3 — wiki/c4-container.md
WIKI_C4_CONTAINER_REQUIRED_HEADINGS: tuple[str, ...] = (
    "1. Container overview",
    "2. Container details",
    "3. Data stores",
    "4. Communication patterns",
    "5. Container diagram",
    "6. Deployment topology",
    "7. Notes",
    "8. C4 container checklist",
)

# Phase 3 — wiki/modules.md
WIKI_MODULES_REQUIRED_HEADINGS: tuple[str, ...] = (
    "1. Top-level layout",
    "2. Standard module anatomy",
    "3. Category → modules map",
    "4. Inheritance & extension",
    "5. Dependencies (`depends`)",
    "6. How to find entrypoints",
    "7. Module tiers",
    "8. Reading order for new contributors",
    "9. Notes",
    "10. Modules navigation checklist",
)

# Phase 4 — extract/components.md
EXTRACT_COMPONENTS_REQUIRED_HEADINGS: tuple[str, ...] = (
    "1. Scoring rubric",
    "2. Scoring table",
    "3. Tier 1",
    "4. Tier 2",
    "5. Tier 3",
    "6. Executive recommendation",
    "7. Open questions",
    "8. Notes",
    "9. Extract-components checklist",
)

# Phase 4 — extract/patterns.md
EXTRACT_PATTERNS_REQUIRED_HEADINGS: tuple[str, ...] = (
    "1. Pattern summary",
    "2. Patterns (detailed)",
    "3. Pattern anti-portability notes",
    "4. Notes",
    "5. Extract-patterns checklist",
)

# Phase 4 — extract/algorithms.md
EXTRACT_ALGORITHMS_REQUIRED_HEADINGS: tuple[str, ...] = (
    "1. Algorithm catalog",
    "2. Algorithms (detailed)",
    "3. Crypto & hashing specifically",
    "4. Notes",
    "5. Extract-algorithms checklist",
)

# Phase 2 — required files inside deep-dive/
DEEP_DIVE_REQUIRED_FILES: tuple[str, ...] = (
    "architecture.md",
    "data-flows.md",
    "key-structures.md",
)

# Module file naming pattern (canonical, post-D4: module-<n>.md only)
# Legacy patterns (<name>-analysis.md, <name>-module.md) were removed —
# use dissect_utils.py migrate-modules to rename existing files.
MODULE_FILE_GLOBS: tuple[str, ...] = ("module-*.md",)


# ---------------------------------------------------------------------------
# C1-C6 rubric (canonical, matching extract-components.md.template lines 58-63)
# AND system-dissector SKILL.md:402
# ---------------------------------------------------------------------------

RUBRIC_CRITERIA: tuple[str, ...] = (
    "Compatibility",  # C1 — fit with the downstream target stack/idioms
    "Code quality",  # C2 — clean, tested, documented upstream
    "License compatibility",  # C3 — legal compatibility (LGPL/GPL/MIT/etc)
    "Maintenance velocity",  # C4 — active maintainers, recent commits, releases
    "Dependency footprint",  # C5 — extra deps added to the downstream stack
    "Reversibility",  # C6 — how easy to undo the port
)
RUBRIC_MAX_PER_CRITERION = 10
RUBRIC_TOTAL_MAX = 60

# Tier thresholds (template line 27): T1 ≥ 50, T2 40-49, T3 < 40.
TIER_THRESHOLDS: dict[str, tuple[int, int]] = {
    "T1": (50, 60),
    "T2": (40, 49),
    "T3": (0, 39),
}


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
# Markdown link — exclude image links (! prefix) and capture target.
_LINK_RE = re.compile(
    r"(?<!!)\[(?P<label>[^\]]+)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
)
_TABLE_ROW_RE = re.compile(r"^\|.+\|$", re.MULTILINE)
_SEPARATOR_ROW_RE = re.compile(r"^\|[\s\-:|]+\|$")
_CODE_FENCE_RE = re.compile(r"^```", re.MULTILINE)

# Residual template placeholder (lowercase tags from real templates).
# Skipped inside code fences by callers.
PLACEHOLDER_RE = re.compile(r"<[a-zA-Z][a-zA-Z0-9_./-]*>")

# file:line reference — used by anti-hallucination gate. Matches e.g.
# `addons/foo/models/x.py:123` and `config.json:42`. Ignores bare `<file:line>`
# placeholders (caught by PLACEHOLDER_RE) and `:123` (no path).
_FILE_LINE_REF_RE = re.compile(r"\b([\w./-]+\.\w+):(\d+)\b")

# `evidence: verified|estimated|partial` inline tag (case-insensitive).
_EVIDENCE_TAG_RE = re.compile(
    r"\bevidence\s*:\s*(verified|estimated|partial)\b", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Aggregate of errors, warnings, and info messages from one validation pass."""

    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Record a blocking error and flip ``passed`` to False."""
        self.passed = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Record a non-blocking warning."""
        self.warnings.append(message)

    def add_info(self, message: str) -> None:
        """Record an informational note."""
        self.info.append(message)

    def merge(self, other: "ValidationResult") -> None:
        """Combine another result into this one (in-place)."""
        self.passed = self.passed and other.passed
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.info.extend(other.info)

    def __str__(self) -> str:
        """Human-readable rendering."""
        status = "PASS" if self.passed else "FAIL"
        lines = [
            f"[{status}] {len(self.errors)} error(s), "
            f"{len(self.warnings)} warning(s), {len(self.info)} info"
        ]
        if self.errors:
            lines.append("Errors:")
            for msg in self.errors:
                lines.append(f"  - {msg}")
        if self.warnings:
            lines.append("Warnings:")
            for msg in self.warnings:
                lines.append(f"  - {msg}")
        if self.info:
            lines.append("Info:")
            for msg in self.info:
                lines.append(f"  - {msg}")
        return "\n".join(lines)


@dataclass
class CrossReferenceIssue:
    """Broken or orphan cross-reference discovered during traversal."""

    source_file: Path
    target: str
    reason: str

    def __str__(self) -> str:
        return f"{self.source_file}: broken ref '{self.target}' ({self.reason})"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _strip_code_fences(body: str) -> str:
    """Remove fenced code blocks from a markdown body.

    Returns the markdown with fenced code blocks removed, so heading,
    table, and link detection ignores their contents.
    """
    lines = body.splitlines()
    out: list[str] = []
    in_fence = False
    for line in lines:
        if _CODE_FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def _heading_texts(body: str) -> list[str]:
    """Return all heading texts (without ``#`` prefix) in document order."""
    return [m.group(2).strip() for m in _HEADING_RE.finditer(body)]


def _missing_headings(body: str, required: Iterable[str]) -> list[str]:
    """Return required headings absent from ``body`` (case-insensitive).

    Matches on the full heading line (including any ``N. `` section
    prefix). This prevents ambiguity when multiple templates share a
    bare heading like ``Notes``.
    """
    seen = " ".join(h.lower() for h in _heading_texts(body))
    return [h for h in required if h.lower() not in seen]


def _word_count(body: str) -> int:
    """Approximate word count excluding markdown noise."""
    cleaned = re.sub(r"[#*`>|]", " ", body)
    cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return len(cleaned.split())


def _strip_anchor(target: str) -> str:
    """Strip the trailing anchor from a link target (e.g. ``./foo.md#x``)."""
    return target.split("#", 1)[0]


def _strip_query(target: str) -> str:
    """Strip the trailing query string from a link target."""
    return target.split("?", 1)[0]


def _placeholder_residues(body: str) -> list[str]:
    """Return residual template placeholders found outside code fences."""
    return sorted(set(PLACEHOLDER_RE.findall(_strip_code_fences(body))))


def _detect_evidence(body: str) -> bool:
    """Return True if body has an explicit ``Evidence`` section or tag."""
    if re.search(r"^#{1,6}\s+Evidence\s*$", body, re.MULTILINE | re.IGNORECASE):
        return True
    if re.search(r"^#{1,6}\s+Evidência\s*$", body, re.MULTILINE | re.IGNORECASE):
        return True
    return bool(_EVIDENCE_TAG_RE.search(body))


# Anti-hallucination gate thresholds (Ação #4).
# Below ESTIMATED_ONLY_ERROR_PCT of `[estimated]` on a source tipo → ERROR.
ESTIMATED_ONLY_ERROR_PCT: int = 80
# Below this pct of ANY tagging (verified + estimated) → WARN (untagged reference).
UNTAGGED_REFS_WARN_PCT: int = 0
# Below this pct of `[verified]` references → WARN (output too speculative).
VERIFIED_MIN_INFO_PCT: int = 50


def _tag_refs_in_window(content: str, refs: list[tuple[str, str]]) -> tuple[int, int]:
    """For each (path, line) reference, look for [verified]/[estimated] nearby.

    Strategy: classify a ref as ``verified`` or ``estimated`` only if the
    tag appears on the **same line** as the reference. Tags on neighbouring
    lines belong to other refs and must not bleed into the count.

    Args:
        content: Markdown text the refs were extracted from (must match the
            string ``_FILE_LINE_REF_RE.finditer`` was run against, otherwise
            match offsets drift).
        refs: List of (path, line) tuples from ``_FILE_LINE_REF_RE.findall``.

    Returns:
        Tuple ``(estimated_count, verified_count)`` covering all refs that
        were tagged on the same line. Untagged refs are dropped from both
        counts.
    """
    if not refs:
        return 0, 0
    estimated = 0
    verified = 0
    matches = list(_FILE_LINE_REF_RE.finditer(content))
    for match, _ref in zip(matches, refs):
        # Find the bounds of the current line.
        line_start = content.rfind("\n", 0, match.start()) + 1
        line_end = content.find("\n", match.end())
        if line_end == -1:
            line_end = len(content)
        line = content[line_start:line_end]
        if re.search(r"\[verified\]", line, re.IGNORECASE):
            verified += 1
        elif re.search(r"\[estimated\]", line, re.IGNORECASE):
            estimated += 1
    return estimated, verified


def check_evidence(content: str, file_path: Path | None = None) -> ValidationResult:
    """Validate that evidence is declared explicitly and consistently.

    Ação #4 anti-hallucination gate. Runs in three layers:

    1. **Section gate** — if the body references ``file:line`` paths but has
       no ``## Evidence`` heading, emit a WARNING (missing declaration).
    2. **Per-reference gate** — for every ``file:line`` reference, look for
       an ``[verified]`` or ``[estimated]`` marker within a window of
       ~80 chars. If 0% of references are tagged, emit WARNING (high
       hallucination risk).
    3. **Source-grounded gate** — when ``file_path`` resolves to a
       triagem.md whose **Target Type** is ``source``, and >80% of tagged
       refs are ``[estimated]``, emit ERROR (output should be grounded
       against the real source code, not speculated).

    Args:
        content: Raw markdown body.
        file_path: Optional path to the artifact being validated; used to
            promote the source-grounded check when known.

    Returns:
        ValidationResult with errors / warnings / info populated.
    """
    result = ValidationResult()
    if not content.strip():
        return result  # Empty files are handled by per-phase validators.

    outside = _strip_code_fences(content)
    refs = _FILE_LINE_REF_RE.findall(outside)
    has_evidence = _detect_evidence(content)

    # Layer 1 — section gate.
    if refs and not has_evidence:
        result.add_warning(
            f"contains {len(refs)} file:line reference(s) but no "
            "'## Evidence' section — anti-hallucination gate (verify against clone)"
        )

    # Layer 2 — per-reference gate.
    if refs:
        # Pass ``outside`` (code-fence-stripped) so match offsets line up
        # with the ``refs`` extracted from ``outside``.
        estimated, verified = _tag_refs_in_window(outside, refs)
        tagged = estimated + verified
        untagged = len(refs) - tagged
        untagged_pct = (untagged / len(refs)) * 100 if refs else 0
        if untagged_pct > UNTAGGED_REFS_WARN_PCT:
            result.add_warning(
                f"{untagged}/{len(refs)} file:line references are untagged "
                f"({untagged_pct:.0f}%); high hallucination risk — "
                "mark each with [verified] or [estimated]"
            )
        verified_pct = (verified / len(refs)) * 100 if refs else 0
        if tagged > 0 and verified_pct < VERIFIED_MIN_INFO_PCT:
            result.add_info(
                f"only {verified}/{len(refs)} references are [verified] "
                f"({verified_pct:.0f}%); consider grounding more against the clone"
            )
        if tagged > 0:
            result.add_info(
                f"evidence coverage: {verified} verified, {estimated} estimated, "
                f"{untagged} untagged (of {len(refs)} refs)"
            )

        # Layer 3 — source-grounded gate (only when triagem.md is reachable).
        if file_path is not None:
            triagem_path = _resolve_triagem_path(file_path)
            if triagem_path is not None and triagem_path.exists():
                tipo = _detect_tipo_from_triagem(triagem_path)
                if tipo == "source" and tagged > 0:
                    estimated_pct = (estimated / tagged) * 100
                    if estimated_pct > ESTIMATED_ONLY_ERROR_PCT:
                        result.add_error(
                            f"{estimated_pct:.0f}% of tagged references are "
                            "[estimated] on a source-type target — re-dissect "
                            "with clone present to ground the output"
                        )

    return result


def _resolve_triagem_path(file_path: Path) -> Path | None:
    """Walk up from ``file_path`` to find the system's ``triagem.md``.

    Args:
        file_path: Path to an artifact inside a dissect directory.

    Returns:
        Path to triagem.md if found, else None.
    """
    parent = file_path.parent
    for _ in range(5):  # walk up to 5 levels
        candidate = parent / "triagem.md"
        if candidate.exists():
            return candidate
        if parent.parent == parent:
            break
        parent = parent.parent
    return None


def _detect_tipo_from_triagem(triagem_path: Path) -> str | None:
    """Extract **Target Type** value from a triagem.md.

    Args:
        triagem_path: Path to triagem.md.

    Returns:
        Lowercased tipo string (e.g. ``"source"``), or None if not declared.
    """
    try:
        body = triagem_path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(
        r"\*\*Target Type\*\*\s*\|\s*`?(\w+(?:[/\-:]\w+)*)`?", body, re.IGNORECASE
    )
    if match is None:
        return None
    head = match.group(1).lower().split(":", 1)[0]
    return head


def _check_evidence_rule(
    content: str, label: str, result: ValidationResult, file_path: Path | None = None
) -> None:
    """Merge :func:`check_evidence` results into ``result``.

    Internal helper used by per-phase validators to keep their signatures
    unchanged while delegating the real logic to ``check_evidence``.
    """
    sub = check_evidence(content, file_path=file_path)
    for msg in sub.errors:
        result.add_error(f"{label}: {msg}")
    for msg in sub.warnings:
        result.add_warning(f"{label}: {msg}")
    for msg in sub.info:
        result.add_info(f"{label}: {msg}")


def _count_patterns(body: str) -> int:
    """Count `## Pattern <n> — <name>` headings in a patterns catalog body.

    Heading must match ``^## Pattern <digits> `` (case-sensitive). Returns
    zero when the body is empty or has no matching headings. Code fences
    are not stripped — patterns nested inside example blocks are not
    counted (intentional: we only want real entries).
    """
    return sum(
        1
        for line in body.splitlines()
        if line.startswith("## Pattern ") and len(line) > len("## Pattern ")
    )


def _count_adrs(body: str) -> int:
    """Count `## ADR-<NNN>` headings in a decisions body.

    Heading must start with ``## ADR-`` and contain at least one digit.
    """
    n = 0
    for line in body.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith("## ADR-"):
            continue
        suffix = stripped[len("## ADR-") :].strip()
        if not suffix:
            continue
        # Take the first token; it should be the numeric id (e.g. "001").
        first = suffix.split()[0]
        digits = first.lstrip("0").lstrip("-")
        if digits.isdigit():
            n += 1
    return n


def _check_source_grounded_evidence(
    content: str, file_path: Path, label: str, result: ValidationResult
) -> None:
    """Run only the layer-3 (source-grounded) check.

    Used by :func:`full_validation` after the per-phase validators finish,
    so the same body is checked twice when full_validation runs: once by
    the per-phase validator (layers 1+2, no path) and once here with the
    real artifact path (layer 3). Layer 3 emits ERROR only when the target
    tipo is ``source`` and >80% of tagged refs are ``[estimated]``.

    Args:
        content: Raw markdown body.
        file_path: Path to the artifact on disk.
        label: Human-readable label for messages.
        result: ValidationResult to merge into.
    """
    triagem_path = _resolve_triagem_path(file_path)
    if triagem_path is None:
        return
    tipo = _detect_tipo_from_triagem(triagem_path)
    if tipo != "source":
        return
    # Only layer-3 logic: count estimated vs total tagged and warn/error
    # on the source-grounded threshold.
    outside = _strip_code_fences(content)
    refs = _FILE_LINE_REF_RE.findall(outside)
    if not refs:
        return
    estimated, verified = _tag_refs_in_window(outside, refs)
    tagged = estimated + verified
    if tagged == 0:
        return
    estimated_pct = (estimated / tagged) * 100
    if estimated_pct > ESTIMATED_ONLY_ERROR_PCT:
        result.add_error(
            f"{label}: {estimated_pct:.0f}% of tagged file:line references are "
            "[estimated] on a source-type target — re-dissect with clone "
            "present to ground the output (Ação #4 anti-hallucination gate)"
        )
    elif estimated_pct > 50:
        result.add_warning(
            f"{label}: {estimated_pct:.0f}% of tagged refs are [estimated]; "
            "consider grounding more against the clone"
        )


def _expected_tier(total: int) -> str:
    """Return the tier label that matches ``total`` per the rubric thresholds."""
    if total >= TIER_THRESHOLDS["T1"][0]:
        return "T1"
    if total >= TIER_THRESHOLDS["T2"][0]:
        return "T2"
    return "T3"


# ---------------------------------------------------------------------------
# Phase 1 — triagem.md
# ---------------------------------------------------------------------------


def validate_triagem(content: str) -> ValidationResult:
    """Validate ``triagem.md`` against the canonical English template.

    Args:
        content: Raw markdown text.

    Returns:
        ValidationResult with errors/warnings/info populated.
    """
    result = ValidationResult()
    if not content.strip():
        result.add_error("triagem.md is empty")
        return result

    outside = _strip_code_fences(content)
    missing = _missing_headings(outside, TRIAGEM_REQUIRED_HEADINGS)
    for heading in missing:
        result.add_error(f"triagem.md missing required heading: '{heading}'")

    words = _word_count(outside)
    if words < 150:
        result.add_warning(f"triagem.md is short ({words} words); aim for 300+")
    else:
        result.add_info(f"triagem.md has {words} words")

    # Target Type declaration (template line 23).
    tipo_match = re.search(
        r"\*\*Target Type\*\*\s*\|\s*`?(\w+(?:[/\-:]\w+)*)`?", content, re.IGNORECASE
    )
    if tipo_match:
        tipo = tipo_match.group(1).lower()
        # Hybrid targets use the form "hybrid:list"
        head = tipo.split(":", 1)[0]
        if head not in VALID_TIPOS:
            result.add_error(f"declared Target Type '{tipo}' is not in {VALID_TIPOS}")
    else:
        result.add_warning("could not detect **Target Type** declaration")

    # License field (template line 26).
    if not re.search(r"\*\*License\*\*\s*\|", content, re.IGNORECASE):
        result.add_warning("triagem.md has no License field")

    # URL references.
    if not re.search(r"https?://", content):
        result.add_info("no URL references found in triagem.md")

    for ph in _placeholder_residues(content):
        result.add_warning(f"triagem.md has residual placeholder '{ph}'")

    _check_evidence_rule(content, "triagem.md", result)
    return result


# ---------------------------------------------------------------------------
# Phase 2 — deep-dive/architecture.md
# ---------------------------------------------------------------------------


def validate_deep_dive_architecture(content: str) -> ValidationResult:
    """Validate ``deep-dive/architecture.md`` against the template.

    Args:
        content: Raw markdown text.

    Returns:
        ValidationResult for architecture.md.
    """
    result = ValidationResult()
    if not content.strip():
        result.add_error("deep-dive/architecture.md is empty")
        return result

    outside = _strip_code_fences(content)
    missing = _missing_headings(outside, DEEP_DIVE_ARCH_REQUIRED_HEADINGS)
    for heading in missing:
        result.add_warning(f"architecture.md missing recommended heading: '{heading}'")

    words = _word_count(outside)
    if words < 600:
        result.add_warning(f"architecture.md is short ({words} words); aim for 1200+")
    else:
        result.add_info(f"architecture.md has {words} words")

    if "```mermaid" not in content:
        result.add_warning("architecture.md has no mermaid diagram (C4 Container view)")

    for ph in _placeholder_residues(content):
        result.add_warning(f"architecture.md has residual placeholder '{ph}'")

    _check_evidence_rule(content, "architecture.md", result)
    return result


# ---------------------------------------------------------------------------
# Phase 2 — deep-dive/data-flows.md
# ---------------------------------------------------------------------------


def validate_deep_dive_data_flows(content: str) -> ValidationResult:
    """Validate ``deep-dive/data-flows.md``.

    Args:
        content: Raw markdown text.

    Returns:
        ValidationResult for data-flows.md.
    """
    result = ValidationResult()
    if not content.strip():
        result.add_error("deep-dive/data-flows.md is empty")
        return result

    outside = _strip_code_fences(content)
    missing = _missing_headings(outside, DEEP_DIVE_FLOWS_REQUIRED_HEADINGS)
    for heading in missing:
        result.add_warning(f"data-flows.md missing recommended heading: '{heading}'")

    words = _word_count(outside)
    if words < 400:
        result.add_warning(f"data-flows.md is short ({words} words); aim for 800+")
    else:
        result.add_info(f"data-flows.md has {words} words")

    for ph in _placeholder_residues(content):
        result.add_warning(f"data-flows.md has residual placeholder '{ph}'")

    _check_evidence_rule(content, "data-flows.md", result)
    return result


# ---------------------------------------------------------------------------
# Phase 2 — deep-dive/key-structures.md
# ---------------------------------------------------------------------------


def validate_deep_dive_key_structures(content: str) -> ValidationResult:
    """Validate ``deep-dive/key-structures.md``.

    Args:
        content: Raw markdown text.

    Returns:
        ValidationResult for key-structures.md.
    """
    result = ValidationResult()
    if not content.strip():
        result.add_error("deep-dive/key-structures.md is empty")
        return result

    outside = _strip_code_fences(content)
    missing = _missing_headings(outside, DEEP_DIVE_STRUCTURES_REQUIRED_HEADINGS)
    for heading in missing:
        result.add_warning(
            f"key-structures.md missing recommended heading: '{heading}'"
        )

    words = _word_count(outside)
    if words < 400:
        result.add_warning(f"key-structures.md is short ({words} words); aim for 800+")
    else:
        result.add_info(f"key-structures.md has {words} words")

    for ph in _placeholder_residues(content):
        result.add_warning(f"key-structures.md has residual placeholder '{ph}'")

    _check_evidence_rule(content, "key-structures.md", result)
    return result


# ---------------------------------------------------------------------------
# Phase 2 — deep-dive/module-<name>.md
# ---------------------------------------------------------------------------


def _module_name_from_path(stem: str) -> str:
    """Return the module slug extracted from a module file stem."""
    for prefix in ("module-",):
        if stem.startswith(prefix):
            return stem[len(prefix) :]
    for suffix in ("-module", "-analysis"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def validate_deep_dive_module(content: str, module: str) -> ValidationResult:
    """Validate a single ``deep-dive/module-<name>.md`` file.

    Args:
        content: Raw markdown text.
        module: Module name being analysed.

    Returns:
        ValidationResult for the analysis.
    """
    result = ValidationResult()
    if not module or not re.match(r"^[a-z0-9][a-z0-9-]*$", module):
        result.add_error("module name must be kebab-case alphanumeric")

    if not content.strip():
        result.add_error(f"deep-dive/module-{module}.md is empty")
        return result

    outside = _strip_code_fences(content)
    missing = _missing_headings(outside, DEEP_DIVE_MODULE_REQUIRED_HEADINGS)
    for heading in missing:
        result.add_warning(
            f"module-{module}.md missing recommended heading: '{heading}'"
        )

    words = _word_count(outside)
    if words < 400:
        result.add_warning(f"module-{module}.md is short ({words} words); aim for 600+")
    else:
        result.add_info(f"module-{module}.md has {words} words")

    if "```" not in content:
        result.add_info(
            f"module-{module}.md has no code blocks; consider adding snippets"
        )

    for ph in _placeholder_residues(content):
        result.add_warning(f"module-{module}.md has residual placeholder '{ph}'")

    _check_evidence_rule(content, f"module-{module}.md", result)
    return result


def _collect_module_files(deep_dive: Path) -> list[Path]:
    """Return deduplicated, sorted module files matching known patterns."""
    seen: set[Path] = set()
    for pattern in MODULE_FILE_GLOBS:
        for candidate in deep_dive.glob(pattern):
            if candidate.is_file():
                seen.add(candidate.resolve())
    return sorted(seen)


# ---------------------------------------------------------------------------
# Phase 3 — wiki/index.md
# ---------------------------------------------------------------------------


def validate_wiki_index(content: str, paths: DissectPaths) -> ValidationResult:
    """Validate ``wiki/index.md`` including internal link correctness.

    Allows relative ``../`` links that stay within the dissect root;
    flags only links that escape the tree.

    Args:
        content: Body of wiki/index.md.
        paths: Resolved dissect paths.

    Returns:
        ValidationResult including broken-link warnings.
    """
    result = ValidationResult()
    if not content.strip():
        result.add_error("wiki/index.md is empty")
        return result

    outside = _strip_code_fences(content)
    missing = _missing_headings(outside, WIKI_INDEX_REQUIRED_HEADINGS)
    for heading in missing:
        result.add_warning(f"wiki/index.md missing recommended heading: '{heading}'")

    words = _word_count(outside)
    if words < 200:
        result.add_warning(f"wiki/index.md is short ({words} words); aim for 400+")

    if not re.search(r"Phase\s*1\s*[—–-]\s*Triage", content, re.IGNORECASE):
        result.add_warning(
            "wiki/index.md missing 'Phase 1 — Triage' row in status table"
        )

    dissect_root = paths.root.resolve()
    for match in _LINK_RE.finditer(outside):
        target = match.group("target").strip()
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target_path = _strip_query(_strip_anchor(target))
        if not target_path:
            continue
        # Resolve relative to the file containing the link.
        resolved = (paths.wiki / target_path).resolve()
        try:
            resolved.relative_to(dissect_root)
        except ValueError:
            result.add_warning(f"wiki/index.md link '{target}' escapes dissect root")
            continue
        if not resolved.exists():
            result.add_warning(
                f"wiki/index.md link '{target_path}' points at missing file"
            )

    for ph in _placeholder_residues(content):
        result.add_warning(f"wiki/index.md has residual placeholder '{ph}'")

    _check_evidence_rule(content, "wiki/index.md", result)
    return result


# ---------------------------------------------------------------------------
# Phase 3 — wiki/c4-context.md / wiki/c4-container.md / wiki/modules.md
# ---------------------------------------------------------------------------


def validate_wiki_c4_context(content: str) -> ValidationResult:
    """Validate ``wiki/c4-context.md``."""
    result = ValidationResult()
    if not content.strip():
        result.add_error("wiki/c4-context.md is empty")
        return result

    outside = _strip_code_fences(content)
    missing = _missing_headings(outside, WIKI_C4_CONTEXT_REQUIRED_HEADINGS)
    for heading in missing:
        result.add_warning(f"c4-context.md missing recommended heading: '{heading}'")

    if "```mermaid" not in content:
        result.add_warning(
            "c4-context.md has no mermaid diagram (Context diagram required)"
        )

    for ph in _placeholder_residues(content):
        result.add_warning(f"c4-context.md has residual placeholder '{ph}'")

    _check_evidence_rule(content, "c4-context.md", result)
    return result


def validate_wiki_c4_container(content: str) -> ValidationResult:
    """Validate ``wiki/c4-container.md``."""
    result = ValidationResult()
    if not content.strip():
        result.add_error("wiki/c4-container.md is empty")
        return result

    outside = _strip_code_fences(content)
    missing = _missing_headings(outside, WIKI_C4_CONTAINER_REQUIRED_HEADINGS)
    for heading in missing:
        result.add_warning(f"c4-container.md missing recommended heading: '{heading}'")

    if "```mermaid" not in content:
        result.add_warning(
            "c4-container.md has no mermaid diagram (Container diagram required)"
        )

    for ph in _placeholder_residues(content):
        result.add_warning(f"c4-container.md has residual placeholder '{ph}'")

    _check_evidence_rule(content, "c4-container.md", result)
    return result


def validate_wiki_modules(content: str) -> ValidationResult:
    """Validate ``wiki/modules.md``."""
    result = ValidationResult()
    if not content.strip():
        result.add_error("wiki/modules.md is empty")
        return result

    outside = _strip_code_fences(content)
    missing = _missing_headings(outside, WIKI_MODULES_REQUIRED_HEADINGS)
    for heading in missing:
        result.add_warning(f"modules.md missing recommended heading: '{heading}'")

    for ph in _placeholder_residues(content):
        result.add_warning(f"modules.md has residual placeholder '{ph}'")

    _check_evidence_rule(content, "modules.md", result)
    return result


# ---------------------------------------------------------------------------
# Phase 4 — extract/components.md
# ---------------------------------------------------------------------------


def validate_extract_components(content: str) -> ValidationResult:
    """Validate ``extract/components.md`` against the C1-C6 rubric.

    Checks:

    * Required section headings (English, matching template).
    * Rubric block lists C1..C6 with the canonical criterion names.
    * Scoring-table header has columns: ``Component``, ``C1..C6``,
      ``Total``, ``Tier``.
    * Each scoring row sums C1..C6 to its declared ``Total`` and tier
      matches the score.

    Args:
        content: Raw markdown text.

    Returns:
        ValidationResult for components.md.
    """
    result = ValidationResult()
    if not content.strip():
        result.add_error("extract/components.md is empty")
        return result

    outside = _strip_code_fences(content)
    missing = _missing_headings(outside, EXTRACT_COMPONENTS_REQUIRED_HEADINGS)
    for heading in missing:
        result.add_error(f"components.md missing required heading: '{heading}'")

    # Rubric block: heading "1. Scoring rubric (6 criteria × 0-10)" up to
    # "## 2." (or end of doc).
    rubric_match = re.search(
        r"^#{1,6}\s+1\.\s+Scoring rubric[\s\S]*?(?=^#{1,6}\s+2\.\s+|\Z)",
        content,
        re.MULTILINE,
    )
    if not rubric_match:
        result.add_error("components.md missing '1. Scoring rubric' section")
        return result

    rubric_block = rubric_match.group(0)
    for label, criterion in zip(("C1", "C2", "C3", "C4", "C5", "C6"), RUBRIC_CRITERIA):
        if not re.search(
            rf"\*\*{label}\*\*[\s\S]{{0,80}}?{re.escape(criterion)}",
            rubric_block,
            re.IGNORECASE,
        ):
            result.add_error(
                f"components.md rubric missing criterion {label} ({criterion})"
            )

    # Locate the scoring-table header row (must contain "Component", "C1",
    # and "Tier").
    scoring_header: Optional[str] = None
    for match in _TABLE_ROW_RE.finditer(content):
        line = match.group(0)
        lowered = line.lower()
        if "component" in lowered and "tier" in lowered and "c1" in lowered:
            scoring_header = line
            break

    if scoring_header is None:
        result.add_error(
            "components.md scoring table header missing one of: "
            "Component | C1 | C2 | C3 | C4 | C5 | C6 | Total | Tier"
        )
        return result

    lowered_header = scoring_header.lower()
    required_cols = [
        "Component",
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
        "C6",
        "Total",
        "Tier",
    ]
    for col in required_cols:
        if col.lower() not in lowered_header:
            result.add_error(
                f"components.md scoring table header missing column '{col}'"
            )

    # Validate each scoring row. Slice the content between the scoring
    # header and the next ``## 3.`` (Tier 1) heading so we don't sweep
    # tables from later sections.
    header_pos = content.find(scoring_header)
    if header_pos < 0:
        return result
    end_pattern = re.compile(r"^#{1,6}\s+3\.\s+", re.MULTILINE)
    end_match = end_pattern.search(content, header_pos + len(scoring_header))
    end_pos = end_match.start() if end_match else len(content)
    scoring_block = content[header_pos:end_pos]

    rows_seen = 0
    for line_match in _TABLE_ROW_RE.finditer(scoring_block):
        line = line_match.group(0)
        if line == scoring_header:
            continue
        if _SEPARATOR_ROW_RE.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # After ``strip("|").split("|")``: cells[0] = row number,
        # cells[1] = component name, cells[2..7] = C1..C6, cells[8] = Total,
        # cells[9] = Tier → 10 cells total.
        if len(cells) < 10:
            result.add_warning(
                f"components.md scoring row has {len(cells)} cells; expected 10"
            )
            continue
        component_name = cells[1]
        try:
            scores = [int(re.sub(r"\D", "", c) or 0) for c in cells[2:8]]
        except (ValueError, IndexError):
            continue
        summed = sum(scores)
        total_cell = cells[8]
        tier_cell = cells[9]
        rows_seen += 1

        declared_total_match = re.search(r"(\d+)\s*/\s*60", total_cell)
        if declared_total_match:
            declared = int(declared_total_match.group(1))
            # Bug fix: ``sumed`` → ``summed`` (was a latent NameError).
            if abs(declared - summed) > 1:
                result.add_warning(
                    f"components.md row '{component_name}': declared total "
                    f"{declared} != summed {summed}"
                )

        # Tier check runs independently of the ``xx/60`` total format.
        tier_token_match = re.search(r"\b(T[123])\b", tier_cell)
        if tier_token_match:
            declared_tier = tier_token_match.group(1)
            expected_tier = _expected_tier(summed)
            if declared_tier != expected_tier:
                result.add_warning(
                    f"components.md row '{component_name}': score "
                    f"{summed} → expected tier {expected_tier}, "
                    f"declared {declared_tier}"
                )

    if rows_seen == 0:
        result.add_warning("components.md scoring table has no data rows (header only)")

    # Tier section headers (3..5).
    for tier_no, tier_label in (("3", "Tier 1"), ("4", "Tier 2"), ("5", "Tier 3")):
        if not re.search(
            rf"^#{{1,6}}\s+{tier_no}\.\s+{re.escape(tier_label)}", content, re.MULTILINE
        ):
            result.add_warning(
                f"components.md missing '{tier_no}. {tier_label}' section header"
            )

    for ph in _placeholder_residues(content):
        result.add_warning(f"components.md has residual placeholder '{ph}'")

    _check_evidence_rule(content, "components.md", result)
    return result


# ---------------------------------------------------------------------------
# Phase 4 — extract/patterns.md
# ---------------------------------------------------------------------------


def _section_subheadings(content: str, section_heading: str) -> list[str]:
    """Return ``###``/``####`` subheading texts under ``section_heading``.

    Uses line-by-line scanning instead of multi-line regex to avoid
    zero-width match issues with the lookahead + lazy quantifier.

    Note: `\b` (word boundary) is omitted on purpose — section headings ending
    in punctuation like `(detailed)` have no word boundary after `)`, causing
    the regex to fail. We rely on exact prefix match instead.

    Args:
        content: Raw markdown text.
        section_heading: Exact heading text (e.g. "2. Patterns (detailed)").

    Returns:
        List of subheading texts (without ``#`` markers).
    """
    lines = content.split("\n")
    section_lines: list[str] = []
    in_section = False
    for line in lines:
        # Start of section (matches ##, ###, #### with the heading text)
        # No \b — relies on exact prefix match to avoid word-boundary issues with punctuation
        if re.match(rf"^#{{1,6}}\s+{re.escape(section_heading)}", line):
            in_section = True
            continue
        # End of section (next top-level numbered heading like "## 3.")
        if in_section and re.match(r"^#{1,6}\s+\d+\.\s+", line):
            break
        if in_section:
            section_lines.append(line)
    # Find ### or #### subheadings within section
    return re.findall(r"^#{3,4}\s+(.+?)\s*$", "\n".join(section_lines), re.MULTILINE)


def validate_extract_patterns(content: str) -> ValidationResult:
    """Validate ``extract/patterns.md`` (must list at least 5 patterns).

    Args:
        content: Raw markdown text.

    Returns:
        ValidationResult for patterns.md.
    """
    result = ValidationResult()
    if not content.strip():
        result.add_error("extract/patterns.md is empty")
        return result

    outside = _strip_code_fences(content)
    missing = _missing_headings(outside, EXTRACT_PATTERNS_REQUIRED_HEADINGS)
    for heading in missing:
        result.add_warning(f"patterns.md missing recommended heading: '{heading}'")

    patterns = _section_subheadings(content, "2. Patterns (detailed)")
    if len(patterns) < 5:
        result.add_error(
            f"patterns.md has {len(patterns)} pattern(s) under section 2; "
            f"need at least 5"
        )
    else:
        result.add_info(f"patterns.md documents {len(patterns)} patterns")

    if "```" not in content:
        result.add_warning("patterns.md has no code snippets")

    for ph in _placeholder_residues(content):
        result.add_warning(f"patterns.md has residual placeholder '{ph}'")

    _check_evidence_rule(content, "patterns.md", result)
    return result


# ---------------------------------------------------------------------------
# Phase 4 — extract/algorithms.md
# ---------------------------------------------------------------------------


def validate_extract_algorithms(content: str) -> ValidationResult:
    """Validate ``extract/algorithms.md`` (must list at least 5 algorithms).

    Args:
        content: Raw markdown text.

    Returns:
        ValidationResult for algorithms.md.
    """
    result = ValidationResult()
    if not content.strip():
        result.add_error("extract/algorithms.md is empty")
        return result

    outside = _strip_code_fences(content)
    missing = _missing_headings(outside, EXTRACT_ALGORITHMS_REQUIRED_HEADINGS)
    for heading in missing:
        result.add_warning(f"algorithms.md missing recommended heading: '{heading}'")

    algorithms = _section_subheadings(content, "2. Algorithms (detailed)")
    if len(algorithms) < 5:
        result.add_error(
            f"algorithms.md has {len(algorithms)} algorithm(s) under section 2; "
            f"need at least 5"
        )
    else:
        result.add_info(f"algorithms.md documents {len(algorithms)} algorithms")

    for ph in _placeholder_residues(content):
        result.add_warning(f"algorithms.md has residual placeholder '{ph}'")

    _check_evidence_rule(content, "algorithms.md", result)
    return result


# ---------------------------------------------------------------------------
# Aggregation & cross-validation
# ---------------------------------------------------------------------------


def _phase_status_for(paths: DissectPaths, phase_no: int) -> str:
    """Return the phase status from state.json (``pending`` when absent)."""
    state = get_sistema_state(paths.sistema)
    if state is None:
        return "pending"
    return state.phase_status.get(phase_no, "pending")


def full_validation(sistema: str) -> ValidationResult:
    """Run every per-phase validator for ``sistema``.

    Phase-aware severity: when ``state.json`` marks a phase ``completed``,
    a missing artifact is an **error**; for ``pending`` or
    ``in_progress`` phases it is a warning. This closes the gap where
    a dissect could pass with exit ``0`` while being empty.

    Args:
        sistema: Kebab-case system name.

    Returns:
        Aggregated ValidationResult covering all phases present.
    """
    sistema = validate_sistema_name(sistema)
    paths = DissectPaths.for_sistema(sistema)
    result = ValidationResult()

    if not paths.root.exists():
        result.add_error(f"dissect root missing: {paths.root}")
        return result

    state = get_sistema_state(sistema)
    if state is None:
        result.add_warning(f"no state.json found for {sistema}")

    def _missing(artifact: str, phase_no: int) -> None:
        status = _phase_status_for(paths, phase_no)
        if status == "completed":
            result.add_error(
                f"{artifact} missing (phase {phase_no} marked completed in state.json)"
            )
        else:
            result.add_warning(
                f"{artifact} missing (phase {phase_no} status: {status})"
            )

    # Phase 1 — triagem
    if paths.triagem.exists():
        body = paths.triagem.read_text(encoding="utf-8")
        result.merge(validate_triagem(body))
        _check_source_grounded_evidence(body, paths.triagem, "triagem.md", result)
    else:
        _missing("triagem.md", 1)

    # Phase 2 — deep-dive
    if paths.deep_dive.exists():
        for fname in DEEP_DIVE_REQUIRED_FILES:
            fpath = paths.deep_dive / fname
            if fpath.exists():
                body = fpath.read_text(encoding="utf-8")
                if fname == "architecture.md":
                    result.merge(validate_deep_dive_architecture(body))
                elif fname == "data-flows.md":
                    result.merge(validate_deep_dive_data_flows(body))
                elif fname == "key-structures.md":
                    result.merge(validate_deep_dive_key_structures(body))
                _check_source_grounded_evidence(
                    body, fpath, f"deep-dive/{fname}", result
                )
            else:
                _missing(f"deep-dive/{fname}", 2)

        module_files = _collect_module_files(paths.deep_dive)
        if not module_files:
            status = _phase_status_for(paths, 2)
            if status == "completed":
                result.add_error(
                    "deep-dive/ has no module-*.md files (phase 2 completed)"
                )
            else:
                result.add_warning("deep-dive/ has no module-*.md files")
        for mod_file in module_files:
            module_name = _module_name_from_path(mod_file.stem)
            body = mod_file.read_text(encoding="utf-8")
            result.merge(validate_deep_dive_module(body, module_name))
            _check_source_grounded_evidence(
                body, mod_file, f"deep-dive/{mod_file.name}", result
            )
    else:
        _missing("deep-dive/", 2)

    # Phase 3 — wiki
    if paths.wiki.exists():
        wiki_index = paths.wiki / "index.md"
        if wiki_index.exists():
            body = wiki_index.read_text(encoding="utf-8")
            result.merge(validate_wiki_index(body, paths))
            _check_source_grounded_evidence(body, wiki_index, "wiki/index.md", result)
        else:
            _missing("wiki/index.md", 3)

        for fname, validator in (
            ("architecture/c4-context.md", validate_wiki_c4_context),
            ("architecture/c4-container.md", validate_wiki_c4_container),
            ("modules/addons.md", validate_wiki_modules),
        ):
            fpath = paths.wiki / fname
            if fpath.exists():
                body = fpath.read_text(encoding="utf-8")
                result.merge(validator(body))
                _check_source_grounded_evidence(body, fpath, f"wiki/{fname}", result)
            else:
                status = _phase_status_for(paths, 3)
                if status == "completed":
                    result.add_error(f"wiki/{fname} missing (phase 3 marked completed)")
                else:
                    result.add_info(f"wiki/{fname} not present (recommended)")
    else:
        _missing("wiki/", 3)

    # Phase 4 — extract
    if paths.extract.exists():
        for fname, validator in (
            ("components.md", validate_extract_components),
            ("patterns.md", validate_extract_patterns),
            ("algorithms.md", validate_extract_algorithms),
        ):
            fpath = paths.extract / fname
            if fpath.exists():
                body = fpath.read_text(encoding="utf-8")
                result.merge(validator(body))
                _check_source_grounded_evidence(body, fpath, f"extract/{fname}", result)
            else:
                _missing(f"extract/{fname}", 4)
    else:
        _missing("extract/", 4)

    # Phase 5 — HANDOFF (stack-agnostic; required)
    handoff_files = (
        ("README.md", "handoff entry point (index of the 6 artifacts)"),
        ("learning-path.md", "pedagogical trail"),
        ("implementation-guide.md", "clean-room recipe per Tier 1"),
        ("patterns-catalog.md", "≥5 patterns with generic usage examples"),
        ("decisions.md", "≥3 ADRs (MADR-style) with file:line cross-refs"),
        ("reuse-checklist.md", "explicit decision per Tier 1/2 component"),
        ("components-priority.md", "ranking + roadmap"),
    )
    handoff_dir = paths.handoff
    if not handoff_dir.exists():
        result.add_error("handoff/ directory missing (Phase 5 required)")
    else:
        for fname, why in handoff_files:
            path = handoff_dir / fname
            if not path.exists():
                result.add_error(f"handoff/{fname} missing — {why}")
                continue
            body = path.read_text(encoding="utf-8")
            for ph in _placeholder_residues(body):
                result.add_warning(f"handoff/{fname} has residual placeholder '{ph}'")
            _check_evidence_rule(body, f"handoff/{fname}", result)
            _check_source_grounded_evidence(body, path, f"handoff/{fname}", result)

        # Quality gate: ≥ 5 patterns catalogued
        catalog = handoff_dir / "patterns-catalog.md"
        if catalog.exists():
            body = catalog.read_text(encoding="utf-8")
            n_patterns = _count_patterns(body)
            if n_patterns < 5:
                result.add_error(
                    f"handoff/patterns-catalog.md has {n_patterns} patterns; "
                    "minimum is 5"
                )

        # Quality gate: ≥ 3 ADRs in decisions.md
        decisions = handoff_dir / "decisions.md"
        if decisions.exists():
            body = decisions.read_text(encoding="utf-8")
            n_adrs = _count_adrs(body)
            if n_adrs < 3:
                result.add_error(
                    f"handoff/decisions.md has {n_adrs} ADRs; minimum is 3"
                )

    # Phase 5b — INTEGRATE specific (OPT-IN via companion skill)
    integrate_md = paths.integrate_neoai / "integrate.md"
    if paths.integrate_neoai.exists():
        if integrate_md.exists():
            body = integrate_md.read_text(encoding="utf-8")
            for ph in _placeholder_residues(body):
                result.add_warning(
                    f"integrate-neoai/integrate.md has residual placeholder '{ph}'"
                )
            _check_evidence_rule(body, "integrate-neoai/integrate.md", result)
            _check_source_grounded_evidence(
                body, integrate_md, "integrate-neoai/integrate.md", result
            )
        else:
            result.add_info(
                "integrate-neoai/ exists but integrate.md missing — "
                "OPT-IN Phase 5b incomplete"
            )
    # Phase 5b is opt-in; absence is fine (just an info note)
    else:
        result.add_info(
            "integrate-neoai/ not present (Phase 5b OPT-IN — "
            "only required if a destination-specific companion was run)"
        )

    return result


def cross_validate(sistema: str) -> list[CrossReferenceIssue]:
    """Walk the dissect tree looking for broken cross-references and orphans.

    Args:
        sistema: Kebab-case system name.

    Returns:
        List of CrossReferenceIssue objects; empty list when healthy.
    """
    sistema = validate_sistema_name(sistema)
    paths = DissectPaths.for_sistema(sistema)
    issues: list[CrossReferenceIssue] = []

    if not paths.root.exists():
        issues.append(
            CrossReferenceIssue(
                source_file=paths.root,
                target="<root>",
                reason="dissect root does not exist",
            )
        )
        return issues

    dissect_root_resolved = paths.root.resolve()
    markdown_files = sorted(p for p in paths.root.rglob("*.md") if p.is_file())

    # 1. Broken markdown links — allow ../ within dissect root.
    for md_file in markdown_files:
        try:
            body = md_file.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(
                CrossReferenceIssue(
                    source_file=md_file,
                    target="<read>",
                    reason=f"failed to read: {exc}",
                )
            )
            continue
        outside = _strip_code_fences(body)
        for match in _LINK_RE.finditer(outside):
            target = match.group("target").strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target_path_str = _strip_query(_strip_anchor(target))
            if not target_path_str:
                continue
            resolved = (md_file.parent / target_path_str).resolve()
            try:
                resolved.relative_to(dissect_root_resolved)
            except ValueError:
                issues.append(
                    CrossReferenceIssue(
                        source_file=md_file,
                        target=target,
                        reason="target escapes dissect root",
                    )
                )
                continue
            if not resolved.exists():
                issues.append(
                    CrossReferenceIssue(
                        source_file=md_file,
                        target=target,
                        reason="target file does not exist",
                    )
                )

    # 2. Orphan extract docs: extract/*.md not linked from any wiki/*.md.
    wiki_link_targets: set[str] = set()
    if paths.wiki.exists():
        for wiki_md in paths.wiki.rglob("*.md"):
            try:
                txt = wiki_md.read_text(encoding="utf-8")
            except OSError:
                continue
            outside = _strip_code_fences(txt)
            for match in _LINK_RE.finditer(outside):
                raw = match.group("target").strip()
                t = _strip_query(_strip_anchor(raw))
                wiki_link_targets.add(t)
                wiki_link_targets.add(Path(t).name)

    if paths.extract.exists():
        for extract_md in paths.extract.rglob("*.md"):
            rel = extract_md.relative_to(paths.extract).as_posix()
            filename = extract_md.name
            referenced = any(
                link.endswith(filename) or link.endswith(rel) or filename in link
                for link in wiki_link_targets
            )
            if not referenced:
                issues.append(
                    CrossReferenceIssue(
                        source_file=(
                            paths.wiki / "index.md"
                            if paths.wiki.exists()
                            else extract_md
                        ),
                        target=filename,
                        reason="orphan extract doc not cited from wiki",
                    )
                )

    # 3. Duplicate filenames in the same directory (naming-drift guard).
    by_dir: dict[Path, list[str]] = {}
    for md_file in markdown_files:
        by_dir.setdefault(md_file.parent, []).append(md_file.name)
    for parent, names in by_dir.items():
        if len(names) != len(set(names)):
            issues.append(
                CrossReferenceIssue(
                    source_file=parent,
                    target="<dir>",
                    reason=f"duplicate filenames in "
                    f"{parent.relative_to(dissect_root_resolved)}: "
                    f"{sorted(n for n in set(names) if names.count(n) > 1)}",
                )
            )

    return issues


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_check(args: argparse.Namespace) -> int:
    """CLI handler for ``check``: run :func:`full_validation`."""
    sistema = validate_sistema_name(args.sistema)
    result = full_validation(sistema)
    print(str(result))
    if result.errors:
        return EXIT_ERROR
    if result.warnings:
        return EXIT_WARNING
    return EXIT_OK


def _cmd_cross(args: argparse.Namespace) -> int:
    """CLI handler for ``cross``: run :func:`cross_validate`."""
    sistema = validate_sistema_name(args.sistema)
    issues = cross_validate(sistema)
    if not issues:
        print(f"{sistema}: no broken references")
        return EXIT_OK
    print(f"{sistema}: {len(issues)} issue(s)")
    for issue in issues:
        print(f"  - {issue}")
    return EXIT_ERROR


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the validator CLI."""
    parser = argparse.ArgumentParser(
        prog="validator",
        description="Quality gates for system-dissector outputs.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="enable DEBUG logging"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="validate every artifact for a sistema")
    p_check.add_argument("sistema", help="kebab-case system name")
    p_check.set_defaults(func=_cmd_check)

    p_cross = sub.add_parser(
        "cross", help="cross-reference validation (links, orphans, dups)"
    )
    p_cross.add_argument("sistema", help="kebab-case system name")
    p_cross.set_defaults(func=_cmd_cross)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
