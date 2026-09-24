"""Core helpers for the system-dissector skill.

Provides path resolution, state persistence, template rendering, and CLI
entry points used while dissecting any system (source, binary, mobile,
firmware, protocol).

Usage as a library:
    from dissect_utils import DissectPaths, DissectState, init_sistema

Usage from the shell:
    python dissect_utils.py init my-system --tipo source
    python dissect_utils.py state my-system
    python dissect_utils.py phase my-system 2 --status in_progress
    python dissect_utils.py list
    python dissect_utils.py checklist my-system
    python dissect_utils.py template triagem --output triagem.md
    python dissect_utils.py index --update
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HINDSIGHT_ROOT: Path = Path(
    "/Users/andersongoliveira/projects/engenharia reversa/neodissector"
)
"""Canonical root for all dissect outputs."""

TEMPLATE_DIR: Path = Path(__file__).resolve().parent.parent / "templates"
"""Directory holding *.md.template files."""

VALID_PHASES: tuple[int, ...] = (1, 2, 3, 4, 5)
"""Five-phase workflow: triage, deep-dive, doc, extract, handoff."""

VALID_TIPOS: tuple[str, ...] = (
    "source",
    "binary",
    "mobile",
    "firmware",
    "protocol",
)
"""Target classification options."""

VALID_STATUSES: tuple[str, ...] = ("pending", "in_progress", "completed", "skipped")
"""Phase status options."""

SISTEMA_NAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
"""Kebab-case alphanumeric with hyphens (no leading/trailing/double hyphens)."""

LOGGER = logging.getLogger("system-dissector")


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DissectPaths:
    """Resolved filesystem paths for a given dissect.

    All paths are derived from a single ``root`` to keep the layout
    consistent across systems.
    """

    sistema: str
    root: Path
    triagem: Path
    deep_dive: Path
    wiki: Path
    extract: Path
    handoff: Path
    integrate_neoai: Path
    state: Path
    readme: Path

    @classmethod
    def for_sistema(cls, sistema: str, base: Path = HINDSIGHT_ROOT) -> "DissectPaths":
        """Build the canonical paths for ``sistema`` under ``base``.

        Args:
            sistema: Kebab-case system name.
            base: Root containing the ``dissects/`` directory.

        Returns:
            DissectPaths with every child path materialised.
        """
        root = base / "dissects" / sistema
        return cls(
            sistema=sistema,
            root=root,
            triagem=root / "triagem.md",
            deep_dive=root / "deep-dive",
            wiki=root / "wiki",
            extract=root / "extract",
            handoff=root / "handoff",
            integrate_neoai=root / "integrate-neoai",
            state=root / "state.json",
            readme=root / "README.md",
        )

    def ensure_dirs(self) -> None:
        """Create all directories used by the workflow in-place."""
        self.deep_dive.mkdir(parents=True, exist_ok=True)
        self.wiki.mkdir(parents=True, exist_ok=True)
        self.extract.mkdir(parents=True, exist_ok=True)
        self.handoff.mkdir(parents=True, exist_ok=True)
        # ``integrate_neoai`` is opt-in (created lazily by neodoo-integrate).
        # We don't ``mkdir`` it here so that empty directories don't pollute
        # the dissect tree when the operator never invokes the companion.

    def exists(self) -> bool:
        """Return True if the dissect root directory already exists."""
        return self.root.exists()


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    """Return the current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


@dataclass
class DissectState:
    """Mutable runtime state of a dissect.

    Stored on disk as ``state.json`` under the dissect root.
    """

    sistema: str
    tipo: str
    phase: int = 1
    phase_status: dict[int, str] = field(default_factory=dict)
    started_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate enum-like fields and normalise datetimes to UTC."""
        if self.tipo not in VALID_TIPOS:
            raise ValueError(
                f"invalid tipo '{self.tipo}'; expected one of {VALID_TIPOS}"
            )
        if self.phase not in VALID_PHASES:
            raise ValueError(
                f"invalid phase '{self.phase}'; expected one of {VALID_PHASES}"
            )
        for phase_no, status in self.phase_status.items():
            if phase_no not in VALID_PHASES:
                raise ValueError(f"invalid phase in phase_status: {phase_no}")
            if status not in VALID_STATUSES:
                raise ValueError(f"invalid status '{status}' for phase {phase_no}")
        if self.started_at.tzinfo is None:
            self.started_at = self.started_at.replace(tzinfo=timezone.utc)
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)

    @classmethod
    def load(cls, path: Path) -> "DissectState":
        """Load a state file from disk.

        Args:
            path: Path to the JSON file.

        Returns:
            The reconstructed DissectState.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the JSON is malformed or invalid.
        """
        if not path.exists():
            raise FileNotFoundError(f"state file not found: {path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        started_raw = raw.get("started_at")
        updated_raw = raw.get("updated_at")
        started = _parse_iso(started_raw) if started_raw else _utcnow()
        updated = _parse_iso(updated_raw) if updated_raw else started
        return cls(
            sistema=raw["sistema"],
            tipo=raw["tipo"],
            phase=raw.get("phase", 1),
            phase_status={int(k): v for k, v in raw.get("phase_status", {}).items()},
            started_at=started,
            updated_at=updated,
            notes=list(raw.get("notes", [])),
        )

    def save(self, path: Path) -> None:
        """Persist the state to ``path`` as pretty JSON with atomic write.

        Uses write-temp + rename for atomicity (prevents partial writes).

        Args:
            path: Destination file (parent dirs will be created).
        """
        self.updated_at = _utcnow()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "sistema": self.sistema,
            "tipo": self.tipo,
            "phase": self.phase,
            "phase_status": {str(k): v for k, v in self.phase_status.items()},
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "notes": list(self.notes),
        }
        # Atomic write: temp file + rename (POSIX atomic)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        tmp.replace(path)

    def mark_phase(self, phase: int, status: str) -> None:
        """Update the status of a phase and bump ``updated_at``.

        Args:
            phase: Phase number (1-5).
            status: One of ``VALID_STATUSES``.
        """
        if phase not in VALID_PHASES:
            raise ValueError(f"invalid phase {phase}")
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid status '{status}'")
        self.phase_status[phase] = status
        if status == "in_progress" and phase >= self.phase:
            self.phase = phase
        self.updated_at = _utcnow()

    def is_complete(self) -> bool:
        """Return True if all four core phases (1-4) are completed."""
        return all(self.phase_status.get(p) == "completed" for p in (1, 2, 3, 4))

    def next_phase(self) -> int:
        """Return the next phase to execute (current + 1, capped at 5)."""
        if self.phase >= max(VALID_PHASES):
            return max(VALID_PHASES)
        return self.phase + 1


def _parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 string into a timezone-aware datetime."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def validate_sistema_name(name: str) -> str:
    """Validate and normalise a system name.

    Args:
        name: Candidate name.

    Returns:
        The validated name (stripped and lowered).

    Raises:
        ValueError: If the name is not kebab-case alphanumeric.
    """
    candidate = name.strip().lower()
    if not candidate:
        raise ValueError("system name cannot be empty")
    if not SISTEMA_NAME_PATTERN.match(candidate):
        raise ValueError(
            "system name must be kebab-case (lowercase alphanumeric with "
            "single hyphens); got: " + repr(name)
        )
    return candidate


def get_sistema_state(sistema: str) -> Optional[DissectState]:
    """Load state for ``sistema`` or return None when absent."""
    state_path = DissectPaths.for_sistema(sistema).state
    if not state_path.exists():
        return None
    try:
        return DissectState.load(state_path)
    except (FileNotFoundError, ValueError, KeyError, json.JSONDecodeError) as exc:
        LOGGER.warning("failed to load state for %s: %s", sistema, exc)
        return None


def list_dissects(base: Path = HINDSIGHT_ROOT) -> list[str]:
    """Return the list of sistema names currently under ``base/dissects``.

    Args:
        base: Hindsight root.

    Returns:
        Sorted list of directory names (only those with state.json).
    """
    dissects_root = base / "dissects"
    if not dissects_root.exists():
        return []
    found: list[str] = []
    for entry in sorted(dissects_root.iterdir()):
        if not entry.is_dir():
            continue
        if (entry / "state.json").exists():
            found.append(entry.name)
    return found


# ---------------------------------------------------------------------------
# Index / catalog generation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DissectSummary:
    """One-line summary of a dissect, used to render INDEX.md."""

    sistema: str
    tipo: str
    phase: int
    progress: int
    total: int
    updated_at: datetime
    state_status: str  # dominant status of the current phase

    @property
    def progress_str(self) -> str:
        """Format progress as ``N/total``."""
        return f"{self.progress}/{self.total}"

    @property
    def updated_iso(self) -> str:
        """ISO date (YYYY-MM-DD) of last update."""
        return self.updated_at.date().isoformat()


def build_summaries(base: Path = HINDSIGHT_ROOT) -> list[DissectSummary]:
    """Collect one ``DissectSummary`` per dissect that has a ``state.json``.

    Args:
        base: Hindsight root.

    Returns:
        Sorted list (by ``updated_at`` desc) of summaries. Dissects whose
        state is unreadable are silently omitted (a warning is logged).
    """
    sistemas = list_dissects(base)
    summaries: list[DissectSummary] = []
    total = len(VALID_PHASES)
    for name in sistemas:
        state = get_sistema_state(name)
        if state is None:
            LOGGER.warning("skipping %s: unreadable state", name)
            continue
        progress = sum(
            1 for status in state.phase_status.values() if status == "completed"
        )
        current_status = state.phase_status.get(state.phase, "pending")
        summaries.append(
            DissectSummary(
                sistema=name,
                tipo=state.tipo,
                phase=state.phase,
                progress=progress,
                total=total,
                updated_at=state.updated_at,
                state_status=current_status,
            )
        )
    summaries.sort(key=lambda s: s.updated_at, reverse=True)
    return summaries


def render_index(summaries: list[DissectSummary]) -> str:
    """Render ``INDEX.md`` content from a list of summaries.

    Args:
        summaries: Per-dissect summaries (most-recent first).

    Returns:
        Markdown body for ``dissects/INDEX.md``.
    """
    header_lines = [
        "# Dissects INDEX",
        "",
        "> Auto-generated via "
        "`python3 ~/.agents/skills/system-dissector/resources/scripts/"
        "dissect_utils.py index --update`.",
        ">",
        "> Source of truth = `dissects/<sistema>/state.json`. "
        "Do NOT edit this file by hand.",
        "",
        "| Sistema | Tipo | Phase | Progresso | Status atual | Atualizado |",
        "|---|---|---|---|---|---|",
    ]
    body_lines: list[str] = []
    for s in summaries:
        body_lines.append(
            f"| `{s.sistema}` | {s.tipo} | {s.phase}/{s.total} | "
            f"{s.progress_str} | {s.state_status} | {s.updated_iso} |"
        )
    if not body_lines:
        body_lines.append("| _(no dissects yet)_ | — | — | 0/5 | pending | — |")
    footer_lines = [
        "",
        f"**Total**: {len(summaries)} dissect(s).",
        "",
        "## How to use",
        "",
        "1. Pick a row above.",
        "2. Open `dissects/<sistema>/README.md` for the entry point.",
        "3. Drill into `wiki/`, `deep-dive/`, `extract/`, `handoff/` per phase.",
        "4. Re-run `dissect_utils.py index --update` whenever a `state.json` changes.",
        "",
    ]
    return "\n".join(header_lines + body_lines + footer_lines) + "\n"


# ---------------------------------------------------------------------------
# Template handling
# ---------------------------------------------------------------------------


@dataclass
class TemplateVars:
    """Convenience container for template variables (unused, kept for future)."""

    sistema: str = ""
    tipo: str = ""
    phase: int = 1
    date: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


def get_template(template_name: str) -> str:
    """Load a ``<name>.md.template`` file from the templates directory.

    Args:
        template_name: Name without the ``.md.template`` suffix.

    Returns:
        The raw template body.

    Raises:
        FileNotFoundError: When the template does not exist.
    """
    template_path = TEMPLATE_DIR / f"{template_name}.md.template"
    if not template_path.exists():
        raise FileNotFoundError(f"template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def render_template(template_name: str, **vars: Any) -> str:
    """Render a template by replacing ``<KEY>`` placeholders.

    Unknown keys raise an error to prevent silent placeholder leaks.

    Args:
        template_name: Template identifier (without extension).
        **vars: Mapping of placeholder name to value.

    Returns:
        Rendered string with all ``<KEY>`` tokens replaced.

    Raises:
        FileNotFoundError: When the template file is missing.
        KeyError: When an undeclared placeholder remains.
    """
    body = get_template(template_name)
    declared: set[str] = set(re.findall(r"<([A-Z0-9_]+)>", body))
    missing = declared.difference(vars)
    if missing:
        raise KeyError(
            f"template {template_name!r} requires variables: {sorted(missing)}"
        )
    rendered = body
    for key, value in vars.items():
        rendered = rendered.replace(f"<{key}>", str(value))
    return rendered


# ---------------------------------------------------------------------------
# Per-phase checklist
# ---------------------------------------------------------------------------


@dataclass
class PhaseCheck:
    """Single item in a phase checklist."""

    key: str
    label: str
    satisfied: bool
    detail: str = ""


def checklist_phase(phase: int, paths: DissectPaths) -> dict[str, bool]:
    """Compute the checklist for one workflow phase.

    Args:
        phase: Phase number (1-5).
        paths: Resolved dissect paths.

    Returns:
        Mapping of checklist key to satisfied boolean.
    """
    if phase not in VALID_PHASES:
        raise ValueError(f"invalid phase {phase}")

    root = paths.root
    if phase == 1:
        return {
            "triagem_exists": paths.triagem.exists(),
            "triagem_non_empty": paths.triagem.exists()
            and paths.triagem.stat().st_size > 0,
            "state_initialized": paths.state.exists(),
            "tipo_declared": _has_section(paths.triagem, "Tipo"),
        }
    if phase == 2:
        modules_dir = paths.deep_dive
        modules = list(modules_dir.glob("module-*.md")) if modules_dir.exists() else []
        return {
            "architecture_md": (modules_dir / "architecture.md").exists(),
            "data_flows_md": (modules_dir / "data-flows.md").exists(),
            "key_structures_md": (modules_dir / "key-structures.md").exists(),
            "modules_analyzed": len(modules) >= 1,
        }
    if phase == 3:
        wiki = paths.wiki
        return {
            "wiki_index": (wiki / "index.md").exists(),
            "wiki_readme": (wiki / "README.md").exists(),
            "wiki_architecture_dir": (wiki / "architecture").exists(),
            "wiki_modules_dir": (wiki / "modules").exists(),
            "wiki_glossary": (wiki / "glossary.md").exists(),
        }
    if phase == 4:
        extract = paths.extract
        return {
            "components_md": (extract / "components.md").exists(),
            "patterns_md": (extract / "patterns.md").exists(),
            "dependencies_md": (extract / "dependencies.md").exists(),
            "scoring_rubric_present": _has_section(
                extract / "components.md", "Scoring rubric"
            ),
        }
    # phase 5 (HANDOFF — stack-agnostic)
    handoff = paths.handoff
    return {
        "handoff_readme": (handoff / "README.md").exists(),
        "handoff_learning_path": (handoff / "learning-path.md").exists(),
        "handoff_implementation_guide": (handoff / "implementation-guide.md").exists(),
        "handoff_patterns_catalog": (handoff / "patterns-catalog.md").exists(),
        "handoff_decisions": (handoff / "decisions.md").exists(),
        "handoff_reuse_checklist": (handoff / "reuse-checklist.md").exists(),
        "handoff_components_priority": (handoff / "components-priority.md").exists(),
        # OPT-IN: only populated when the operator runs the
        # ``neodoo-integrate`` companion skill for a destination-specific target.
        "integrate_neoai_dir": paths.integrate_neoai.exists(),
        "integrate_neoai_md": (paths.integrate_neoai / "integrate.md").exists(),
        "root_readme": root.joinpath("README.md").exists(),
    }


def _has_section(path: Path, heading: str) -> bool:
    """Return True if ``path`` contains a markdown heading matching ``heading``."""
    if not path.exists():
        return False
    try:
        body = path.read_text(encoding="utf-8")
    except OSError:
        return False
    pattern = re.compile(rf"^#+\s*{re.escape(heading)}", re.MULTILINE)
    return bool(pattern.search(body))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    """Configure root logger once for the CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s [%(name)s] %(message)s",
    )


def cmd_init(args: argparse.Namespace) -> int:
    """Handle ``init`` subcommand: create dirs + state.json."""
    sistema = validate_sistema_name(args.sistema)
    paths = DissectPaths.for_sistema(sistema)
    paths.ensure_dirs()
    state_path = paths.state
    if state_path.exists() and not args.force:
        LOGGER.error(
            "state already exists for %s at %s (use --force to overwrite)",
            sistema,
            state_path,
        )
        return 1
    state = DissectState(sistema=sistema, tipo=args.tipo)
    state.phase_status[1] = "in_progress"
    state.save(state_path)
    paths.readme.parent.mkdir(parents=True, exist_ok=True)
    if not paths.readme.exists():
        paths.readme.write_text(_readme_template(sistema, args.tipo), encoding="utf-8")
    LOGGER.info("initialised %s (tipo=%s) at %s", sistema, args.tipo, paths.root)
    return 0


def _readme_template(sistema: str, tipo: str) -> str:
    """Return a minimal README scaffold for a fresh dissect."""
    return (
        f"# {sistema}\n\n"
        f"**Tipo**: {tipo}\n"
        f"**Status**: Phase 1 in progress\n\n"
        f"See:\n\n"
        f"- `triagem.md`\n"
        f"- `deep-dive/`\n"
        f"- `wiki/`\n"
        f"- `extract/`\n"
        f"- `handoff/` (Phase 5 — stack-agnostic deliverables)\n"
        f"- `integrate-neoai/` (OPT-IN — only if a destination-specific companion was run)\n"
    )


def cmd_state(args: argparse.Namespace) -> int:
    """Handle ``state`` subcommand: print the current state of one system."""
    sistema = validate_sistema_name(args.sistema)
    state = get_sistema_state(sistema)
    if state is None:
        LOGGER.error("no state for %s; run 'init' first", sistema)
        return 1
    print(json.dumps(asdict(state), indent=2, default=str))
    return 0


@contextlib.contextmanager
def _state_lock(state_path: Path) -> Iterator[None]:
    """Acquire exclusive flock on a lockfile adjacent to ``state.json``.

    Prevents race conditions when multiple sub-agents update state
    concurrently (Phase 2 parallel). Uses fcntl.flock + blocking wait.

    Args:
        state_path: Path to state.json. Lockfile is ``state.json.lock``.
    """
    lock_path = state_path.with_suffix(state_path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as lock_fd:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)


def cmd_phase(args: argparse.Namespace) -> int:
    """Handle ``phase`` subcommand: update one phase's status."""
    sistema = validate_sistema_name(args.sistema)
    paths = DissectPaths.for_sistema(sistema)
    if not paths.state.exists():
        LOGGER.error("no state for %s; run 'init' first", sistema)
        return 1
    with _state_lock(paths.state):
        state = DissectState.load(paths.state)
        state.mark_phase(args.phase, args.status)
        if args.note:
            state.notes.append(args.note)
        state.save(paths.state)
    LOGGER.info("phase %d marked %s for %s", args.phase, args.status, sistema)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """Handle ``list`` subcommand: print all known dissects."""
    del args  # unused
    sistemas = list_dissects()
    if not sistemas:
        print("(no dissects yet)")
        return 0
    for name in sistemas:
        state = get_sistema_state(name)
        if state is None:
            print(f"{name}: <state missing>")
            continue
        progress = sum(
            1 for status in state.phase_status.values() if status == "completed"
        )
        total = len(VALID_PHASES)
        print(
            f"{name}: tipo={state.tipo} phase={state.phase} progress={progress}/{total}"
        )
    return 0


def cmd_checklist(args: argparse.Namespace) -> int:
    """Handle ``checklist`` subcommand: print checklist for all phases."""
    sistema = validate_sistema_name(args.sistema)
    paths = DissectPaths.for_sistema(sistema)
    if not paths.exists():
        LOGGER.error("dissect directory missing for %s", sistema)
        return 1
    print(f"# Checklist: {sistema}")
    for phase in VALID_PHASES:
        items = checklist_phase(phase, paths)
        print(f"\n## Phase {phase}")
        for key, ok in items.items():
            marker = "[x]" if ok else "[ ]"
            print(f"  {marker} {key}")
    return 0


def cmd_template(args: argparse.Namespace) -> int:
    """Handle ``template`` subcommand: emit a template to stdout or file."""
    if args.output:
        target = Path(args.output).expanduser().resolve()
        body = get_template(args.name)
        target.write_text(body, encoding="utf-8")
        LOGGER.info("wrote template %s -> %s", args.name, target)
    else:
        sys.stdout.write(get_template(args.name))
        sys.stdout.write("\n")
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    """Handle ``index`` subcommand: render or regenerate ``dissects/INDEX.md``.

    Without ``--update``, the rendered table is printed to stdout and the
    on-disk file is left untouched. With ``--update``, the file is written
    and the body is also printed for convenience.

    Args:
        args: argparse namespace with ``--update`` flag.

    Returns:
        Exit code 0 on success, 1 when the dissects directory is missing
        or the target cannot be written.
    """
    base = HINDSIGHT_ROOT
    dissects_root = base / "dissects"
    if not dissects_root.exists():
        LOGGER.error("dissects directory missing at %s", dissects_root)
        return 1
    summaries = build_summaries(base)
    body = render_index(summaries)
    if args.update:
        target = dissects_root / "INDEX.md"
        try:
            target.write_text(body, encoding="utf-8")
        except OSError as exc:
            LOGGER.error("failed to write %s: %s", target, exc)
            return 1
        LOGGER.info("wrote %d-row index to %s", len(summaries), target)
    sys.stdout.write(body)
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level argparse parser."""
    parser = argparse.ArgumentParser(
        prog="dissect_utils",
        description=(
            "Helpers for the system-dissector skill — 5 phases: "
            "Triage (1), Deep Dive (2), Document (3), Extract (4), "
            "Handoff (5). Phase 5 produces stack-agnostic handoff/ deliverables."
        ),
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="enable DEBUG logging"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create a new dissect directory + state")
    p_init.add_argument("sistema", help="kebab-case system name")
    p_init.add_argument(
        "--tipo",
        required=True,
        choices=VALID_TIPOS,
        help="target classification",
    )
    p_init.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing state.json",
    )
    p_init.set_defaults(func=cmd_init)

    p_state = sub.add_parser("state", help="print the state.json for a sistema")
    p_state.add_argument("sistema", help="kebab-case system name")
    p_state.set_defaults(func=cmd_state)

    p_phase = sub.add_parser("phase", help="update the status of a single phase")
    p_phase.add_argument("sistema", help="kebab-case system name")
    p_phase.add_argument(
        "phase_num",
        type=int,
        choices=VALID_PHASES,
        help="phase number to update",
    )
    # Backward-compatible flag name (we accept either form).
    p_phase.add_argument(
        "phase",
        type=int,
        choices=VALID_PHASES,
        nargs="?",
        help=argparse.SUPPRESS,
    )
    p_phase.add_argument(
        "--status",
        required=True,
        choices=VALID_STATUSES,
        help="new status for the phase",
    )
    p_phase.add_argument("--note", default="", help="optional note to append")
    p_phase.set_defaults(func=cmd_phase)

    p_list = sub.add_parser("list", help="list all known dissects")
    p_list.set_defaults(func=cmd_list)

    p_check = sub.add_parser(
        "checklist", help="show the per-phase checklist for one sistema"
    )
    p_check.add_argument("sistema", help="kebab-case system name")
    p_check.set_defaults(func=cmd_checklist)

    p_tpl = sub.add_parser(
        "template", help="print a template file (or save it with --output)"
    )
    p_tpl.add_argument(
        "name",
        help=(
            "template name without extension — e.g. 'triagem', "
            "'handoff-readme', 'cross-system-patterns'"
        ),
    )
    p_tpl.add_argument(
        "--output", "-o", help="write template to this file instead of stdout"
    )
    p_tpl.set_defaults(func=cmd_template)

    p_index = sub.add_parser(
        "index",
        help=(
            "render or regenerate dissects/INDEX.md (table of all "
            "dissects, types, phases, progress, last update)"
        ),
    )
    p_index.add_argument(
        "--update",
        action="store_true",
        help="write INDEX.md to disk (default: print to stdout)",
    )
    p_index.set_defaults(func=cmd_index)

    return parser


def _reconcile_phase_args(args: argparse.Namespace) -> argparse.Namespace:
    """Reconcile the dual positional for the ``phase`` subcommand.

    The spec uses ``python dissect_utils.py phase <sistema> <N> --status X``.
    argparse cannot bind two positionals to the same dest cleanly, so we
    accept ``phase_num`` as primary and a legacy ``phase`` fallback, then
    promote the resolved value onto ``args.phase``.
    """
    if getattr(args, "command", None) != "phase":
        return args
    phase_num = getattr(args, "phase_num", None)
    phase_alt = getattr(args, "phase", None)
    if phase_num is None and phase_alt is not None:
        phase_num = phase_alt
    if phase_num is not None:
        setattr(args, "phase", phase_num)
    return args


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)
    _reconcile_phase_args(args)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
