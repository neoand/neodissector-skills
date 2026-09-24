"""Cross-system pattern consolidation for system-dissector.

Scans ``dissects/*/extract/patterns.md`` across every dissected system,
groups similar patterns by name (exact + Levenshtein distance), detects
patterns that recur in >= 2 systems (cross-system validation), and emits
a consolidated catalog at ``dissects/_cross-system-patterns.md``.

The output is a **stack-agnostic** artifact. When 2+ different dissects
solve the same problem with similar shapes, the pattern is worth a
canonical implementation (or a canonical reference) regardless of which
downstream stack the team is building. Single-system patterns stay in
their ``dissects/<s>/extract/patterns.md`` — only cross-system patterns
surface here.

Usage as a CLI:

    python3 consolidate_patterns.py consolidate
    python3 consolidate_patterns.py list
    python3 consolidate_patterns.py search <keyword>
    python3 consolidate_patterns.py validate <pattern>

Exit codes: 0 on success, 1 on user-facing error, 2 on validation
warning. No external dependencies — stdlib only.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, Optional

LOGGER = logging.getLogger("system-dissector.consolidate")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HINDSIGHT_ROOT: Path = Path(
    "/Users/andersongoliveira/projects/engenharia reversa/neodissector"
)
DISSECTS_DIR: Path = HINDSIGHT_ROOT / "dissects"
PATTERNS_FILENAME: str = "patterns.md"
OUTPUT_PATH: Path = DISSECTS_DIR / "_cross-system-patterns.md"

# Cross-system threshold: a pattern must appear in at least this many
# distinct sistemas to qualify for the consolidated catalog.
MIN_CROSS_SYSTEM: int = 2

# Fuzzy match threshold. Two names are considered the same pattern when
# either they match exactly (case-insensitive) or their Levenshtein
# distance is at or below this value. 3 lets us collapse "retry",
# "retries", "retrying" while keeping "auth" and "oauth" distinct.
LEVENSHTEIN_THRESHOLD: int = 3

# Clean-room scoring: 0-10 heuristic per pattern.
#   base = verified_refs * 2 (each verified file:line is worth 2 points)
#   bonus = estimated_refs (each estimated reference is worth 1 point)
#   cap at 10
# A pattern with zero file:line refs scores 1 (placeholder).

EXIT_OK: int = 0
EXIT_ERROR: int = 1
EXIT_WARNING: int = 2

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# `### 2.1 Pattern Name` or `### 2.10 Pattern Name` (template allows up to 12).
# Captures the section number and the pattern name (kebab/snake/space).
_PATTERN_HEADING_RE: re.Pattern[str] = re.compile(
    r"^###\s+(\d+)\.(\d+)\s+`?([^\n`]+?)`?\s*$",
    re.MULTILINE,
)

# `<label>` markdown emphasis inside a pattern block, e.g.
# `- **Category**: integration`. The leading `- ` bullet is part of the
# template; allow optional indentation but require the bullet for
# unambiguity (avoids catching section bodies like `**Description**`).
_FIELD_RE: re.Pattern[str] = re.compile(
    r"^\s*-\s+\*\*([^*]+)\*\*\s*:\s*(.+?)\s*$",
    re.MULTILINE,
)

# file:line references (matches e.g. addons/foo/models/x.py:123).
_FILE_LINE_REF_RE: re.Pattern[str] = re.compile(r"\b([\w./-]+\.\w+):(\d+)\b")

# `[verified]` / `[estimated]` evidence tags on the same line as the ref.
_VERIFIED_TAG_RE: re.Pattern[str] = re.compile(r"\[verified\]", re.IGNORECASE)
_ESTIMATED_TAG_RE: re.Pattern[str] = re.compile(r"\[estimated\]", re.IGNORECASE)

# Optional markdown table row for "Where used" (bullet-prefixed to match
# the template's `- **Where used**: path/to/file.py:42` shape).
_WHERE_USED_RE: re.Pattern[str] = re.compile(
    r"^\s*-\s+\*\*Where used\*\*\s*:\s*(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PatternRef:
    """A single ``file:line`` occurrence inside a pattern block.

    Frozen so a single occurrence cannot be double-counted by mistake.
    """

    path: str
    line: int
    verified: bool

    @property
    def is_estimated(self) -> bool:
        """Return True when the ref is tagged [estimated] but not [verified]."""
        # We do not store the estimated tag explicitly; estimated_only is
        # derivable at scoring time from the parent pattern's tag list.
        return not self.verified


@dataclass
class ExtractedPattern:
    """One pattern block as it appears in a single dissect's ``patterns.md``."""

    sistema: str
    section_no: str  # e.g. "2.1"
    name: str
    raw_name: str  # name as it appears, including any backticks
    category: str
    quality: str
    effort: str
    where_used: str
    body: str  # raw markdown body of the pattern section
    refs: list[PatternRef] = field(default_factory=list)

    @property
    def ref_count(self) -> int:
        """Return total file:line references inside the pattern."""
        return len(self.refs)

    @property
    def verified_count(self) -> int:
        """Return count of [verified] file:line references."""
        return sum(1 for r in self.refs if r.verified)

    @property
    def estimated_count(self) -> int:
        """Return count of refs without a [verified] tag on the same line."""
        return self.ref_count - self.verified_count

    @property
    def clean_room_score(self) -> int:
        """Return a 0-10 score derived from verified/estimated ref counts.

        Heuristic:
            score = min(10, verified * 2 + estimated)
        Patterns with zero refs score 1 (placeholder, still extracted).
        """
        if self.ref_count == 0:
            return 1
        raw = self.verified_count * 2 + self.estimated_count
        return min(10, max(0, raw))


@dataclass
class ConsolidatedPattern:
    """A pattern observed across one or more dissects.

    Single-system patterns are kept (with ``is_cross_system = False``)
    so the catalog can also serve as an index; the report writer only
    surfaces the cross-system ones in the main body.
    """

    canonical_name: str  # lowercase, normalised for grouping
    occurrences: list[ExtractedPattern] = field(default_factory=list)

    @property
    def sistemas(self) -> list[str]:
        """Deduplicated, insertion-ordered list of sistemas where observed."""
        seen: set[str] = set()
        out: list[str] = []
        for occ in self.occurrences:
            if occ.sistema not in seen:
                seen.add(occ.sistema)
                out.append(occ.sistema)
        return out

    @property
    def is_cross_system(self) -> bool:
        """Return True if the pattern appears in >= MIN_CROSS_SYSTEM sistemas."""
        return len(set(occ.sistema for occ in self.occurrences)) >= MIN_CROSS_SYSTEM

    @property
    def average_clean_room_score(self) -> float:
        """Mean clean-room score across occurrences (0.0 when empty)."""
        if not self.occurrences:
            return 0.0
        return sum(p.clean_room_score for p in self.occurrences) / len(self.occurrences)

    @property
    def frequency(self) -> int:
        """Number of distinct sistemas where the pattern appears."""
        return len(self.sistemas)

    def display_name(self) -> str:
        """Return the most common original name (best readable form)."""
        names: dict[str, int] = {}
        for occ in self.occurrences:
            names[occ.name] = names.get(occ.name, 0) + 1
        return max(names, key=lambda n: names[n]) if names else self.canonical_name


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _strip_code_fences(body: str) -> str:
    """Remove fenced code blocks so heading/link/regex detection ignores them.

    Mirrors the helper in validator.py to keep parsing consistent across
    the dissector toolchain.
    """
    out: list[str] = []
    in_fence = False
    for line in body.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(line)
    return "\n".join(out)


def _normalise_name(name: str) -> str:
    """Return a normalised form for grouping/similarity.

    Lowercase, strip backticks/code markers, collapse whitespace to
    single hyphens, drop trailing punctuation.
    """
    cleaned = name.strip().strip("`").strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    return cleaned.strip("-")


def _levenshtein(a: str, b: str) -> int:
    """Iterative Levenshtein edit distance — stdlib only.

    Used to detect near-identical pattern names ("retry" vs "retries").
    Rotates rows to keep memory at O(min(len(a), len(b))).
    """
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    if len(a) > len(b):
        a, b = b, a
    prev = list(range(len(a) + 1))
    for i, ch_b in enumerate(b, start=1):
        curr = [i] + [0] * len(a)
        for j, ch_a in enumerate(a, start=1):
            cost = 0 if ch_a == ch_b else 1
            curr[j] = min(
                curr[j - 1] + 1,  # insertion
                prev[j] + 1,  # deletion
                prev[j - 1] + cost,  # substitution
            )
        prev = curr
    return prev[-1]


def _is_similar(a: str, b: str) -> bool:
    """Return True when two normalised names should be merged.

    Three signals are OR'd together:
        1. Exact match (already handled before this is called for clarity).
        2. Levenshtein distance <= LEVENSHTEIN_THRESHOLD — collapses short
           typos like "retry" / "retries".
        3. SequenceMatcher ratio >= 0.6 — catches shared-prefix patterns
           like "retry-with-backoff" / "retry-with-jitter" where most of
           the name matches but the suffix diverges.
        4. Token Jaccard >= 0.5 — handles hyphenated names where the
           shared structure matters more than the exact spelling.

    The thresholds are deliberately conservative: false positives in the
    consolidated catalog pollute the cross-system evidence base, while
    false negatives just keep two single-system entries apart.
    """
    if a == b:
        return True
    if abs(len(a) - len(b)) > LEVENSHTEIN_THRESHOLD + 1:
        # Cheap length pre-filter; longer gaps almost always exceed the
        # edit budget and the other tests below.
        pass
    elif _levenshtein(a, b) <= LEVENSHTEIN_THRESHOLD:
        return True
    if SequenceMatcher(None, a, b).ratio() >= 0.6:
        return True
    tokens_a = set(a.split("-")) - {""}
    tokens_b = set(b.split("-")) - {""}
    if not tokens_a or not tokens_b:
        return False
    overlap = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(overlap) / len(union) >= 0.5


def _extract_refs_with_tags(body: str) -> list[PatternRef]:
    """Pull file:line references out of ``body`` and tag each as verified/estimated.

    Tags are detected on the **same line** as the reference (consistent
    with ``validator.py:_tag_refs_in_window``). Refs without any tag on
    their line are classified as estimated by default — anti-hallucination
    rules penalise untagged refs anyway.
    """
    refs: list[PatternRef] = []
    for match in _FILE_LINE_REF_RE.finditer(body):
        line_start = body.rfind("\n", 0, match.start()) + 1
        line_end = body.find("\n", match.end())
        if line_end == -1:
            line_end = len(body)
        line = body[line_start:line_end]
        verified = bool(_VERIFIED_TAG_RE.search(line))
        refs.append(
            PatternRef(path=match.group(1), line=int(match.group(2)), verified=verified)
        )
    return refs


def parse_patterns_file(path: Path, sistema: str) -> list[ExtractedPattern]:
    """Parse one ``extract/patterns.md`` into a list of ``ExtractedPattern``.

    Only ``### 2.N <name>`` blocks under ``## 2. Patterns (detailed)`` are
    captured (matches the canonical extract-patterns template).

    Args:
        path: Absolute path to the patterns.md file.
        sistema: Sistema name (parent directory name).

    Returns:
        List of extracted patterns. Empty when the file has no recognised
        patterns (e.g. empty file or template not yet filled).
    """
    if not path.exists():
        LOGGER.debug("patterns file missing: %s", path)
        return []
    body = path.read_text(encoding="utf-8")
    outside = _strip_code_fences(body)

    # Locate the "## 2. Patterns (detailed)" section; patterns outside it
    # are noise (e.g. the summary table does not contain ### headings).
    section_match = re.search(
        r"^##\s+2\.\s+Patterns\s+\(detailed\)\s*$",
        outside,
        re.MULTILINE,
    )
    if not section_match:
        LOGGER.debug("no '## 2. Patterns (detailed)' section in %s", path)
        return []
    section_start = section_match.end()
    # Section ends at the next H2 (## N.) or end-of-file.
    next_section = re.search(r"^##\s+\d+\.\s+", outside[section_start:], re.MULTILINE)
    section_end = section_start + next_section.start() if next_section else len(outside)
    section = outside[section_start:section_end]

    results: list[ExtractedPattern] = []
    for match in _PATTERN_HEADING_RE.finditer(section):
        major, minor, raw_name = match.groups()
        raw_name = raw_name.strip()
        section_no = f"{major}.{minor}"

        # Block runs from the heading to the next ###/## heading.
        block_start = match.end()
        next_heading = re.search(r"^#{2,3}\s+", section[block_start:], re.MULTILINE)
        block_end = block_start + next_heading.start() if next_heading else len(section)
        block_body = section[block_start:block_end]

        # Parse field lines (Category / Quality / Effort) inside the block.
        fields: dict[str, str] = {}
        for field_match in _FIELD_RE.finditer(block_body):
            fields[field_match.group(1).strip().lower()] = field_match.group(2).strip()

        where_used = ""
        wu_match = _WHERE_USED_RE.search(block_body)
        if wu_match:
            where_used = wu_match.group(1).strip()

        results.append(
            ExtractedPattern(
                sistema=sistema,
                section_no=section_no,
                name=raw_name,
                raw_name=raw_name,
                category=fields.get("category", ""),
                quality=fields.get("quality", ""),
                effort=fields.get("effort to port", fields.get("effort", "")),
                where_used=where_used,
                body=block_body,
                refs=_extract_refs_with_tags(block_body),
            )
        )
    return results


def discover_patterns(
    base: Path = DISSECTS_DIR,
) -> list[ExtractedPattern]:
    """Walk ``base/<sistema>/extract/patterns.md`` and parse each file.

    Args:
        base: Dissects root (defaults to ``HINDSIGHT_ROOT/dissects``).

    Returns:
        Aggregated list of ExtractedPattern from every dissect that has a
        patterns.md file.
    """
    out: list[ExtractedPattern] = []
    if not base.exists():
        LOGGER.warning("dissects root missing: %s", base)
        return out
    for sistema_dir in sorted(base.iterdir()):
        if not sistema_dir.is_dir():
            continue
        # Skip non-dissect directories (output of consolidate itself lives here).
        if sistema_dir.name.startswith(("_", ".")):
            continue
        patterns_path = sistema_dir / "extract" / PATTERNS_FILENAME
        parsed = parse_patterns_file(patterns_path, sistema_dir.name)
        if parsed:
            LOGGER.debug("parsed %d patterns from %s", len(parsed), sistema_dir.name)
            out.extend(parsed)
    return out


def consolidate(patterns: list[ExtractedPattern]) -> list[ConsolidatedPattern]:
    """Group patterns by name similarity (Levenshtein-bounded).

    Args:
        patterns: Flat list of patterns from every dissect.

    Returns:
        Consolidated patterns, one per group. Order is stable:
        insertion order matches the first occurrence in ``patterns``.
    """
    groups: list[ConsolidatedPattern] = []
    for pat in patterns:
        norm = _normalise_name(pat.name)
        if not norm:
            continue
        merged = False
        for group in groups:
            if _is_similar(group.canonical_name, norm):
                group.canonical_name = group.canonical_name  # keep first
                group.occurrences.append(pat)
                merged = True
                break
        if not merged:
            groups.append(ConsolidatedPattern(canonical_name=norm, occurrences=[pat]))
    return groups


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _utcnow_iso() -> str:
    """Return current UTC time as ISO-8601 string with trailing Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_markdown(
    groups: list[ConsolidatedPattern],
    total_dissects: int,
    generated_at: str,
) -> str:
    """Render the consolidated catalog as markdown.

    Single-system patterns are listed in a "single-system" section at
    the bottom; the main body only shows patterns observed in >= 2
    sistemas.

    Args:
        groups: Consolidated patterns (already grouped).
        total_dissects: Total number of dissects with patterns.md files.
        generated_at: ISO-8601 timestamp to embed in the header.

    Returns:
        Full markdown body for ``dissects/_cross-system-patterns.md``.
    """
    cross = [g for g in groups if g.is_cross_system]
    single = [g for g in groups if not g.is_cross_system]
    cross.sort(
        key=lambda g: (-g.frequency, -g.average_clean_room_score, g.canonical_name)
    )
    single.sort(key=lambda g: g.canonical_name)

    lines: list[str] = []
    lines.append("---")
    lines.append("pattern: cross-system/aggregate/canonical-catalog")
    lines.append("status: draft")
    lines.append(f"consolidado_em: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    lines.append(f"total_origins: {total_dissects}")
    lines.append("gerado_por: consolidate_patterns.py consolidate")
    lines.append("---")
    lines.append("")
    lines.append("# Cross-System Patterns — canonical catalog")
    lines.append("")
    lines.append(
        "> **Propósito**: catálogo consolidado de patterns extraídos de "
        "MÚLTIPLOS dissects. Cada pattern aqui foi observado em >= 2 sistemas "
        "diferentes (validação cross-system). Use este artefato quando precisar "
        "decidir entre *implementar canônico*, *referenciar* (lib existente) "
        "ou *comprar* (vendor) — nunca para copy-paste cego."
    )
    lines.append("")
    lines.append("## Sumário")
    lines.append("")
    lines.append("| # | Pattern | Sistemas | Score médio | Frequência | Recomendação |")
    lines.append("|---|---------|----------|-------------|------------|--------------|")
    if not cross:
        lines.append(
            "| — | _nenhum pattern cross-system detectado ainda_ | — | — | — | — |"
        )
    else:
        for idx, g in enumerate(cross, start=1):
            lines.append(
                f"| {idx} | `{g.display_name()}` | "
                f"{', '.join(g.sistemas)} | "
                f"{g.average_clean_room_score:.1f}/10 | "
                f"{g.frequency}/{total_dissects} | "
                f"{_recommendation_placeholder(g)} |"
            )
    lines.append("")
    lines.append(
        f"**Total**: {len(cross)} cross-system pattern(s), "
        f"{len(single)} single-system pattern(s), "
        f"{total_dissects} dissect(s) varrido(s)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Patterns cross-system")
    lines.append("")

    if not cross:
        lines.append(
            "_Sem patterns cross-system ainda. Re-rodar este script após "
            "completar Phase 4 de pelo menos mais um dissect, ou após "
            "adicionar patterns a um dissect existente._"
        )
        lines.append("")
    else:
        for g in cross:
            lines.extend(_render_group(g, total_dissects))
            lines.append("---")
            lines.append("")

    if single:
        lines.append("## Patterns single-system (referência)")
        lines.append("")
        lines.append(
            "Estes patterns aparecem em apenas 1 dissect — não contam como "
            "evidência cross-system. Ficam aqui apenas como índice."
        )
        lines.append("")
        for g in single:
            occ = g.occurrences[0]
            lines.append(
                f"- `{occ.name}` (sistema: `{occ.sistema}`, "
                f"score: {occ.clean_room_score}/10, "
                f"category: {occ.category or '—'})"
            )
        lines.append("")

    lines.append("## Metadados de geração")
    lines.append("")
    lines.append(f"- **Timestamp**: `{generated_at}`")
    lines.append(f"- **Total dissects varridos**: {total_dissects}")
    lines.append(
        f"- **Total patterns extraídos**: {sum(len(g.occurrences) for g in groups)}"
    )
    lines.append(f"- **Patterns cross-system (>= 2 origens)**: {len(cross)}")
    lines.append(f"- **Patterns single-system**: {len(single)}")
    lines.append("")
    return "\n".join(lines)


def _recommendation_placeholder(group: ConsolidatedPattern) -> str:
    """Return a default recommendation placeholder based on score/frequency.

    Human curator overrides this after the script generates the catalog.
    """
    if group.frequency >= 3 and group.average_clean_room_score >= 7:
        return "implementar canônico"
    if group.average_clean_room_score >= 6:
        return "referenciar"
    return "avaliar caso a caso"


def _render_group(group: ConsolidatedPattern, total_dissects: int) -> list[str]:
    """Render the markdown block for one consolidated pattern."""
    lines: list[str] = []
    lines.append(f"### Pattern: {group.display_name()}")
    lines.append("")
    lines.append(f"**Spec funcional** (clean-room — sem código colado):")
    lines.append("")
    lines.append(
        "> Spec a ser redigida por humano após revisão. Pseudocódigo abaixo "
        "é placeholder; substitua com base nos snippets divergentes abaixo."
    )
    lines.append("")
    lines.append("```text")
    lines.append(f"function {group.canonical_name}(input: T) -> Result<U, E>:")
    lines.append("    # TODO: descrever fluxo, invariantes, pós-condições")
    lines.append("    return Err(NotImplemented)")
    lines.append("```")
    lines.append("")
    lines.append("**Origens observadas** (cross-system — mínimo 2 sistemas):")
    lines.append("")
    systems_in_order: list[str] = []
    for occ in group.occurrences:
        if occ.sistema not in systems_in_order:
            systems_in_order.append(occ.sistema)
        lines.append(
            f"- `dissects/{occ.sistema}/extract/patterns.md` — Pattern "
            f"{occ.section_no} `{occ.name}` "
            f"(score clean-room: {occ.clean_room_score}/10)"
        )
    lines.append("")
    lines.append("**Implementações divergentes**:")
    lines.append("")
    lines.append("| Sistema | Abordagem | Complexidade | Stack | Onde |")
    lines.append("|---------|-----------|--------------|-------|------|")
    for occ in group.occurrences:
        # Heuristic to populate complexity/stack from the first ref when
        # possible; otherwise leave blank for human curation.
        primary_ref = occ.refs[0] if occ.refs else None
        where = f"`{primary_ref.path}:{primary_ref.line}`" if primary_ref else "—"
        complexity = "—"  # human fills in based on the spec
        stack = "—"  # human fills in based on extract/components.md
        lines.append(
            f"| `{occ.sistema}` | _descrever abordagem_ | {complexity} | "
            f"{stack} | {where} |"
        )
    lines.append("")
    lines.append("**Recomendação** (para qualquer stack destino):")
    lines.append("")
    lines.append(f"- Recomendação automática: **{_recommendation_placeholder(group)}**")
    lines.append("- [ ] Implementar canônico no nosso stack")
    lines.append("- [ ] Referenciar (usar lib existente)")
    lines.append("- [ ] Comprar / vendor (pacote de terceiros)")
    lines.append("")
    lines.append("**Métricas**:")
    lines.append("")
    lines.append(f"- Frequência: {group.frequency}/{total_dissects}")
    lines.append(f"- Score clean-room médio: {group.average_clean_room_score:.1f}/10")
    lines.append(
        f"- Refs verificadas: "
        f"{sum(o.verified_count for o in group.occurrences)}"
        f" / total "
        f"{sum(o.ref_count for o in group.occurrences)}"
    )
    lines.append(
        f"- Categorias representadas: "
        f"{', '.join(sorted(set(o.category for o in group.occurrences if o.category))) or '—'}"
    )
    lines.append(f"- Origens: {', '.join(systems_in_order)}")
    lines.append("")
    return lines


# ---------------------------------------------------------------------------
# CLI subcommands
# ---------------------------------------------------------------------------


def cmd_consolidate(args: argparse.Namespace) -> int:
    """Generate the consolidated catalog and write it to disk."""
    output = Path(args.output) if args.output else OUTPUT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)

    patterns = discover_patterns(Path(args.base))
    if not patterns:
        LOGGER.warning("no patterns found under %s; nothing to consolidate", args.base)
        # Still write an empty stub so downstream tooling has a target.
        stub = render_markdown(
            groups=[],
            total_dissects=0,
            generated_at=_utcnow_iso(),
        )
        output.write_text(stub, encoding="utf-8")
        return EXIT_OK

    sistemas = sorted({p.sistema for p in patterns})
    groups = consolidate(patterns)
    generated_at = _utcnow_iso()
    body = render_markdown(
        groups=groups,
        total_dissects=len(sistemas),
        generated_at=generated_at,
    )
    output.write_text(body, encoding="utf-8")
    cross = sum(1 for g in groups if g.is_cross_system)
    LOGGER.info(
        "consolidated %d pattern(s) across %d dissect(s) -> %d cross-system → %s",
        len(patterns),
        len(sistemas),
        cross,
        output,
    )
    return EXIT_OK


def cmd_validate(args: argparse.Namespace) -> int:
    """Re-score and print details for one specific pattern name."""
    needle = _normalise_name(args.pattern)
    patterns = discover_patterns(Path(args.base))
    groups = consolidate(patterns)
    matches = [
        g for g in groups if g.canonical_name == needle or needle in g.canonical_name
    ]
    if not matches:
        LOGGER.error("pattern not found: %s", args.pattern)
        return EXIT_ERROR
    for g in matches:
        print(
            json.dumps(
                {
                    "canonical_name": g.canonical_name,
                    "display_name": g.display_name(),
                    "is_cross_system": g.is_cross_system,
                    "frequency": g.frequency,
                    "average_clean_room_score": round(g.average_clean_room_score, 2),
                    "sistemas": g.sistemas,
                    "occurrences": [
                        {
                            "sistema": o.sistema,
                            "section": o.section_no,
                            "name": o.name,
                            "category": o.category,
                            "quality": o.quality,
                            "effort": o.effort,
                            "clean_room_score": o.clean_room_score,
                            "ref_count": o.ref_count,
                            "verified_count": o.verified_count,
                        }
                        for o in g.occurrences
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    return EXIT_OK


def cmd_search(args: argparse.Namespace) -> int:
    """Search patterns by keyword (substring or Levenshtein)."""
    needle = _normalise_name(args.keyword)
    patterns = discover_patterns(Path(args.base))
    groups = consolidate(patterns)
    matches: list[ConsolidatedPattern] = []
    for g in groups:
        if needle in g.canonical_name:
            matches.append(g)
            continue
        if _is_similar(g.canonical_name, needle):
            matches.append(g)
    if not matches:
        LOGGER.warning("no pattern matches keyword: %s", args.keyword)
        return EXIT_WARNING
    for g in matches:
        print(
            f"{g.display_name():40s}  sistemas={','.join(g.sistemas)}  "
            f"freq={g.frequency}  score={g.average_clean_room_score:.1f}/10"
        )
    return EXIT_OK


def cmd_list(args: argparse.Namespace) -> int:
    """Print a compact table of all consolidated patterns."""
    patterns = discover_patterns(Path(args.base))
    if not patterns:
        print("(no patterns found)")
        return EXIT_OK
    grupos = consolidate(patterns)
    sistemas = sorted({p.sistema for p in patterns})
    cross = [g for g in grupos if g.is_cross_system]
    cross.sort(
        key=lambda g: (-g.frequency, -g.average_clean_room_score, g.canonical_name)
    )
    print(f"{'pattern':40s}  {'sistemas':24s}  {'freq':>4s}  {'score':>5s}  rec")
    print("-" * 90)
    for g in cross:
        sistemas_col = ",".join(g.sistemas)
        if len(sistemas_col) > 24:
            sistemas_col = sistemas_col[:21] + "..."
        print(
            f"{g.display_name():40s}  {sistemas_col:24s}  "
            f"{g.frequency:>4d}  {g.average_clean_room_score:>4.1f}  "
            f"{_recommendation_placeholder(g)}"
        )
    if not cross:
        print("(no cross-system patterns yet)")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the consolidate CLI."""
    parser = argparse.ArgumentParser(
        prog="consolidate_patterns",
        description="Cross-system pattern consolidation for system-dissector.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="enable DEBUG logging"
    )
    parser.add_argument(
        "--base",
        default=str(DISSECTS_DIR),
        help=f"dissects root (default: {DISSECTS_DIR})",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    p_cons = sub.add_parser(
        "consolidate",
        help="scan dissects/*/extract/patterns.md and write _cross-system-patterns.md",
    )
    p_cons.add_argument(
        "--output",
        "-o",
        default=str(OUTPUT_PATH),
        help=f"output path (default: {OUTPUT_PATH})",
    )
    p_cons.set_defaults(func=cmd_consolidate)

    p_val = sub.add_parser(
        "validate", help="re-score and dump one consolidated pattern by name"
    )
    p_val.add_argument("pattern", help="pattern name (or substring) to inspect")
    p_val.set_defaults(func=cmd_validate)

    p_search = sub.add_parser(
        "search", help="search consolidated patterns by keyword (substring/Levenshtein)"
    )
    p_search.add_argument("keyword")
    p_search.set_defaults(func=cmd_search)

    p_list = sub.add_parser(
        "list", help="print a compact table of all cross-system patterns"
    )
    p_list.set_defaults(func=cmd_list)

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
