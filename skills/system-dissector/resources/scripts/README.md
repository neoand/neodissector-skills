# system-dissector — Helper Scripts

Python helpers for the [`system-dissector`](../SKILL.md) skill. They provide
path resolution, state persistence, template rendering, and quality
validation for the canonical `dissects/<sistema>/` layout.

## Requirements

- Python **3.11+** (uses `Self`, `dataclass(slots=True)`, PEP 695-ish patterns)
- No third-party dependencies — stdlib only (`argparse`, `logging`, `pathlib`, `json`, `re`, `dataclasses`)
- The Anderson uses `uv` for ad-hoc runs; nothing to install

## Layout

```
resources/
├── scripts/
│   ├── dissect_utils.py     # Paths, state dataclass, templates, CLI
│   ├── state_manager.py     # Higher-level state operations + CLI
│   ├── validator.py         # Quality validators for every phase
│   └── README.md            # This file
└── templates/
    └── *.md.template        # Loaded by dissect_utils.get_template
```

## Quick start

```bash
# All scripts are runnable as CLIs from the resources/scripts directory.
cd /Users/andersongoliveira/.agents/skills/system-dissector/resources/scripts

python dissect_utils.py init my-system --tipo source
python dissect_utils.py state my-system
python dissect_utils.py phase my-system 2 --status in_progress --note "started architecture review"
python dissect_utils.py list
python dissect_utils.py checklist my-system
python dissect_utils.py template triagem --output triagem.md

python state_manager.py summary my-system
python state_manager.py resume my-system
python state_manager.py integrity my-system
python state_manager.py append my-system "blocked on CVE review"

python validator.py check my-system
python validator.py cross my-system
```

Exit codes:

- `0` — operation succeeded (validators use 1 when issues are found)
- `1` — user error (missing sistema, invalid input, validation failure)

## Module map

### `dissect_utils.py` — core

Owns the canonical paths and the on-disk state file.

- `HINDSIGHT_ROOT` — constant pointing at `/Users/andersongoliveira/projects/engenharia reversa/HINDSIGHT`
- `DissectPaths` — frozen dataclass with `root`, `triagem`, `deep_dive`, `wiki`, `extract`, `integrate`, `state`, `readme`
  - `DissectPaths.for_sistema(name)` — build paths for one sistema
  - `.ensure_dirs()` — create all output directories
  - `.exists()` — has the dissect directory been created?
- `DissectState` — mutable runtime state (sistema, tipo, phase, phase_status, timestamps, notes)
  - `.load(path)` / `.save(path)` — JSON persistence
  - `.mark_phase(phase, status)` — record progress
  - `.is_complete()` / `.next_phase()` — progress helpers
- `validate_sistema_name(name)` — kebab-case validator
- `get_sistema_state(name)` — load or `None`
- `list_dissects(base)` — all sistema names under `base/dissects`
- `get_template(name)` / `render_template(name, **vars)` — load & fill `*.md.template`
- `checklist_phase(phase, paths)` — bool map of required artefacts per phase

### `state_manager.py` — state wrappers

High-level operations on top of `DissectState`.

- `create(sistema, tipo)` — fresh state (overwrites if present)
- `load(sistema)` — strict load (raises `FileNotFoundError`)
- `update_phase(sistema, phase, status, note="")` — mark + persist + optional note
- `append_note(sistema, note)` — timestamped note
- `get_progress_summary(sistema)` — JSON-friendly dict with completed/pending/in_progress/skipped + percent
- `mark_resume_point(sistema)` — integer phase to resume at
- `validate_state_integrity(state)` — list of integrity issue strings

### `validator.py` — quality gates

Markdown quality checks for each phase output.

- `ValidationResult` — dataclass with `passed`, `errors`, `warnings`, `info`; supports `merge` and pretty `__str__`
- `validate_triagem(content)` — required headings + word count + tipo validation
- `validate_deep_dive(content, modulo)` — per-module analysis checks
- `validate_wiki_index(content, paths)` — heading + broken-link detection
- `validate_extract_components(content)` — scoring rubric presence + column validation + row totals
- `validate_extract_patterns(content)` — at least 5 patterns + code snippets + integration section
- `validate_integrate_plan(content)` — required headings + word count
- `full_validation(sistema)` — runs all of the above in one pass
- `cross_validate(sistema)` — finds broken links and orphan extract docs
- `CrossReferenceIssue` — dataclass describing each broken reference

## Integration with the skill

When `system-dissector` runs, an LLM agent should:

1. Call `dissect_utils.init <sistema> --tipo <kind>` to scaffold the layout
2. After each phase output, run `validator check <sistema>` to confirm quality
3. Run `validator cross <sistema>` to detect broken links before declaring the wiki complete
4. Use `state_manager resume <sistema>` after any restart to know which phase to continue at
5. Persist progress with `dissect_utils phase <sistema> <N> --status completed`

## Conventions

- All public APIs return `Path` objects (no string paths)
- All scripts log via the `logging` module (no `print` for diagnostics)
- Errors are surfaced as exceptions, not silent failures
- Templates use `<PLACEHOLDER>` tokens; unknown keys raise `KeyError`
- Sistema names are always kebab-case alphanumeric (`my-system-2`)
- Phase numbers are always `1..5`; types are always one of `VALID_TIPOS`
