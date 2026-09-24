"""State management helpers for system-dissector.

Wraps ``DissectState`` with higher-level operations: create-on-demand,
note appending, progress summary, resume-point detection, and integrity
checks. Importable as a library or runnable as a CLI for spot checks.

Usage as a library:
    from state_manager import create, load, update_phase, get_progress_summary

Usage from the shell:
    python state_manager.py summary my-system
    python state_manager.py resume my-system
    python state_manager.py integrity my-system
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from dissect_utils import (
    HINDSIGHT_ROOT,
    VALID_PHASES,
    VALID_STATUSES,
    DissectPaths,
    DissectState,
    get_sistema_state,
    validate_sistema_name,
)

LOGGER = logging.getLogger("system-dissector.state")


# ---------------------------------------------------------------------------
# Convenience wrappers
# ---------------------------------------------------------------------------


def create(sistema: str, tipo: str) -> DissectState:
    """Create a fresh state file, overwriting any existing one.

    Args:
        sistema: Kebab-case system name.
        tipo: Target classification (source/binary/mobile/firmware/protocol).

    Returns:
        The freshly persisted DissectState.
    """
    sistema = validate_sistema_name(sistema)
    paths = DissectPaths.for_sistema(sistema)
    paths.ensure_dirs()
    state = DissectState(sistema=sistema, tipo=tipo)
    # Phase 1 starts in_progress to mirror dissect_utils.cmd_init: a fresh
    # dissect is already running triage and we expect the agent to mark it
    # completed via `dissect_utils phase <sistema> 1 --status completed`.
    state.phase_status[1] = "in_progress"
    state.save(paths.state)
    LOGGER.info("created state for %s (tipo=%s)", sistema, tipo)
    return state


def load(sistema: str) -> DissectState:
    """Load state for ``sistema``; raise ``FileNotFoundError`` when missing.

    Args:
        sistema: Kebab-case system name.

    Returns:
        The current DissectState.

    Raises:
        FileNotFoundError: When no state.json exists.
    """
    sistema = validate_sistema_name(sistema)
    state = get_sistema_state(sistema)
    if state is None:
        paths = DissectPaths.for_sistema(sistema)
        raise FileNotFoundError(f"no state for {sistema} at {paths.state}")
    return state


def update_phase(
    sistema: str,
    phase: int,
    status: str,
    note: str = "",
) -> DissectState:
    """Update a phase status and (optionally) append a note.

    Args:
        sistema: Kebab-case system name.
        phase: Phase number (1-5).
        status: New status string.
        note: Optional free-form note appended to the state.

    Returns:
        The updated DissectState after persistence.

    Raises:
        FileNotFoundError: When no state exists yet.
        ValueError: For invalid phase/status values.
    """
    if phase not in VALID_PHASES:
        raise ValueError(f"invalid phase {phase}")
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid status '{status}'")
    state = load(sistema)
    state.mark_phase(phase, status)
    if note:
        state.notes.append(f"[phase {phase} {status}] {note}")
    paths = DissectPaths.for_sistema(sistema)
    state.save(paths.state)
    LOGGER.info("updated %s phase %d -> %s", sistema, phase, status)
    return state


def append_note(sistema: str, note: str) -> DissectState:
    """Append a timestamped note to the state file.

    Args:
        sistema: Kebab-case system name.
        note: Free-form note content.

    Returns:
        The updated DissectState.

    Raises:
        FileNotFoundError: When no state exists yet.
    """
    if not note.strip():
        raise ValueError("note must be non-empty")
    state = load(sistema)
    stamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    state.notes.append(f"[{stamp}] {note}")
    paths = DissectPaths.for_sistema(sistema)
    state.save(paths.state)
    return state


# ---------------------------------------------------------------------------
# Progress reporting
# ---------------------------------------------------------------------------


@dataclass
class ProgressSummary:
    """Aggregate progress metrics for a dissect."""

    sistema: str
    tipo: str
    current_phase: int
    completed: list[int]
    pending: list[int]
    in_progress: list[int]
    skipped: list[int]
    percent: float
    notes_count: int
    last_updated: Optional[datetime]

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict view of the summary."""
        return {
            "sistema": self.sistema,
            "tipo": self.tipo,
            "current_phase": self.current_phase,
            "completed": self.completed,
            "pending": self.pending,
            "in_progress": self.in_progress,
            "skipped": self.skipped,
            "percent": round(self.percent, 2),
            "notes_count": self.notes_count,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
        }


def get_progress_summary(sistema: str) -> dict[str, object]:
    """Compute and return a JSON-friendly progress summary.

    Args:
        sistema: Kebab-case system name.

    Returns:
        Dict with the keys defined on :class:`ProgressSummary`.
    """
    state = load(sistema)
    return _summary_from_state(state).as_dict()


def _summary_from_state(state: DissectState) -> ProgressSummary:
    """Build a :class:`ProgressSummary` from an in-memory state."""
    completed: list[int] = []
    pending: list[int] = []
    in_progress: list[int] = []
    skipped: list[int] = []
    for phase in VALID_PHASES:
        status = state.phase_status.get(phase, "pending")
        if status == "completed":
            completed.append(phase)
        elif status == "in_progress":
            in_progress.append(phase)
        elif status == "skipped":
            skipped.append(phase)
        else:
            pending.append(phase)
    total = len(VALID_PHASES)
    percent = (len(completed) / total) * 100.0 if total else 0.0
    return ProgressSummary(
        sistema=state.sistema,
        tipo=state.tipo,
        current_phase=state.phase,
        completed=completed,
        pending=pending,
        in_progress=in_progress,
        skipped=skipped,
        percent=percent,
        notes_count=len(state.notes),
        last_updated=state.updated_at,
    )


def mark_resume_point(sistema: str) -> int:
    """Return the phase where the dissect should resume.

    Logic:
        * If a phase is ``in_progress``, return it.
        * Otherwise return the lowest phase that is not ``completed``
          (or ``skipped``) and not currently in_progress.

    Args:
        sistema: Kebab-case system name.

    Returns:
        Phase number in ``VALID_PHASES``.
    """
    state = load(sistema)
    for phase in VALID_PHASES:
        if state.phase_status.get(phase) == "in_progress":
            return phase
    for phase in VALID_PHASES:
        status = state.phase_status.get(phase, "pending")
        if status in {"pending"}:
            return phase
    return max(VALID_PHASES)


# ---------------------------------------------------------------------------
# Integrity validation
# ---------------------------------------------------------------------------


def validate_state_integrity(state: DissectState) -> list[str]:
    """Return a list of human-readable integrity issues found in ``state``.

    Checks performed:
        * Sistema name is still valid (kebab-case).
        * Tipo is a known classification.
        * Every phase key (if present) maps to a known status.
        * ``phase`` field is consistent with the latest ``in_progress``
          entry in ``phase_status``.
        * ``updated_at`` is not earlier than ``started_at``.

    Args:
        state: The state to inspect.

    Returns:
        List of issue descriptions; empty list means state is healthy.
    """
    issues: list[str] = []

    try:
        validate_sistema_name(state.sistema)
    except ValueError as exc:
        issues.append(f"sistema name invalid: {exc}")

    if state.tipo not in {"source", "binary", "mobile", "firmware", "protocol"}:
        issues.append(f"unknown tipo '{state.tipo}'")

    for phase_no, status in state.phase_status.items():
        if phase_no not in VALID_PHASES:
            issues.append(f"phase_status contains invalid phase {phase_no}")
        if status not in VALID_STATUSES:
            issues.append(f"phase_status[{phase_no}] has invalid status '{status}'")

    if state.phase not in VALID_PHASES:
        issues.append(f"current phase {state.phase} outside valid range")

    in_progress_phases = [
        p for p, s in state.phase_status.items() if s == "in_progress"
    ]
    if len(in_progress_phases) > 1:
        issues.append(
            "multiple phases marked in_progress: "
            f"{in_progress_phases}; expected at most one"
        )
    elif in_progress_phases and in_progress_phases[0] != state.phase:
        # Allow the pointer to lag behind (when user just marked a future
        # phase); warn but do not flag as a hard error.
        issues.append(
            "state.phase points to "
            f"{state.phase} but in_progress is on {in_progress_phases[0]}"
        )

    if state.updated_at < state.started_at:
        issues.append("updated_at is earlier than started_at")

    return issues


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_summary(args: argparse.Namespace) -> int:
    """Print a JSON progress summary for ``args.sistema``."""
    sistema = validate_sistema_name(args.sistema)
    try:
        summary = get_progress_summary(sistema)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return 1
    print(json.dumps(summary, indent=2))
    return 0


def _cmd_resume(args: argparse.Namespace) -> int:
    """Print the resume-point phase for ``args.sistema``."""
    sistema = validate_sistema_name(args.sistema)
    try:
        phase = mark_resume_point(sistema)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return 1
    print(f"{sistema}: resume at phase {phase}")
    return 0


def _cmd_integrity(args: argparse.Namespace) -> int:
    """Print integrity issues found in the state file."""
    sistema = validate_sistema_name(args.sistema)
    state = get_sistema_state(sistema)
    if state is None:
        LOGGER.error("no state for %s", sistema)
        return 1
    issues = validate_state_integrity(state)
    if not issues:
        print(f"{sistema}: OK (no issues)")
        return 0
    print(f"{sistema}: {len(issues)} issue(s)")
    for issue in issues:
        print(f"  - {issue}")
    return 0


def _cmd_append(args: argparse.Namespace) -> int:
    """Append a note from the CLI."""
    sistema = validate_sistema_name(args.sistema)
    try:
        append_note(sistema, args.note)
    except (FileNotFoundError, ValueError) as exc:
        LOGGER.error("%s", exc)
        return 1
    print(f"appended note to {sistema}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the state manager CLI."""
    parser = argparse.ArgumentParser(
        prog="state_manager",
        description="State helpers for system-dissector.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="enable DEBUG logging"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_summary = sub.add_parser("summary", help="print progress summary as JSON")
    p_summary.add_argument("sistema")
    p_summary.set_defaults(func=_cmd_summary)

    p_resume = sub.add_parser("resume", help="print the phase to resume at")
    p_resume.add_argument("sistema")
    p_resume.set_defaults(func=_cmd_resume)

    p_integrity = sub.add_parser("integrity", help="run integrity checks on state.json")
    p_integrity.add_argument("sistema")
    p_integrity.set_defaults(func=_cmd_integrity)

    p_append = sub.add_parser("append", help="append a note to state.json")
    p_append.add_argument("sistema")
    p_append.add_argument("note")
    p_append.set_defaults(func=_cmd_append)

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
