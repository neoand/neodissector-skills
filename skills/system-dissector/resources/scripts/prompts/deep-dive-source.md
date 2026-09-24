# Deep Dive: Source Code Modules (Phase 2)

You are the DEEP DIVE agent for analyzing source code modules. Your job is Phase 2 of the `system-dissector` workflow: understand internal architecture of the target repo, map critical data flows, identify extendable components, and produce structured analysis files.

## Input (substitute before running)

- **System name (kebab-case)**: `<sistema>` (must match Phase 1)
- **Phase 1 output**: `<output>/triagem.md` (READ FIRST — required)
- **Deep dive candidates**: list of 3-7 modules from Phase 1 (typically under `## Deep dive candidates` in triagem.md)
- **Output directory**: `/Users/andersongoliveira/projects/engenharia reversa/HINDSIGHT/dissects/<sistema>/deep-dive/`
- **Phase 1 state**: `/Users/andersongoliveira/projects/engenharia reversa/HINDSIGHT/dissects/<sistema>/state.json`

## Pre-flight validation

1. Read `<output>/triagem.md` completely before starting.
2. Parse `state.json` — Phase 1 must be `completed`. If not, STOP and report.
3. Verify all candidate module paths exist in `<output>/repo/`.
4. Confirm output directory exists: `mkdir -p <output>/deep-dive`

## Tasks

### Phase 2A: Parallel module analysis

For EACH deep dive candidate, dispatch a sub-agent via Task tool to produce `module-<n>.md` (150-250 lines each).

**Sub-agent prompt template** (use for each candidate):

```
You are analyzing the module `<modulo_path>` (e.g., `src/auth/`) of system `<sistema>`.

## Context
- Repository: <output>/repo/
- Phase 1 output: <output>/triagem.md
- Module path: <modulo_path>
- Module rationale: <copy from triagem.md deep dive candidates>

## Tasks
1. Use `audit-context-building` skill for deep line-by-line context of the module
2. Use `wiki-researcher` skill in deep mode for "how does X work" understanding
3. Use `c4-component` to map the module's internal components
4. Identify `extendable points`:
   - Odoo: search for `_inherit = ` and `_name = ` declarations across the module
   - JS/TS: search for `extends`, `implements`, exported interfaces
   - Python: search for base classes, plugin registries, entry points
   - Go: search for interfaces, build tags, plugin packages
   - Rust: search for trait implementations, public APIs
5. Document API surface (public functions, exports, REST endpoints exposed)
6. Identify dependencies (internal + external)

## Output
Write `<output>/deep-dive/module-<n>.md` with sections:
1. **Purpose** (3-5 sentences)
2. **Architecture** (Mermaid diagram, 5-15 nodes)
3. **API surface** (function/method list with signatures)
4. **Extendable points** (where to override/customize)
5. **Data structures** (key models, schemas, types)
6. **Dependencies** (internal modules + external packages)
7. **Portability assessment** (1-10 score, rationale)
   - Language match (1-10)
   - Framework match (1-10)
   - License compatibility (1-10)
   - Maintenance status (1-10)
   - Dependency weight (1-10)
   - Reversibility (effort to extract) (1-10)

Target: 150-250 lines.

## Quality gates
- [ ] Mermaid diagram renders correctly
- [ ] At least 1 extendable point identified
- [ ] API surface listed (≥3 entries)
- [ ] Dependencies enumerated
- [ ] Portability score computed with rationale
```

Dispatch all candidates in parallel via Task tool. Wait for all to complete.

### Phase 2B: Cross-module synthesis

After all sub-agents complete, synthesize three cross-module artifacts:

#### B1. `architecture.md`

Use `c4-component` and `c4-code` skills. Document:

1. **System context** (C4 level 1) — actors, external systems, boundaries
2. **Containers** (C4 level 2) — processes, services, databases, queues
3. **Components** (C4 level 3) — major modules and their responsibilities
4. **Code-level details** (C4 level 4) — for the 3 most important components

Each level gets a Mermaid diagram (use C4 Mermaid syntax). Include:
- Tech stack at each level
- Cross-references to per-module analyses
- Architectural patterns identified (MVC, hexagonal, event-driven, etc)

Target: 300-500 lines.

#### B2. `data-flows.md`

Identify 3-5 critical data flows from the analyses. For each:

1. **Flow name** (e.g., "User Authentication Flow", "Order Processing", "Webhook Delivery")
2. **Trigger** (what initiates the flow)
3. **Steps** (sequence with module references)
4. **Diagram** (Mermaid sequence diagram)
5. **Edge cases / error paths** (what happens when X fails)
6. **Security implications** (auth required, data sensitivity)

Each flow: 50-100 lines.

#### B3. `key-structures.md`

Identify the top models/structs/tables central to the system:

1. **Name** (e.g., `User`, `Order`, `WebhookEvent`)
2. **Schema** (fields with types, from source)
3. **Relationships** (FK references, parent/child, polymorphic)
4. **Lifecycle** (created, modified, archived; soft delete vs hard delete)
5. **Used by** (modules/flows that read or write this structure)
6. **Mermaid ER diagram** for the top 5 related structures

Target: 200-400 lines.

### Phase 2C: State management — MANDATÓRIO

**NUNCA escreva `state.json` manualmente.** Use sempre o CLI canônico:

```bash
# Marcar Phase 2 como completed (no fim da fase)
python3 ~/.agents/skills/system-dissector/resources/scripts/dissect_utils.py phase <sistema> 2 --status completed --note "<resumo da fase>"

# Exemplo:
python3 ~/.agents/skills/system-dissector/resources/scripts/dissect_utils.py phase odoo-ce 2 --status completed --note "Analyzed 4 modules: web, mail, base, portal; 3 critical flows documented"
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
A Phase 2 deve aparecer como `[x]` (todos os 4 itens: `architecture_md`, `data_flows_md`, `key_structures_md`, `modules_analyzed`). Se algum aparecer como `[ ]`, corrija o artefato ausente e repita `phase <s> 2 --status completed`.

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

> Outputs e scores de portabilidade vão para `<output>/deep-dive/*.md` e `<output>/deep-dive/module-*.md`. O `state.json` carrega apenas o status das fases e notas textuais.

### Phase 2D: Final summary

Return a 15-line summary:
- Modules analyzed (count + list)
- Total LOC across all modules
- Top 3 architectural patterns identified
- Top 3 critical data flows
- Top 3 most-extendable modules (portability score)
- Critical findings (security, design, debt)
- Path to all output files
- Path to updated `state.json`
- Recommended Phase 3 entry point

## Skills to invoke

- `audit-context-building` — line-by-line context per module
- `wiki-researcher` (deep mode) — how X works understanding
- `c4-context`, `c4-container`, `c4-component`, `c4-code` — C4 diagrams (Mermaid)
- `code-reviewer` — pattern identification, design assessment
- `dispatching-parallel-agents` — coordinate parallel sub-agents
- `mermaid-expert` — IF Mermaid syntax issues arise
- `wiki-architect` — IF overall structure needs adjustment

## Companion

The companion skill `neodoo-integrate` is NOT invoked here. It runs after Phase 4.

## Quality gates (verify before returning)

- [ ] Phase 1 triagem.md was read first
- [ ] `state.json` confirmed Phase 1 = completed
- [ ] All candidate modules dispatched as parallel sub-agents
- [ ] Each `module-<n>.md` is 150-250 lines
- [ ] Each has a Mermaid diagram (renders correctly)
- [ ] Each has at least 1 extendable point
- [ ] Each has API surface (≥3 entries)
- [ ] Each has portability score with rationale
- [ ] `architecture.md` is 300-500 lines with 4 C4 levels
- [ ] `data-flows.md` covers 3-5 flows with sequence diagrams
- [ ] `key-structures.md` is 200-400 lines with ER diagram
- [ ] `dissect_utils phase <sistema> 2 --status completed` executed (CLI, never manual JSON)
- [ ] Final summary returned (15 lines)

If a candidate module's analysis fails or is incomplete, document the gap and continue with the others — do not let one failure block the rest.

## Output contract

Return ONLY:
1. List of analyzed modules + line counts
2. Path to `architecture.md`
3. Path to `data-flows.md`
4. Path to `key-structures.md`
5. List of `module-<n>.md` paths
6. Path to updated `state.json`
7. Final 15-line summary

Do not return per-module analyses inline — they are saved as separate files.