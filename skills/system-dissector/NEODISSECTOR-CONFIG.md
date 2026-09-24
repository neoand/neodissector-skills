# Neodissector Config — Política de edição de código alvo

> **Status**: canônico desde 2026-09-24 (Item 3 — segurança de escrita).
> **Owner**: Anderson + sistema-dissector skill.
> **Inspirado em**: `reversa-config.json` do `sandeco/reversa`
> (spec `legacy-code-edition.md` v1.3, escore 88/100).

---

## 1 · Resumo

O neodissector respeita um arquivo de configuração JSON, `.neodissector/config.json` (ou `neodissector.config.json` na raiz), que controla **se e onde** o neodissector pode escrever código FORA dos seus territórios próprios.

**Default**: `allowLegacyEdits: false` — fail-safe. **Nada** é escrito fora dos territórios do neodissector até o usuário liberar explicitamente.

**AGNÓSTICO de stack** — o schema não menciona stack específico. Pode ser usado por QUALQUER stack destino, framework ou fork.

---

## 2 · Quando você PRECISA dessa config

O neodissector, por default, escreve apenas em seus territórios próprios (`dissects/`, `.neodissector/`, e variantes futuras). Você **NÃO** precisa desta config para:

- ✅ Dissecar um sistema alvo (escrita vai para `dissects/<sistema>/`)
- ✅ Gerar wiki/extract/handoff (idem)
- ✅ Rodar `consolidate_patterns.py`
- ✅ Tudo que é análise sem modificação do código alvo

Você **PRECISA** desta config quando quiser:

- 🔧 Rodar **reconstructor** que escreve código no projeto alvo (não em `dissects/`)
- 🔧 Rodar **refactor time** que aplica transformações (Restructure, Modularize, etc.)
- 🔧 Rodar **migration team** que migra componentes para outra stack
- 🔧 **Bug fix** que altera código do projeto alvo (não apenas do registro do bug)
- 🔧 **Em geral**: QUALQUER operação que toque código do projeto alvo fora dos territórios do neodissector

---

## 3 · Schema (v1)

```json
{
  "version": 1,
  "allowLegacyEdits": false,
  "allowedPaths": []
}
```

| Campo | Tipo | Default | Significado |
|---|---|---|---|
| `version` | int | 1 | Versão do schema. Migrar se mudar. |
| `allowLegacyEdits` | bool | `false` | `false` bloqueia TUDO fora dos territórios. `true` consulta `allowedPaths`. |
| `allowedPaths` | string[] | `[]` | Lista de globs (relativos à raiz do projeto, com `/` normalizado) que CASO `allowLegacyEdits=true`. Se vazio e allow=true → BLOQUEADO. |

---

## 4 · Territórios próprios (sempre graváveis, ignore a config)

Independente de `allowLegacyEdits`:

```
.neodissector/                  — config, state, plano
dissects/                       — dissecações (Phase 1-5 + state.json)
neodissector-sdd/               — alternativo
neodissector_docs/              — futuro (docs time)
neodissector_forward/           — futuro (forward time)
neodissector_bugs/              — futuro (bug time)
neodissector_refactor/          — futuro (refactor time)
_neodissector_sdd/              — mirror legacy (compat)
_neodissector_forward/          — mirror legacy
```

Esses paths são SEMPRE graváveis. Mesmo com `allowLegacyEdits: false`, escrever dentro deles passa.

---

## 5 · Globs em `allowedPaths`

Sintaxe:

- `*` — match qualquer sequência de caracteres **dentro de um segmento** (não atravessa `/`)
- `**` — match qualquer profundidade, inclusive zero segmentos
- `?` — match um caractere
- Sem globs → match exato do path

Exemplos:

```json
{
  "version": 1,
  "allowLegacyEdits": true,
  "allowedPaths": [
    "src/legacy/**",                  // tudo dentro de src/legacy/
    "tests/migration/**",             // tudo dentro de tests/migration/
    "docs/adr/ADR-*.md",              // ADRs específicos
    "packages/voice/src/index.ts"     // arquivo exato
  ]
}
```

**Fail-safe se allow=true e lista vazia**: BLOQUEADO. Lógica: lista vazia geralmente significa "esqueci de preencher", não "liberar tudo".

---

## 6 · Onde colocar o arquivo

Procurado em ordem (primeiro achado vence):

1. `.neodissector/config.json` (preferido)
2. `neodissector.config.json` (na raiz)

Ambos funcionam. Use `.neodissector/` se você já tem um workflow Anderson-canonical; use a raiz se quiser visibilidade pública.

---

## 7 · Inicialização

```bash
# Default seguro (nada liberado)
python3 ~/.agents/skills/system-dissector/resources/scripts/legacy_policy.py init

# Liberação irrestrita (CUIDADO — todo o projeto editável)
python3 ~/.agents/skills/system-dissector/resources/scripts/legacy_policy.py init --allow-all

# Liberação restrita a globs
python3 ~/.agents/skills/system-dissector/resources/scripts/legacy_policy.py init \
  --allow-paths "src/legacy/**" "tests/migration/**"
```

---

## 8 · Consulta programática

```python
from legacy_policy import Policy, PolicyNotConfiguredError, PolicyLoadError

try:
    policy = Policy.load(project_root=Path("."))
except PolicyNotConfiguredError:
    # Config ausente — fail-safe = bloqueado
    policy = None
except PolicyLoadError as e:
    # Config inválida — corrigir
    print(f"Config error: {e}")

if policy:
    decision = policy.check("src/main.py", action="write")
    if decision.allowed:
        # ok
    else:
        print(f"Recusado: {decision.reason}")
```

---

## 9 · Consulta via CLI

```bash
# Status completo
python3 legacy_policy.py status --project-root .

# Verificar um path específico
python3 legacy_policy.py check src/main.py --action write
# ✓ write src/main.py
#   reason: target casa com allowedPaths
#   config: .neodissector/config.json

# Negado:
python3 legacy_policy.py check src/main.py --action write
# ✗ write src/main.py
#   reason: allowLegacyEdits=false (default seguro). Para liberar, edite a config...
#   config: .neodissector/config.json

# Exit codes:
#   0 = permitido
#   1 = negado (gate natural de CI)
#   2 = erro de config (fail-safe)
```

---

## 10 · Política de atualização

| Cenário | Comportamento |
|---|---|
| Atualizar o neodissector num projeto SEM config | `init` continua opcional; fail-safe = bloqueado (sem mudança de comportamento) |
| Atualizar num projeto COM config já existente | Config preservada; nenhuma alteração automática |
| Corromper o JSON manualmente | Próxima checagem retorna PolicyLoadError, BLOQUEADO até corrigir |
| Mudar `allowLegacyEdits` no meio da sessão | Releitura é responsabilidade do caller; o `Policy` é snapshot imutável |

---

## 11 · Decisões de design

| Decisão | Alternativa considerada | Por que essa |
|---|---|---|
| Schema agnóstico (não cita stack) | Citando stack específico (como Reversa cita NeoAI) | Neodissector serve QUALQUER stack destino |
| Defaults `allowLegacyEdits: false` | Default `true` | Segurança: melhor bloquear e o usuário liberar, que liberar e o usuário bloquear |
| Fail-safe = bloqueado | Fail-safe = perguntar | Política de pergunta vira friction; bloqueado + mensagem clara = invariante executável |
| `allowedPaths` vazio + allow=true = BLOQUEADO | allow=true com vazio = liberação irrestrita | "Esqueci de preencher" é comum; "lista vazia = libera tudo" é armadilha |
| Globs com `**` recursivo | Apenas `*` single-level | Casos reais (refactor) precisam atravessar diretórios |
| Sem versionamento automático | Auto-migra | Simplicidade — quebrar é explícito; documentar quando version mudar |
| Sem hook de enforcement em tempo real | Hook OpenCode/Claude bloqueando Write | Hook é specific ao engine; script é engine-agnóstico. OpenCode tem PreToolUse, mas é opcional e separado. |

---

## 12 · Não-objetivos (Non-Goals)

- **Permissões por agente ou usuário** — uma única policy por projeto (v1).
- **UI para editar** — JSON manual, sempre (v1).
- **Integração com git** — pre-commit / branch protection ficam para outros sistemas.
- **Auto-migração entre versões do schema** — quebrar é explícito.
- **Hard enforcement no engine** — guardrail por instrução + script. Hook OpenCode/Claude é camada opcional fora deste script.

---

## 13 · Histórico

- **2026-09-24**: v1 canônico criado. Schema agnóstico de stack. Defaults fail-safe. Script `legacy_policy.py` em `~/.agents/skills/system-dissector/resources/scripts/`. Inspirado em `reversa-config.json` do `sandeco/reversa`.