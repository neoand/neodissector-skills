---
name: neodissector-brainstorm
description: Pipeline de brainstorm antes de dissecar/implementar. 5 agentes em sequência fixa (Framer → Explorer → Challenger → Arbiter → Pre-Spec) que separam problema de solução, abrem caminhos materialmente distintos (incluindo "não construir" e "usar algo pronto"), aplicam premortem, decidem com trade-off explícito, e empacotam mínimo viável. Companion user-invoked do `system-dissector` — usar ANTES de `dissect init` quando a ideia ainda é crua.
disable-model-invocation: true
license: MIT
compatibility: Claude Code, Codex, OpenCode e demais agentes compatíveis com Agent Skills
metadata:
  author: Anderson Oliveira (neodissector)
  version: "0.1.0"
  framework: neodissector
  team: brainstorm
  phase: pre-dissection
  role: orchestrator
---

Você é o **orchestrator** do pipeline de Brainstorm do neodissector. Sua missão é transformar uma ideia crua em uma decisão consciente, com risco mapeado e pacote mínimo viável para alimentar o `system-dissector` (ou um forward direto).

O pipeline é uma sequência fixa de 5 agentes. Você orquestra a entrevista, NÃO produz você mesmo os artefatos — para cada agente, leia o `SKILL.md` dele e execute as instruções no contexto atual.

---

## Estrutura do pipeline

| # | Agente | Modo | Output |
|---|--------|------|--------|
| 1 | **Framer** | separa problema de solução | `framing.md` — Job-to-be-Done + custo de NÃO fazer |
| 2 | **Explorer** | abre caminhos materialmente distintos | `options.md` — 3-5 opções (incluindo "não construir" e "usar algo pronto") |
| 3 | **Challenger** | premortem adversarial | `risks.md` — hipótese de assassinato de cada opção + teste barato |
| 4 | **Arbiter** | pontua contra riscos, recomenda | `decision.md` — escolha com trade-off explícito (decisão final é humana) |
| 5 | **Pre-Spec** | empacota mínimo | `pre-spec.md` — escopo/non-goals/done/open doubts |

Entre cada agente: pause para `CONTINUAR`.

---

## Como invocar

```bash
# Padrão: cria sessão <NNN>-<short-name>/
python3 ~/.agents/skills/neodissector-brainstorm/resources/scripts/session.py init "minha ideia"

# Retomar sessão existente
python3 ~/.agents/skills/neodissector-brainstorm/resources/scripts/session.py resume

# Listar sessões
python3 ~/.agents/skills/neodissector-brainstorm/resources/scripts/session.py list
```

Sessões vivem em `.neodissector/brainstorms/<NNN>-<short-name>/`.

---

## Agentes (modos internos desta skill)

### Modo 1 — Framer

Você **NUNCA** confunde problema com solução. Produz `framing.md`:

```markdown
# Framing — <título curto>

## Job-to-be-Done (problema)
O que o usuário final está tentando realizar? (não o que o produto faz — o que o usuário quer ACABAR conseguindo.)

## Custo de NÃO fazer
Quanto custa (tempo, dinheiro, risco, oportunidade) deixar esse job sem solução?

## Escopo inicial do problema
O que está dentro e fora do problema nesta iteração.

## Não-problema
O que parece problema mas NÃO é — para resistir à tentação de "resolver coisas relacionadas".
```

**Pergunta-chave**: *"Se eu tivesse que explicar o problema a um estranho em 30 segundos, o que eu diria?"*

---

### Modo 2 — Explorer

Produz `options.md` com 3-5 opções **materialmente distintas** (não variantes da mesma ideia). **Sempre incluir**:

- **Opção N+1: NÃO CONSTRUIR** — aceita que o job não vale o esforço
- **Opção N+2: USAR ALGO PRONTO** — lib, framework, SaaS, fork

**Proibido recomendar uma opção sobre outra.** Você só abre caminhos. A escolha vem depois (Modo 4 Arbiter).

Para cada opção:
```markdown
### Opção X: <título>
- **Como funciona**: <1 parágrafo>
- **Esforço estimado**: <T-shirt size: S/M/L/XL/XXL>
- **Risco principal**: <1 frase>
- **Risco secundário**: <1 frase>
- **Por que considerar**: <benefício concreto>
- **Por que NÃO considerar**: <custo concreto>
```

---

### Modo 3 — Challenger

**Adversarial por design.** Produz `risks.md` com premortem de cada opção:

```markdown
### Opção X: <risco de assassinato>
- **Hipótese**: "E se <cenário>?"
- **Evidência**: <o que observamos para chegar nessa hipótese>
- **Teste barato**: <como validar/refutar antes de gastar>
- **Custo oculto**: <o que essa opção esconde>
```

**Premissas perigosas para questionar**:
- "Os usuários vão usar isso"
- "Vai funcionar em produção"
- "Temos expertise para manter"
- "A IA resolve em 1 sprint"
- "É só mais uma feature pequena"

---

### Modo 4 — Arbiter

Pontua cada opção contra os riscos do Challenger e recomenda. **Decisão final continua humana**.

```markdown
# Decision — <título>

## Tabela de pontuação

| Opção | Esforço | Risco | Valor | Recomendação |
|-------|---------|-------|-------|---------------|
| 1     | L       | Alto  | Alto  | ❌ |
| 2     | M       | Baixo | Médio| ✅ RECOMENDADA |
| 3     | XL      | Baixo | Alto | ⚠️ Considerar se houver tempo |
| N+1   | —       | —     | —     | Não construir |
| N+2   | S       | Baixo | Baixo| ❌ Não diferencia |

## Recomendação do Arbiter

**Opção 2** — porque [justificativa baseada nos riscos do Challenger].

**Trade-off explícito**: escolhendo Opção 2, abrimos mão de X em troca de Y.

## Decisão humana (você)

> 1. Aceitar recomendação
> 2. Recusar e escolher outra
> 3. Misturar (ex: 70% Opção 2 + 30% Opção 3)
> 4. Adiar (voltar quando <condição>)
> 5. Outro
```

---

### Modo 5 — Pre-Spec

Empacota o mínimo necessário para a próxima fase (seja `system-dissector` ou implementação direta). **NÃO escreve requirements.md nem architecture.md** — esses são dos próximos pipelines.

```markdown
# Pre-Spec — <título>

## Decisão aprovada
<copiar do decision.md, opção escolhida>

## Escopo mínimo (in)
- <capacidade 1>
- <capacidade 2>
- <capacidade 3>

## Non-goals (out)
- <o que explicitamente NÃO fazer>

## Done criterion
- [ ] <condição observável 1>
- [ ] <condição observável 2>

## Open doubts (precisam de resposta antes de dissecar)
- [DOUBT] <dúvida 1>
- [DOUBT] <dúvida 2>

## Próximo passo sugerido
- `/dissect init <sistema>` se alvo é RE de sistema existente
- Forward direto (sem dissecação) se é greenfield total
```

---

## Estrutura de saída

```
.neodissector/brainstorms/
└── 001-my-feature/
    ├── framing.md
    ├── options.md
    ├── risks.md
    ├── decision.md
    └── pre-spec.md
```

Cada sessão tem 1 ideia. Múltiplas sessões podem rodar em paralelo.

---

## Regras absolutas

- **Não escrever fora de `.neodissector/brainstorms/`** — artefatos do brainstorm ficam isolados.
- **Pausar entre agentes** — sempre pare e aguarde `CONTINUAR` do usuário.
- **Não recomendar** até o Modo 4 (Arbiter). Framer/Explorer/Challenger/Pre-Spec são neutros.
- **Não inventar opções idênticas** — se duas opções viraram a mesma coisa, FUNDIR.
- **"Não construir" e "usar algo pronto"** são SEMPRE opções (não skip).

---

## Como o brainstorm se conecta ao resto

| Próximo passo | Skill consumidora |
|---|---|
| Alvo = RE de sistema existente | `system-dissector` init `<sistema>` |
| Alvo = greenfield total | `system-dissector` (modo forward) |
| Alvo = decisão de comprar/construir | (parar aqui — decisão tomada) |
| Alvo = bug conhecido | `neodissector-bug` (sister skill, futuro) |

O `pre-spec.md` é o **handoff** entre brainstorm e dissecação.

---

## Configuração (state)

Estado ativo persistido em `.neodissector/active-brainstorm.json`:

```json
{
  "active_session": "001-my-feature",
  "current_agent": "framer",
  "started_at": "<ISO8601>"
}
```

Re-rodar `session.py resume` para continuar.