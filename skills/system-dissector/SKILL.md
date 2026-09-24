---
name: system-dissector
description: Orquestra dissecação completa de QUALQUER sistema — código aberto, código fechado, binário, app mobile, firmware, serviço/protocolo. Workflow stateful de 5 fases (Triage → Deep Dive → Document → Extract → Handoff) com state.json persistido, validação automática, e 17 templates copy-pasteable. Inclui 6 sub-agent prompts prontos (5 triages + 1 deep-dive).
disable-model-invocation: false
risk: unknown
source: community
date_added: '2026-09-22'
---

# System Dissector

Orquestra dissecação end-to-end de qualquer sistema: GitHub repo, binário fechado, APK/IPA, firmware IoT, serviço/protocolo. Workflow stateful + persistido com state.json, validação automática, templates copy-pasteable, sub-agent prompts prontos. Combina 25+ skills em 5 fases agnósticas de stack destino.

## Quick start (TL;DR)

```bash
# 1. Validar nome do sistema
python3 ~/.agents/skills/system-dissector/resources/scripts/dissect_utils.py init <nome> --tipo source

# 2. Sub-agente Phase 1 (recebe o prompt pronto)
cat ~/.agents/skills/system-dissector/resources/scripts/prompts/triage-source.md

# 3. Phase 2-5 (sub-agentes ou invocação direta)

# 4. Validar outputs a qualquer momento
python3 ~/.agents/skills/system-dissector/resources/scripts/dissect_utils.py checklist <nome>
```

## Use this skill when

- Pegar um sistema open-source (repo GitHub) e gerar documentação estruturada + extrair padrões portáveis
- Pegar um sistema fechado (binário, app, firmware) e dissecar para reconstruir ou interoperar
- Auditar arquitetura de um sistema legado para modernizar ou reescrever
- Mapear API/protocolo proprietário para integrar com seu stack
- Extrair padrões comuns entre múltiplos sistemas para seu próprio produto
- Fazer due diligence técnica antes de integrar uma dependência

## Do not use this skill when

- O alvo é código do seu próprio projeto (use code-reviewer / c4-architecture direto)
- Você só precisa ler/entender 1-2 arquivos (use read tool)
- Tarefa puramente de pentest/exploit (use security-audit + binary-ninja)
- Tarefa de auditoria de segurança sem extração (use 007 / security-audit)

## Companion skills (opt-in, agnósticas de stack)

Cada uma vira `user-invoked` (fora do contexto permanente) e é alcançável por slash-command OU pelo orchestrator lendo o `SKILL.md`.

- **`neodoo-integrate`** — companion OPT-IN para um stack específico do Anderson (NeoAI/NeoAISystems). Use SOMENTE quando o destino do reuso casa com esse stack. Caso contrário, a Fase 5 HANDOFF é suficiente.
- **`neodissector-reconstructor`** — consome `handoff/` e gera plano de reconstrução bottom-up com preservação de tokens. Implementa cada tarefa sob demanda, validando escrita via `legacy_policy`.
- **`neodissector-brainstorm`** — pipeline Framer → Explorer → Challenger → Arbiter → Pre-Spec. **Antes** de `dissect init` quando a ideia ainda é crua. Produz `pre-spec.md` como handoff.
- **`neodissector-bug`** — memória causal repository-native para defeitos (Reproduction Capsule, Correction Change Set, root cause epistemológico, debate 3-modos, closure policy). Vive em `dissects/<s>/bugs/`.
- **`neodissector-migration`** — time de migração para outra stack (Paradigm Advisor → Curator → Strategist → Designer → Inspector) com parity tests Gherkin.
- **`neodissector-refactor`** — 7 especialistas (restructure, modularize, decouple, optimize, simplify, standardize, prune) com safety net obrigatório. ROI por hotpath, não estética.
- **`neodissector-pricing`** — 3 cenários lado-a-lado (Effort / Value / Market) para decidir se compensa portar/reescrever. Nunca número único.

## Recursos auxiliares (`resources/`)

Esta skill vem com artefatos prontos para uso. Estrutura:

```
resources/
├── SKILL.md                          (este arquivo)
├── templates/                        (23 templates copy-pasteable)
│   ├── triagem.md.template
│   ├── deep-dive-architecture.md.template
│   ├── deep-dive-module.md.template
│   ├── deep-dive-data-flows.md.template
│   ├── deep-dive-key-structures.md.template
│   ├── wiki-index.md.template
│   ├── wiki-c4-context.md.template
│   ├── wiki-c4-container.md.template
│   ├── wiki-modules.md.template
│   ├── wiki-decisions.md.template              ← ADRs extraídos (MADR-style) — usado em wiki/, fase 3
│   ├── extract-components.md.template         ← rubrica canônica C1-C6 /60
│   ├── extract-patterns.md.template
│   ├── extract-algorithms.md.template
│   ├── extract-api.md.template                 ← mapeamento de APIs externas
│   ├── license-audit.md.template              ← SPDX + veredito por componente
│   ├── risk-raw.md.template                   ← notas brutas pré-scoring
│   ├── handoff-readme.md.template              ← Phase 5: entry point do handoff
│   ├── handoff-learning-path.md.template       ← Phase 5: trilha pedagógica
│   ├── handoff-implementation-guide.md.template← Phase 5: clean-room recipe
│   ├── handoff-patterns-catalog.md.template    ← Phase 5: catálogo de patterns
│   ├── handoff-decisions.md.template           ← Phase 5: ADRs para o time de implementação
│   ├── handoff-reuse-checklist.md.template     ← Phase 5: reusar direto · adapter · clean-room · não portar
│   ├── handoff-components-priority.md.template ← Phase 5: ranking C1-C6 + roadmap
│   └── cross-system-patterns.md.template       ← consolidação entre múltiplos dissects
├── scripts/                          (Python helpers)
│   ├── dissect_utils.py              (path resolver, state, templates, CLI)
│   ├── state_manager.py              (state.json management)
│   ├── validator.py                  (quality gates, cross-ref)
│   ├── consolidate_patterns.py       (gera dissects/_cross-system-patterns.md)
│   └── README.md                     (CLI usage)
└── scripts/prompts/                  (sub-agent prompts prontos)
    ├── triage-source.md
    ├── triage-binary.md
    ├── triage-mobile.md
    ├── triage-firmware.md
    ├── triage-protocol.md
    └── deep-dive-source.md
```

## Naming convention para diretórios

Use **kebab-case** (lowercase + hyphens). Exemplos válidos:
- `odoo-ce`, `wa-diff`, `meowcaller-fork`, `stripe-sdk`, `nextjs-app-boilerplate`
- ✅ Válido: `acme-api`, `auth-service`, `iot-firmware-v2`
- ❌ Inválido: `acme_api` (use kebab-case), `AcmeAPI` (use lowercase), `acme api` (use hyphens)

Validação automática em `dissect_utils.init` (levanta `ValueError` se inválido).

## State management (state.json)

Cada dissect mantém um `state.json` em `dissects/<sistema>/state.json` que rastreia:

```json
{
  "sistema": "odoo-ce",
  "tipo": "source",
  "phase": 2,
  "phase_status": {
    "1": "completed",
    "2": "in_progress",
    "3": "pending",
    "4": "pending",
    "5": "pending"
  },
  "started_at": "2026-09-22T10:30:00Z",
  "updated_at": "2026-09-22T11:15:00Z",
  "notes": [
    "Phase 1: identified 220+ addons in odoo/addons",
    "Phase 2: deep-diving web, mail, base modules"
  ],
  "metadata": {
    "repo_url": "https://github.com/odoo/odoo",
    "license": "LGPL-3.0",
    "languages": ["Python", "JavaScript"],
    "framework": "Odoo 19"
  }
}
```

### CLI para state management

```bash
# Inicializar dissect
python3 dissect_utils.py init <sistema> --tipo source
python3 dissect_utils.py init <sistema> --tipo binary
python3 dissect_utils.py init <sistema> --tipo mobile
python3 dissect_utils.py init <sistema> --tipo firmware
python3 dissect_utils.py init <sistema> --tipo protocol

# Consultar state (JSON direto no stdout)
python3 dissect_utils.py state <sistema>

# Atualizar phase
python3 dissect_utils.py phase <sistema> 1 --status completed
python3 dissect_utils.py phase <sistema> 2 --status in_progress --note "investigating mail module"

# Checklist (mostra progresso + items por phase)
python3 dissect_utils.py checklist <sistema>
# Output: [x] para completed, [ ] para pending, por phase

# Renderizar template (para stdout)
python3 dissect_utils.py template triagem             # sem extensão .md.template
python3 dissect_utils.py template deep-dive-module    # caminho com kebab-case
python3 dissect_utils.py template wiki-c4-context

# Salvar template em arquivo
python3 dissect_utils.py template triagem --output ./triagem.md

# Listar todos os dissects
python3 dissect_utils.py list
```

### Reality check — comandos disponíveis

Comandos **atualmente implementados** (verificar com `<script> --help` antes de usar):

| Comando | Disponível | Substituto |
|---|---|---|
| `dissect_utils.py init` | ✅ | — |
| `dissect_utils.py state` | ✅ | — |
| `dissect_utils.py phase` | ✅ | — |
| `dissect_utils.py list` | ✅ | — |
| `dissect_utils.py checklist` | ✅ | — |
| `dissect_utils.py template` | ✅ | — |
| `dissect_utils.py index [--update]` | ✅ | regenera `dissects/INDEX.md` (auto-gerado a partir de `state.json`) |
| `dissect_utils.py check` | ❌ | use `checklist` |
| `dissect_utils.py summary` | ❌ | use `checklist` + `state` |
| `dissect_utils.py resume` | ❌ | use `checklist` + `state` |
| `validator.py check` | ✅ | — |
| `validator.py cross` | ✅ | — |
| `validator.py triagem` | ❌ | use `check <sistema>` |
| `validator.py full` | ❌ | use `check <sistema>` |
| `validator.py deep-dive <s> <m>` | ❌ | use `check <s>` (agregado) |

> Outros scripts auxiliares no mesmo diretório (`state_manager.py`,
> `qualifier.py`) podem ter comandos próprios — sempre conferir
> `<script> --help` antes de invocar.

### Recovery / restart

Se o dissect for interrompido (timeout, sessão perdida, etc.):

```bash
# Ver progresso atual
python3 dissect_utils.py checklist <sistema>

# Mostrar últimas notes (via state.json)
python3 dissect_utils.py state <sistema>

# Ver qual é a próxima phase pendente (via phase_status)
```

O state.json é preservado entre execuções. Cada Phase 1-5 mantém checkpoint ao ser marcada como `completed`. Sub-agentes devem sempre chamar `phase <sistema> <N> --status completed --note "<nota>"` antes de finalizar.

## Decision tree: que tipo de alvo é?

Antes de tudo, classifique o alvo. Cada tipo aciona um sub-agent prompt diferente.

```
Alvo?
├── Código fonte (repo Git)         → triage-source.md
├── Binário (PE/ELF/Mach-O)         → triage-binary.md
├── App mobile (APK/IPA)            → triage-mobile.md
├── Firmware IoT (binário + filesystem) → triage-firmware.md
├── Serviço/protocolo (HTTP/WS/gRPC) → triage-protocol.md
└── Múltiplos tipos (ex: app + protocol) → combinar fluxos (2 phase 1 paralelas)
```

### Como invocar a Phase 1

Para cada categoria, há um prompt pronto em `resources/scripts/prompts/`. O fluxo é:

1. Carregar o prompt: `cat resources/scripts/prompts/triage-source.md`
2. Substituir os placeholders (`<sistema>`, `<repo>`)
3. Passar ao sub-agente via `task` tool ou executar diretamente
4. Sub-agente executa Phase 1, preenche `triagem.md`, marca state
5. Continuar para Phase 2 (use `deep-dive-source.md` ou crie variante por tipo)

Exemplo (modo interativo):

```python
# Carregar prompt pronto e substituir os placeholders reais
# (placeholders usados pelos 6 prompts: <sistema>, <repo>, <bin>, <apk>, <pcap>, etc.)
prompt = read_file("resources/scripts/prompts/triage-source.md")
prompt = prompt.replace("<sistema>", "meu-sistema")
prompt = prompt.replace("<repo>", "https://github.com/foo/bar")

task(
  description="Phase 1 triage do meu-sistema",
  prompt=prompt,
  subagent_type="general"
)
```

### TRIAGE-SOURCE (repo Git aberto)

**Detect**: pasta `.git` presente, ou URL GitHub/GitLab, ou arquivo `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` / `odoo-bin` / `__manifest__.py` / `pom.xml`.

**Sub-agent prompt**: `resources/scripts/prompts/triage-source.md`

**Workflow**:
1. `python3 dissect_utils.py init <sistema> --tipo source`
2. `git clone <url>` em `dissects/<sistema>/repo/`
3. Phase 1: language detection, license check, structural recon
4. Phase 2: c4-context → c4-container → c4-component + audit-context-building + wiki-researcher (deep)
5. Phase 3: wiki completa + C4 diagrams
6. Phase 4: extract components (code reusável, patterns, deps)
7. (Phase 5: HANDOFF 5a + opcionalmente 5b se a companion casa com o stack destino)

### TRIAGE-BINARY (binário fechado)

**Detect**: arquivo `.exe`, `.dll`, `.so`, `.dylib`, sem source.

**Sub-agent prompt**: `resources/scripts/prompts/triage-binary.md`

**Workflow**:
1. `python3 dissect_utils.py init <sistema> --tipo binary`
2. Copiar binário para `dissects/<sistema>/bin/`
3. Phase 1: `file`, `checksec`, `diec`, FLOSS, CAPA
4. Phase 2: `reverse-engineer` + `binary-ninja` ou IDA Pro + Frida 17 para dynamic
5. Phase 3: wiki (decoded structures, IAT, strings, IOCs)
6. Phase 4: extract patterns (algoritmos, protocols) + rebuild recipe

### TRIAGE-MOBILE (APK/IPA)

**Detect**: arquivo `.apk`, `.ipa`, `.aab`.

**Sub-agent prompt**: `resources/scripts/prompts/triage-mobile.md`

**Workflow**:
1. `python3 dissect_utils.py init <sistema> --tipo mobile`
   - Não há flag `--platform`; a distinção android/ios é feita na fase
     de deep-dive via sub-agent `triage-mobile.md` + skills específicas.
2. `mobile-re` skill (cobre MobSF 4.5, Frida 17, apktool 3, jadx)
3. Combinar com `reverse-engineer` para native libs
4. Output: extracted code + protocol + bypass techniques

### TRIAGE-FIRMWARE

**Detect**: `firmware.bin`, `update.img`, saída de `binwalk -e`.

**Sub-agent prompt**: `resources/scripts/prompts/triage-firmware.md`

**Workflow**:
1. `python3 dissect_utils.py init <sistema> --tipo firmware`
2. `firmware-analyst` skill (cobre binwalk v3.1, FACT, QEMU emulation)
3. Extrair filesystem, identificar components
4. Output: architecture map + vulnerability list + CVE matches

### TRIAGE-PROTOCOL

**Detect**: Wireshark pcap, BURP export, mitmproxy flow.

**Sub-agent prompt**: `resources/scripts/prompts/triage-protocol.md`

**Workflow**:
1. `python3 dissect_utils.py init <sistema> --tipo protocol`
2. `protocol-reverse-engineering` skill (Wireshark 4.6, mitmproxy 12, Scapy)
3. Mapear endpoints, schemas, crypto
4. Output: protocol spec + python parser + replay capability

## Workflow de 5 fases

### Phase 1: TRIAGE (15-30 min)

**Objetivo**: classificar o alvo, capturar metadados iniciais, definir escopo.

**Ferramentas**:
- Código: `git log --oneline -20`, `git ls-files | head -50`, `tokei` (LOC), `cloc`
- Binário: `file`, `checksec`, `diec`, `floss`, `capa`, `strings`
- Mobile: `apktool d`, `jadx-cli`, MobSF static
- Firmware: `binwalk -e -M`, `file` no extracted
- Protocol: tshark statistics, JA3 fingerprinting

**Sub-agent**: usar prompt apropriado de `resources/scripts/prompts/`

**Output**: `dissects/<sistema>/triagem.md` usando template `triagem.md.template`

**Quality gates** (validador automático):
- [ ] Header completo (data, URL, tipo, classificação)
- [ ] Metadata (linguagem, framework, versão, licença, maintainer)
- [ ] Estrutura de alto nível (tree -L 2)
- [ ] Estatísticas (LOC, deps, tamanho)
- [ ] Risk assessment (CVEs, auth, crypto, permissions)
- [ ] ≥3 deep dive candidates
- [ ] state.json atualizado: phase 1 = completed

### Phase 2: DEEP DIVE (1-4h, paralelizado)

**Objetivo**: entender arquitetura interna + mapear componentes-chave.

**Por sub-tipo**:
- **Source code** (prompt: `deep-dive-source.md`):
  - `audit-context-building` para contexto linha-a-linha
  - `wiki-researcher` (deep mode) para "como funciona X"
  - `c4-context` + `c4-container` + `c4-component` + `c4-code`
  - `code-reviewer` para identificar padrões
- **Binary**:
  - `reverse-engineer` + `binary-ninja` ou IDA Pro + Frida 17
  - FLOSS 3.1.1 + QUANTUMSTRAND β3
  - CAPA 9.4 para capabilities
- **Mobile**: `mobile-re` + MobSF + Frida 17
- **Firmware**: `firmware-analyst` + QEMU emulation + FACT
- **Protocol**: `protocol-reverse-engineering` + Wireshark 4.6 + mitmproxy 12

**Paralelização**: cada módulo/funcionalidade é investigada por um sub-agente independente (use `dispatching-parallel-agents`).

**Output**: `dissects/<sistema>/deep-dive/` usando templates:
- `deep-dive-architecture.md.template`
- `deep-dive-data-flows.md.template`
- `deep-dive-key-structures.md.template`
- `deep-dive-module.md.template` (um por módulo)

**Quality gates**:
- [ ] Cada módulo tem 150-250 linhas (validar com `wc -l`)
- [ ] Pelo menos 1 diagrama mermaid por architecture.md
- [ ] API surface listada para cada módulo
- [ ] Portability assessment para cada módulo
- [ ] data-flows.md tem ≥3 fluxos
- [ ] state.json: phase 2 = completed

### Phase 3: DOCUMENTATION (30-60 min)

**Objetivo**: gerar wiki completa multi-formato.

**Ferramentas**:
- `wiki-page-writer` para cada página
- `wiki-architect` para estrutura geral
- `c4-component` / `c4-code` para diagramas C4
- `docs-architect` para resumo executivo
- `wiki-vitepress` (opcional) para build estático

**Output**: `dissects/<sistema>/wiki/` usando templates:
- `wiki-index.md.template`
- `wiki-c4-context.md.template`
- `wiki-c4-container.md.template`
- `wiki-modules.md.template`
- `wiki-decisions.md.template` (ADRs extraídos — MADR-style; consumido por Phase 5 HANDOFF)
- (opcional) `wiki/api/`, `wiki/security/` usando templates customizados

**Quality gates**:
- [ ] wiki/index.md tem links para todas as seções
- [ ] C4 diagrams em mermaid válido (testar em mermaid.live)
- [ ] Cross-references entre páginas (wiki/ ↔ deep-dive/ ↔ extract/)
- [ ] state.json: phase 3 = completed

### Phase 4: EXTRACT (1-2h)

**Objetivo**: identificar componentes portáveis + padrões reutilizáveis.

**Ferramentas**:
- Manual curation (leitura dos outputs Phase 2/3)
- Rubrica de scoring canônica C1-C6 aplicada por inspeção dos artefatos de fase 2/3

**Output**: `dissects/<sistema>/extract/` usando templates:
- `extract-components.md.template` (com scoring canônico C1-C6 /60 — `Compatibility`, `Code quality`, `License compatibility`, `Maintenance velocity`, `Dependency footprint`, `Reversibility`)
- `extract-patterns.md.template` (≥5 patterns)
- `extract-algorithms.md.template` (se houver algoritmos extraíveis)
- `extract-api.md.template` (mapeamento de APIs externas — outbound/inbound/SDKs)
- `license-audit.md.template` (SPDX + veredito por componente)
- `risk-raw.md.template` (notas brutas pré-scoring)

**Quality gates**:
- [ ] ≥5 componentes com scoring rubric completo (C1-C6 /60)
- [ ] Tier 1/2/3 separados (≥50, 40-49, <40)
- [ ] ≥5 patterns portáveis
- [ ] Cada pattern tem snippet + caso de uso genérico
- [ ] `extract/api.md` lista outbound + inbound (se houver)
- [ ] `license-audit.md` com veredito por componente (§6)
- [ ] `risk-raw.md` com pelo menos 1 item em cada categoria crítica (security, license, multi-tenancy)
- [ ] state.json: phase 4 = completed

### Phase 5: HANDOFF (30-60 min)

**Objetivo**: empacotar **como passar o bastão** para o time que vai implementar ou reaproveitar o sistema. Outputs em `dissects/<sistema>/handoff/`. Companion `neodoo-integrate` continua opt-in para quem quer destino compatível com essa skill — **não obrigatório**.

Esta fase é **agnóstica de stack destino**. Os artefatos servem para QUALQUER consumidor downstream: stack interno do time, framework open-source, fork mantido pelo próprio time, ou simples integração ad-hoc.

**Sub-fluxo (escolher 1)**:
- **5a. HANDOFF agnóstico (obrigatório, padrão)**: produz `handoff/` com os artefatos listados abaixo.
- **5b. INTEGRATE específico (opt-in, via `neodoo-integrate`)**: adiciona `integrate-neoai/` ao lado do `handoff/`, com plano de port específico para o stack alvo dessa skill companion.

**Artefatos obrigatórios** (`dissects/<sistema>/handoff/`):
- `README.md` — entry point com índice dos 6 artefatos + 3 caminhos de leitura (5min / 30min / 2h)
- `learning-path.md` — trilha pedagógica para um engenheiro novo chegar a fluência
- `implementation-guide.md` — guia clean-room por componente Tier 1 (princípio: nunca copiar código)
- `patterns-catalog.md` — ≥5 patterns com snippet + caso de uso genérico (cross-ref `extract/patterns.md`)
- `decisions.md` — ADRs (MADR-style) extraídos do sistema original, para o time novo reusar (base: `wiki/decisions.md`)
- `reuse-checklist.md` — decision matrix: por componente Tier 1/2, marcar `reusar direto | wrap/adapter | clean-room | não portar`
- `components-priority.md` — tabela C1-C6 com ranking + roadmap sugerido

**Quality gates** (todos obrigatórios em `handoff/`):
- [ ] `handoff/README.md` existe, com os 6 artefatos linkados
- [ ] `handoff/learning-path.md` lista pré-requisitos + sequência + marcos de compreensão
- [ ] `handoff/implementation-guide.md` cobre todos os Tier 1 com spec funcional + pseudocódigo + casos de teste
- [ ] `handoff/patterns-catalog.md` ≥5 patterns, cada um com exemplo genérico de uso
- [ ] `handoff/decisions.md` ≥3 ADRs (MADR-style) com cross-ref via `file:line`
- [ ] `handoff/reuse-checklist.md` com decisão explícita (□) por componente Tier 1/2
- [ ] `handoff/components-priority.md` com tabela ordenada por score, esforço (P/M/G), risco
- [ ] state.json: phase 5 = completed

## Output directory structure (canônico)

```
<WORKSPACE>/                      (workspace root do projeto — ex: neodissector/)
├── README.md                        (entry point do workspace)
├── dissects/
│   ├── INDEX.md                     (auto-gerado via `dissect_utils.py index --update`)
│   ├── _archived-pilots/           (dissects cancelados/rascunhos)
│   └── <sistema>/                  (kebab-case)
│       ├── README.md               (entry point — link para todas as fases)
│       ├── triagem.md              (Phase 1 output)
│       ├── deep-dive/              (Phase 2 output)
│       │   ├── architecture.md
│       │   ├── data-flows.md
│       │   ├── key-structures.md
│       │   ├── <modulo1>-analysis.md
│       │   └── ...
│       ├── wiki/                   (Phase 3 output)
│       │   ├── index.md
│       │   ├── README.md
│       │   ├── architecture/
│       │   │   ├── c4-context.md
│       │   │   └── c4-container.md
│       │   ├── modules/
│       │   │   └── addons.md
│       │   ├── api/
│       │   ├── security/
│       │   ├── glossary.md
│       │   └── decisions.md        (ADRs extraídos — MADR-style)
│       ├── extract/                (Phase 4 output)
│       │   ├── components.md       (rubrica canônica C1-C6 /60)
│       │   ├── patterns.md
│       │   ├── algorithms.md
│       │   ├── dependencies.md
│       │   ├── api.md              (mapeamento de APIs externas)
│       │   └── license-audit.md    (SPDX + veredito por componente)
│       ├── risk-raw.md             (notas brutas pré-scoring)
│       ├── handoff/                (Phase 5 output — agnóstico de stack)
│       │   ├── README.md            (entry point do handoff)
│       │   ├── learning-path.md     (trilha pedagógica)
│       │   ├── implementation-guide.md (clean-room recipe)
│       │   ├── patterns-catalog.md  (patterns + exemplos de uso)
│       │   ├── decisions.md         (ADRs do sistema original, via file:line)
│       │   ├── reuse-checklist.md   (reusar direto · adapter · clean-room · não portar)
│       │   └── components-priority.md (ranking C1-C6 + esforço estimado)
│       ├── integrate-<stack>/      (OPT-IN — somente se o stack destino casa com uma companion integrate; ex: integrate-neoai/ é legacy/histórico do pilot Hindsight, mas hoje qualquer companion integrate-<stack> serve)
│       │   ├── integrate.md
│       │   ├── port-plan/
│       │   └── risk-score.md
│       └── state.json              (state management)
└── _cross-system-patterns.md       (consolidação entre todos os dissects — gerada por consolidate_patterns.py)
```

## Path resolver (canônico)

Use sempre os helpers Python em vez de hardcodar paths:

```python
from dissect_utils import DissectPaths, DissectState

# Path para um sistema (root = workspace root do projeto)
paths = DissectPaths.for_sistema("odoo-ce")
print(paths.triagem)    # <workspace>/dissects/odoo-ce/triagem.md
print(paths.deep_dive)  # <workspace>/dissects/odoo-ce/deep-dive/
print(paths.handoff)    # <workspace>/dissects/odoo-ce/handoff/

# Criar estrutura completa
paths.ensure_dirs()

# Verificar se existe
if paths.exists():
    state = DissectState.load(paths.state)
    print(f"Phase atual: {state.phase}")
```

## Quality gates e validação automática

Use `validator.py` para validar outputs a qualquer momento:

```bash
# Validação full (todos os artifacts existentes do sistema)
python3 validator.py check <sistema>

# Cross-validation (links quebrados, refs orfãs)
python3 validator.py cross <sistema>
```

> **Nota**: `validator.py` só expõe `check` e `cross`. Não há subcomandos
> por fase (`triagem`, `deep-dive`, etc.) — `check <sistema>` já agrega tudo
> que estiver presente no diretório do dissect.

O validador retorna:
- ✅ `passed: True` se todos os critérios OK
- ⚠️ `warnings`: issues menores (ex: missing optional field)
- ❌ `errors`: issues bloqueantes (ex: missing required field)

Integre o validador no final de cada phase (sub-agente deve rodar `validator check` antes de marcar phase como completed).

## Integração com BMAD (brownfield documentation)

Esta skill é **complementar** à `bmad-document-project` (existe em `neodoo19_framework/.agents/skills/`):

- **system-dissector** (esta): engenharia reversa de QUALQUER sistema, extração de componentes
- **bmad-document-project**: documentação estruturada brownfield usando método BMAD

**Quando usar cada uma**:
- system-dissector: você não é dono do código (alvo é open-source, third-party, legado sem dono)
- bmad-document-project: você é dono do código (modernizar projeto existente com docs)

**Combine as duas**:
1. system-dissector → extrair components/patterns de um terceiro
2. bmad-document-project → documentar o projeto próprio que incorpora os componentes (qualquer stack: framework interno, fork mantido, app interno, etc.)

## Cross-system pattern extraction (workflow)

Após dissecar **3+ sistemas**, você terá um conjunto de patterns repetidos. O workflow é **agnóstico de stack destino** — só identifica o que se repete.

1. Listar todos os dissects: `python3 dissect_utils.py list`
2. Rodar consolidador: `python3 consolidate_patterns.py` (gera/atualiza `<WORKSPACE>/dissects/_cross-system-patterns.md`)
3. Identificar patterns recorrentes (ex: webhook dispatchers, rate limiters, OAuth flows)
4. Para cada pattern recorrente:
   - Decidir: implementar canônico no seu stack, ou só referenciar via hyperlink?
   - Documentar como **skill dedicada** em `~/.agents/skills/<pattern>.md` (ex: `webhook-dispatcher-pattern`)
   - Listar os sistemas onde apareceu (cross-ref `dissects/<s>/extract/patterns.md#<anchor>`)

**Output consolidado**: `<WORKSPACE>/dissects/_cross-system-patterns.md` (criar se não existir)

```markdown
# Cross-System Architecture Patterns — consolidado de dissects

## Pattern: <nome>
- **Sistemas onde aparece**: <lista>
- **Implementações observadas**:
  - `<sistema1>`: <descrição> + ref `dissects/<sistema1>/extract/patterns.md#<anchor>`
  - `<sistema2>`: <descrição> + ref `dissects/<sistema2>/extract/patterns.md#<anchor>`
- **Recomendação**: <implementar canônico|referenciar|comprar|não usar>
- **Snippet canônico**: <link para skill dedicada, se existir>
```

## Exemplos de uso

### Exemplo 1: dissecar um repo Git pequeno

```bash
# Setup
python3 ~/.agents/skills/system-dissector/resources/scripts/dissect_utils.py init stripe-sdk --tipo source

# Phase 1: triagem (sub-agente)
# Carregar prompt: cat resources/scripts/prompts/triage-source.md
# Sub-agente popula triagem.md

# Phase 2: deep-dive (paralelo por módulo)
# Sub-agentes em paralelo para: customers, payment_intents, webhooks

# Phase 3: docs (wiki)
# Phase 4: extract (componentes + patterns)

# Phase 5: HANDOFF (agnóstico — 7 artefatos em handoff/)
# Opcionalmente: neodoo-integrate (companion opt-in) → integrate-neoai/

# Validação
python3 ~/.agents/skills/system-dissector/resources/scripts/dissect_utils.py checklist stripe-sdk
```

### Exemplo 2: dissecar um binário (sem source)

```bash
python3 dissect_utils.py init some-proprietary-tool --tipo binary
# Phase 1 com prompts/triage-binary.md
# Phase 2 com skills reverse-engineer + binary-ninja + Frida
# Phase 4: extrair algorithms (mesmo sem source, é possível extrair lógica)
```

### Exemplo 3: integração cross-skill (BMAD)

```bash
# Após system-dissector completo, integrar com bmad
python3 ~/.agents/projects/neodoo19_framework/.agents/skills/bmad-document-project/scripts/document.py <projeto-neodoo>

# Cross-review (conselho MiniMax + Kimi)
~/.agents/scripts/cross-review/bmad-cross-review.sh --projeto <projeto> --mode adversarial
```

## Ethical considerations

- Respeite licenças (LGPL → dynamic linking apenas; GPL → open source ou pagar; MIT/Apache → ok com attribution)
- Não copie código proprietário sem autorização
- Marque origens claras no código portado (DMCA / Lei 9.610 art. 104 — Brasil)
- Documente sua metodologia de dissecação para revisão posterior
- Em binários fechados: tenha autorização ouça em bug bounty/CTF/scope definido
- Não use para extrair certificados/chaves/segredos sem autorização

## Checklist final de execução

```markdown
## Phase 1: TRIAGE
- [ ] `dissect_utils.py init <sistema> --tipo <tipo>` executado
- [ ] state.json criado
- [ ] triagem.md preenchido (todos campos obrigatórios)
- [ ] ≥3 deep dive candidates listados
- [ ] state.json: phase 1 = completed
- [ ] Validador passou: `validator.py check <sistema>`

## Phase 2: DEEP DIVE
- [ ] Cada módulo investigado (150-250 linhas cada)
- [ ] architecture.md + data-flows.md + key-structures.md
- [ ] Sub-agentes paralelos usados quando possível
- [ ] Cross-references entre módulos
- [ ] state.json: phase 2 = completed
- [ ] Validador passou: `validator.py check <sistema>` (e `cross` para links)

## Phase 3: DOCUMENTATION
- [ ] Wiki estruturada (index, architecture, modules, api, security, glossary)
- [ ] C4 diagrams em mermaid válido
- [ ] Cross-references entre wiki/ ↔ deep-dive/ ↔ extract/
- [ ] state.json: phase 3 = completed
- [ ] Validador passou: `validator.py check <sistema>`

## Phase 4: EXTRACT
- [ ] components.md com scoring 1-10 priorizado
- [ ] patterns.md com ≥5 patterns (snippet + caso de uso)
- [ ] algorithms.md se houver
- [ ] state.json: phase 4 = completed
- [ ] Validador passou

## Phase 5: HANDOFF (obrigatório)
- [ ] `dissects/<sistema>/handoff/README.md` (entry point com índice)
- [ ] `learning-path.md` (trilha pedagógica com pré-requisitos e marcos)
- [ ] `implementation-guide.md` (clean-room recipe para todos os Tier 1)
- [ ] `patterns-catalog.md` (≥5 patterns com exemplo genérico)
- [ ] `decisions.md` (≥3 ADRs MADR-style com cross-ref `file:line`)
- [ ] `reuse-checklist.md` (decisão explícita por Tier 1/2)
- [ ] `components-priority.md` (ranking + roadmap)
- [ ] state.json: phase 5 = completed
- [ ] Validador passou

## Phase 5b: INTEGRATE específico (OPT-IN)
- [ ] skill companion (ex: `neodoo-integrate`) executada
- [ ] `integrate-neoai/integrate.md` (plano de port)
- [ ] `port-plan/<componente>-port.md` para cada Tier 1
- [ ] `risk-score.md` final
- [ ] state.json: phase 5 = completed (Phase 5 HANDOFF já está pronta)
```

## Recursos / Skills relacionadas

### Análise
- `reverse-engineer` (RE binário completo)
- `binary-ninja` (BN 6.0 dedicado)
- `binary-analysis-patterns` (assembly patterns)
- `ai-assisted-re` (MCP + LLM workflows)
- `anti-reversing-techniques` (proteções)
- `mobile-re` (Android/iOS)
- `firmware-analyst` (IoT)
- `protocol-reverse-engineering` (network)
- `malware-analyst` (malware)
- `memory-forensics` (memory dumps)

### Código fonte
- `audit-context-building` (linha-a-linha)
- `wiki-researcher` (deep mode)
- `wiki-architect`, `wiki-page-writer`, `wiki-onboarding`, `wiki-changelog`, `wiki-qa`, `wiki-vitepress`
- `c4-context`, `c4-container`, `c4-component`, `c4-code`
- `code-reviewer`, `code-review-checklist`, `find-bugs`
- `docs-architect` (docs longas)
- `code-documentation-code-explain`, `code-documentation-doc-generate`
- `codebase-audit-pre-push`

### Output
- `neodoo-integrate` (companion opt-in — port plan específico para um stack interno)

### Orquestração
- `dispatching-parallel-agents` (paralelismo)
- `subagent-driven-development` (sub-agentes)
- `multi-agent-brainstorming` (perspectivas)
- `agent-orchestrator` (orquestração geral)
- `agent-manager-skill` (gerencia agents tmux)
- `bmad-document-project` (brownfield documentation — complementar)

### Cross-review
- `bmad-cross-review` (MiniMax + Kimi + agy conselho)

## References

- BMAD v6.10.0 (`neodoo19_framework`)
- Pesquisa de mercado RE 2025-2026 (`<workspace>/pesquisa-mercado-RE-2025-2026.md`)
- Skills RE 2025-2026 (12 skills atualizadas)
- Odoo 19 standards (`neodoo19_framework/framework/standards/ODOO19_CORE_STANDARDS.md`)
- Convenções do agente principal (`~/.agent/AGENTS.md`, `~/.agent/projects/`) — referência, não destino exclusivo
- C4 model (`https://c4model.com/`)
- Mermaid C4 syntax (`https://mermaid.js.org/syntax/c4.html`)