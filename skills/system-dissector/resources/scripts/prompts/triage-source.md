# Triage: Source Code Repository (Phase 1)

You are the TRIAGE agent for a Git source repository. Your job is Phase 1 of the `system-dissector` workflow: classify the target, capture initial metadata, and define the scope for Phase 2 (Deep Dive).

## Input (substitute before running)

- **Repository URL or local path**: `<repo>` (e.g. `https://github.com/owner/project` or `/path/to/local/repo`)
- **System name (kebab-case)**: `<sistema>` (e.g. `my-saas-app`, `neodoo-mkt`)
- **Output directory**: `/Users/andersongoliveira/projects/engenharia reversa/HINDSIGHT/dissects/<sistema>/`

## Pre-flight validation

1. Verify `<sistema>` is kebab-case (`^[a-z][a-z0-9-]*[a-z0-9]$`). If not, normalize and warn.
2. Check output directory does not already exist OR confirm overwrite intent.
3. Confirm `<repo>` is reachable: `git ls-remote <repo>` for URLs, or `test -d <repo>/.git` for paths.

## Tasks (execute in order)

### 1. Create directory structure

```
mkdir -p "<output>/{repo,deep-dive,wiki/architecture,wiki/modules,wiki/api,wiki/security,extract,integrate}"
```

### 2. Clone the repository (shallow)

For remote URLs:
```
git clone --depth=10 <repo> "<output>/repo"
```

For local paths:
```
cp -R <repo>/. "<output>/repo/"   # preserve .git if present
```

If the repo needs full history for velocity analysis, deepen selectively:
```
cd "<output>/repo" && git fetch --unshallow
```

### 3. Detect language and framework

Run from `<output>/repo/`:
- `tokei .` for LOC per language (fallback: `cloc . --json`)
- `ls package.json pyproject.toml Cargo.toml go.mod pom.xml build.gradle __manifest__.py Gemfile composer.json 2>/dev/null` to identify manifest files
- Inspect `package.json` `engines`, `pyproject.toml` `requires-python`, etc. for version constraints

### 4. Detect license

- Check for `LICENSE`, `LICENSE.md`, `LICENSE.txt`, `COPYING`
- Extract SPDX identifier when possible (look for `SPDX-License-Identifier:` headers or `license` field in manifest)

### 5. Identify maintainer and velocity

- `git log --oneline | head -20` (recent commits)
- `git log --pretty=format:'%an' | sort | uniq -c | sort -rn | head -5` (top contributors)
- `git log --since='6 months ago' --oneline | wc -l` (commits last 6 months)
- `git shortlog -s -n` (summary by author)
- For releases: check tags (`git tag --sort=-creatordate | head -10`) and `CHANGELOG.md` if present

### 6. Map high-level structure

```
tree -L 2 -I 'node_modules|.git|dist|build|__pycache__|.venv|venv|target' --noreport
```

If `tree` not available: `find . -maxdepth 2 -not -path '*/.git*' -not -path '*/node_modules*' | sort`

### 7. Risk assessment

- **CVEs in dependencies**:
  - Python: `pip-audit -r <(grep -v '^#' requirements.txt 2>/dev/null) 2>&1 || true`
  - JS/TS: `npm audit --json 2>&1 || true`
  - Rust: `cargo audit 2>&1 || true`
  - Go: `govulncheck ./... 2>&1 || true`
- **Hardcoded secrets** (initial sweep): `gitleaks detect --no-banner --redact 2>&1 || true`
- **Auth weaknesses**: presence of `password`, `secret`, `token` in code paths (grep for `def authenticate`, `jwt`, `oauth`)
- **Crypto usage**: grep for `md5`, `sha1`, `random`, `Math.random` (weak primitives)

### 8. Identify 3-7 deep dive candidates

Look for modules that are:
- High-traffic (entry points: `main.py`, `index.js`, `app.py`, `wsgi.py`, `server.go`)
- Business-critical (auth, billing, core domain logic)
- Complex (high cyclomatic complexity, large LOC count)
- Inheritable (`_inherit` for Odoo, `extends` for JS, `class X(Base)` patterns)

Document each with: name, path, rationale for deep dive, expected sub-skill (c4-component, wiki-researcher, etc).

### 9. Write `triagem.md`

Use the canonical template from `system-dissector/SKILL.md` § "Templates de output" (template `triagem.md`). Fill all fields:

- Metadados básicos (linguagem, framework, versão, licença, maintainer, releases, velocity)
- Estrutura (tree -L 2)
- Estatísticas (LOC, deps count, MB)
- Risk assessment inicial (CVEs, auth, crypto, permissions)
- Deep dive candidates (3-7 with rationale)
- Notas (observações durante triagem)

Target: 200-300 lines.

### 10. State management — MANDATÓRIO

**NUNCA escreva `state.json` manualmente.** Use sempre o CLI canônico:

```bash
# Marcar Phase 1 como completed (no fim da fase)
python3 ~/.agents/skills/system-dissector/resources/scripts/dissect_utils.py phase <sistema> 1 --status completed --note "<resumo da fase>"

# Exemplo:
python3 ~/.agents/skills/system-dissector/resources/scripts/dissect_utils.py phase odoo-ce 1 --status completed --note "Identified 220+ addons; deep dive candidates: web, mail, base"
```

**NÃO use**:
- ❌ Escrever JSON manualmente (schema quebrado)
- ❌ `echo '{...}' > state.json`
- ❌ Editar state.json via Edit tool

**Validação pré-saída**:
Antes de retornar ao orquestrador, execute:
```bash
python3 ~/.agents/skills/system-dissector/resources/scripts/dissect_utils.py checklist <sistema>
```
A Phase 1 deve aparecer como `[x]`. Se aparecer `[ ]`, repita `phase <s> 1 --status completed`.

#### Schema de state.json (referência)

O `state.json` é gerenciado pelo CLI. Schema atual:
```json
{
  "sistema": "<kebab-case>",
  "tipo": "source|binary|mobile|firmware|protocol",
  "phase": 1-5,
  "phase_status": {"1": "completed|in_progress|pending", ...},
  "started_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "notes": ["..."],
  "metadata": {}
}
```

Você NÃO escreve esse arquivo. O CLI gerencia. Use `phase ... --status completed` ao fim de cada fase.

### 11. Final summary

Return a 10-line summary including:
- System name + classification
- Language/framework + LOC
- License + risk level (low/medium/high)
- Top 3 deep dive candidates
- Path to `triagem.md`
- Path to `state.json`
- Any blockers or anomalies encountered

## Skills to invoke

- `audit-context-building` — initial line-by-line recon of key files (entry points, manifests)
- `c4-context` — macro system context view (actors, external systems)
- `find-skills` (if you need to discover additional skills during execution)

## Companion

The companion skill `neodoo-integrate` is NOT invoked here. It runs after Phase 4 (Extract).

## Quality gates (verify before returning)

- [ ] System name is valid kebab-case
- [ ] Directory structure created at canonical path
- [ ] Repository cloned shallow (depth=10) OR copied
- [ ] Language and framework detected with evidence (manifest file paths)
- [ ] License identified (SPDX identifier or file path)
- [ ] Maintainer and velocity stats present (commits/month)
- [ ] `tree -L 2` output included in `triagem.md`
- [ ] LOC stats from `tokei` or `cloc` included
- [ ] At least 3 deep dive candidates documented with rationale
- [ ] `triagem.md` is 200-300 lines
- [ ] `dissect_utils phase <sistema> 1 --status completed` executed (CLI, never manual JSON)
- [ ] Final summary returned (10 lines)

If any gate fails, document the gap in the summary and proceed with a partial `triagem.md` (mark sections as `[NOT VERIFIED — reason]`).

## Output contract

Return ONLY:
1. Path to `triagem.md`
3. Path to `state.json`
4. Final 10-line summary

Do not return intermediate logs unless explicitly requested.