# Invocation Policy — Eixo model-invoked vs user-invoked

> **Status**: canônico desde 2026-09-24 (Items 1-8).
> **Última atualização**: 2026-09-24 (adição de 6 companion skills do neodissector).
> **Owner**: Anderson + sistema-dissector skill.
> **Inspirado em**: `sandeco/reversa` — `docs/invocation-policy.md` §4.7.
> **Lição herdada**: "declarar invariante sem executor é decoração que envelhece em silêncio".

---

## 1 · O eixo

Toda skill do escopo do **neodissector** é declarada em um de dois estados mutuamente exclusivos:

| Estado | `disable-model-invocation` | Quem invoca | Onde a `description` aparece |
|---|---|---|---|
| **MODEL-invoked** | `false` (explícito) | O modelo decide sozinho, baseado na `description` (gatilhos ricos) | Contexto permanente de toda requisição |
| **USER-invoked** | `true` (explícito) | Apenas o usuário via slash-command OU o orchestrator (`system-dissector`) lendo o `SKILL.md` | Apenas no `ls`/catálogo — fora do contexto |

**Sem terceiro estado.** Toda skill nova NASCER classificada, sem exceção. Sem flag = falha do verificador (`R3`).

---

## 2 · Por que separar

- **Economia de contexto permanente** — as 14 skills user-invoked somavam ~4.500 chars de `description` carregadas em toda requisição, sem o usuário nunca chamá-las pelo nome. Marcando como user-invoked, ficam fora do contexto.
- **Roteamento mais preciso** — o modelo vê só as 1-2 skills que ele pode auto-invocar, em vez de 15 concorrentes com fraseado parecido.
- **Padrão documentado** — cada skill nova é classificada por INTENT (model-invoked se é entry-point de fluxo, user-invoked se é ferramenta ou sub-orchestrator).

---

## 3 · Escopo canônico (16 skills)

### 3.1 MODEL-invoked (1)

| Skill | Função |
|---|---|
| `system-dissector` | Orquestrador mestre do workflow stateful de 5 fases. Sem ele no contexto, modelo não sabe orquestrar dissecação. |

### 3.2 USER-invoked (15)

São alcançáveis por slash-command `/nome` direto OU pelo `system-dissector` lendo o `SKILL.md` e executando no contexto atual:

| Skill | Domínio |
|---|---|
| `reverse-engineer` | RE de binários (IDA/Ghidra/BN/Rizin/Frida) |
| `binary-ninja` | BN 6.0 + MCP server |
| `binary-analysis-patterns` | patterns multi-arch (ARM SVE2, RISC-V, Hexagon, MCore) |
| `protocol-reverse-engineering` | Protocolos de rede (Wireshark/mitmproxy/Scapy) |
| `malware-analyst` | Análise defensiva (FLOSS/CAPA/MobSF) |
| `firmware-analyst` | IoT firmware (binwalk/FACT/QEMU) |
| `memory-forensics` | Volatility 3 / Velociraptor / MemProcFS |
| `dwarf-expert` | DWARF v3-v5 + debuginfod |
| `anti-reversing-techniques` | Themida/VMProtect/anti-Frida/anti-LLM (uso autorizado) |
| `ai-assisted-re` | RE assistida por LLM (BN MCP/IDA-MCP/GhidraMCP) |
| `mobile-re` | Frida 17 + MobSF + apktool + jadx |
| `variant-analysis` | Bug-variant hunt (Semgrep/CodeQL) |
| `audit-context-building` | Análise linha-a-linha ultra-granular |
| `wiki-researcher` | Investigação profunda multi-arquivo |
| `neodoo-integrate` | Companion OPT-IN para um stack específico do Anderson (não-default) |
| `neodissector-reconstructor` | Consome `handoff/` → plano bottom-up → implementa com preservação de tokens |
| `neodissector-brainstorm` | Pipeline Framer→Explorer→Challenger→Arbiter→Pre-Spec antes de dissecar |
| `neodissector-bug` | Memória causal repository-native (Reproduction Capsule, Change Set, closure policy) |
| `neodissector-migration` | Time de migração com parity tests Gherkin (Paradigm → Curator → Inspector) |
| `neodissector-refactor` | 7 especialistas com safety net (restructure/modularize/decouple/...) |
| `neodissector-pricing` | 3 cenários: Effort/Value/Market — nunca número único |

---

## 4 · Custo medido (2026-09-24)

| | Antes | Depois (Cenário B) |
|---|---:|---:|
| Skills model-invoked | 16 | **1** |
| Skills user-invoked | 0 | **21** |
| Chars de description em contexto permanente | ~7.000 | **~374** |
| Tokens permanentes estimados | **~1.750** | **~94** |
| | | **−1.656 tokens (−94%)** |

> ℹ️ A economia em fatura é parcialmente mitigada por prompt caching. O ganho **garantido** é espaço de janela e precisão de roteamento. **Não prometa economia proporcional na fatura**.

---

## 5 · Regras verificadas pelo gate (R1-R8)

| # | Regra | Severidade |
|---|---|---|
| R1 | Frontmatter YAML parseável | erro |
| R2 | Campos `name` + `description` presentes e não-vazios | erro |
| R3 | Campo `disable-model-invocation` explícito (true/false) | erro |
| R4 | Skill em USER_INVOKED → flag = true | erro |
| R5 | Skill em MODEL_INVOKED → flag = false | erro |
| R6 | Flag = true sem classificação → falha (skill órfã) | erro |
| R7 | Description de user-invoked sem gatilho de modelo (`use when`, `digitar '/'`) | erro |
| R8 | Skill canônica listada mas SKILL.md ausente → falha | erro |

---

## 6 · Verificador (canônico, executável)

**Path**: `~/.agents/skills/system-dissector/resources/scripts/verify-invocation.py`

```bash
# APROVADO
python3 ~/.agents/skills/system-dissector/resources/scripts/verify-invocation.py

# JSON output (para CI)
python3 ~/.agents/skills/system-dissector/resources/scripts/verify-invocation.py --json

# Apenas resumo final
python3 ~/.agents/skills/system-dissector/resources/scripts/verify-invocation.py --quiet
```

**Exit code**: `0` = APROVADO, `1` = REPROVADO (gate natural de CI).

---

## 7 · Como adicionar uma nova skill ao escopo

1. **Decidir o lado do eixo**:
   - Será entry-point de fluxo (modelo pode auto-invocar)? → MODEL-invoked
   - Será ferramenta ou sub-orchestrator? → USER-invoked
2. **Atualizar `USER_INVOKED` ou `MODEL_INVOKED`** no script `verify-invocation.py` (lista canônica).
3. **Marcar `disable-model-invocation: true|false`** no frontmatter do `SKILL.md` da nova skill.
4. **Garantir que a `description`** está human-facing (se user-invoked) ou model-facing (se model-invoked, com gatilhos `Use when…`, `Activate quando…`).
5. **Rodar `verify-invocation.py`** — só merge se exit=0.

> **Sem o passo 2**, R6 falhará. Sem o passo 3, R3/R4/R5 falharão. Sem o passo 4, R7 falhará em user-invoked. Toda skill nova entra por esses 5 passos — não pule.

---

## 8 · Como migrar uma skill já existente (de fora do escopo) para dentro

Se você decidir que uma skill em outro lugar de `~/.agents/skills/` deve virar parte do neodissector (ex: uma skill de RE nova do ecossistema):

1. Adicione o nome à lista canônica no script.
2. Verifique o frontmatter atual dela (pode já ter `disable-model-invocation` correto).
3. Se a `description` tiver gatilhos de modelo e for user-invoked, reescreva para human-facing.
4. Rode `verify-invocation.py`. Se falhar, ajuste até passar.

---

## 9 · Histórico

- **2026-09-24** (criação): policy canônico criado. 14 skills RE + 1 companion (neodoo-integrate) marcadas como user-invoked. 2 descrições reescritas (variant-analysis, wiki-researcher). Verificador em gate.
- **2026-09-24** (Items 2-8): adicionadas 6 companion skills do neodissector — `neodissector-reconstructor`, `neodissector-brainstorm`, `neodissector-bug`, `neodissector-migration`, `neodissector-refactor`, `neodissector-pricing`. Total: 21 user-invoked + 1 model-invoked = 22 skills no escopo. Economia de contexto permanente: ~1.750 tokens → ~94 tokens (−94%).
- (próximas) — adicionar novos itens conforme o ecossistema cresce.