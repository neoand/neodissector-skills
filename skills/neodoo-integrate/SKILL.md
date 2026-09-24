---
name: neodoo-integrate
description: Companion skill to system-dissector. Converts dissecação outputs into port/integration plans for NeoAI/NeoAISystems. Maps extracted components to NeoAI architecture, scores reusability, generates integration checklists, validates against NeoAI/NeoAISystems constraints. Use after running system-dissector on a target system.
disable-model-invocation: true
risk: unknown
source: community
date_added: '2026-09-22'
---

# Neodoo Integrate — Port/Integration Planning for NeoAI/NeoAISystems

Companion skill to `system-dissector`. Recebe os artefatos de dissecação (componentes extraíveis, patterns portáveis, API mappings, wiki) e gera **planos de port/integration** concretos para NeoAI/NeoAISystems, NeoGo, Nuxt-Agendador, UniversalOne, Odoo 19 + NeoDoo.

## TL;DR

- **Quem chama:** depois de rodar `system-dissector` em um sistema-alvo (Odoo Enterprise, DeskcommCRM, WaCalls, qualquer SaaS), você recebe `dissects/<sistema>/extract/*.md` + `dissects/<sistema>/wiki/*.md`.
- **O que entrega:** (1) scoring de reusabilidade 1-10 por componente; (2) classificação do tipo de port (source-port / wrap / extract-pattern / reference / drop-in); (3) plano de port detalhado por componente; (4) gates de validação BMAD; (5) extração de patterns cross-system.
- **Não é:** um portador automático. A skill **planeja**, **documenta** e **valida** — humanos (Anderson) aprovam antes de qualquer merge em NeoAI/NeoAISystems.
- **Stack-alvo (2026-09-22):** Nuxt 4 + Vue 3.5 + Tailwind v4 + Pinia (frontend) | Odoo 19 CE (backend primário) | Go 1.26 + Gin (NeoGo, pbx-bridge) | PostgreSQL 17 | Docker Swarm em VPS IONOS `74.208.36.71` | Vercel AI SDK + cascata MiniMax → Groq → Gemini.

## Use this skill when

- Você terminou uma dissecação de sistema (skill `system-dissector`) e precisa decidir **o que vale a pena portar** para NeoAI/NeoAISystems.
- Você precisa de um **scoring objetivo 1-10** para priorizar componentes extraíveis.
- Você precisa gerar **planos de port** detalhados em Odoo 19 modules, Nuxt 4/Vue 3 components, ou NeoGo services.
- Você quer extrair **patterns comuns** entre múltiplos sistemas disseccados (ex: "todos usam webhook dispatcher com retry exponencial").
- Você precisa **validar a viabilidade** de um port contra constraints NeoAI (multi-tenant, RLS, BMAD, licenças).
- Você vai redigir uma **story BMAD** de portabilidade (passa pelo conselho MiniMax+Kimi antes do merge).

## Do not use this skill when

- Você ainda não dissecou o sistema-alvo (use `system-dissector` primeiro).
- O alvo é firmware / IoT / mobile-only (use `firmware-analyst` ou `mobile-re` + portar manualmente).
- Você quer portar **para outro stack que não NeoAI/NeoAISystems** (essa skill é específica para o ecossistema do Anderson).
- Você quer fazer **análise de malware** ou extração de chaves (use `malware-analyst`).
- Você quer apenas **inspiração** de pattern sem port concreto — use `binary-analysis-patterns` ou `protocol-reverse-engineering` direto.

## NeoAI/NeoAISystems architecture summary (2026-09-22)

### Stack canônico

| Layer | Technology | Source of truth |
|---|---|---|
| Frontend | Nuxt 4 + Vue 3.5 + TS 6 + Tailwind v4 + Pinia 3 + `@nuxt/ui` v4 | `/Users/andersongoliveira/Nuxt-Agendador/` |
| Backend primário | Nuxt 4 Nitro server (TS) + Zod | `apps/web/server/` |
| Backend secundário (multi-tenant ERP) | Odoo 19 CE (PostgreSQL 17) | `/Users/andersongoliveira/Odoov19-José/` |
| Backend terciário (WhatsApp gateway) | Go 1.26 + Gin + GORM (NeoGo) | `/Users/andersongoliveira/NeoGo/` |
| Voice engine | Go (Pion WebRTC + codec MLOW) + NeoDoo telephony | `/Users/andersongoliveira/NeoGo/pkg/voipengine/` |
| Mobile / Bot | Telegram (NeoAssessor bot) + WhatsApp (via NeoGo) | `/Users/andersongoliveira/NeoAssessor/` |
| Database | PostgreSQL 17 (RLS multi-tenant via `rls.current_org_id()`) + Redis 8 | migrations em `db/migrations/NNN_*.sql` |
| Cache / Queue | Redis 8 (cache + pub/sub) + RabbitMQ 4.1 (NeoGo) | — |
| Storage | MinIO (S3-compat) | stack Swarm `utility` |
| AI cascade | Vercel AI SDK v7 + MiniMax (M3) → Groq → Gemini | `apps/web/server/utils/ai/sdk-facade.ts` |
| Observability | Langfuse + PostHog + Prometheus | — |
| Deploy | Docker Swarm single-node (Ubuntu 24.04, 12 vCPU, 23Gi RAM) | `infra/deploy.sh` + VPS IONOS `74.208.36.71` |

### Adjacent products (portar é permitido, cada um é independente)

- **UniversalOne** (`/Users/andersongoliveira/UniversalOne/`) — Nuxt 4 frontend sobre CGU (Odoo V19c) + iurd_api FastAPI. Multi-tenant via Keycloak OIDC.
- **EkklesiaOne-SaaS** (`/Users/andersongoliveira/EkklesiaOne-SaaS/`) — plataforma SaaS multitenant para gestão eclesiástica.
- **MIA** (`/Users/andersongoliveira/MIA/`) — plataforma multicanal IA + interface LLM unificada para o ecossistema IURD MX.
- **Neodoo-mkt** (`/Users/andersongoliveira/projects/neodoo_mkt/`) — módulo Odoo 19 de automação de marketing omnichannel.
- **Odoo WhatsApp Module** (`/Users/andersongoliveira/projects/Odoo_WhatsApp_Modulo/`) — conector WhatsApp via NeoGo.

### Conventions mandatórias

Ver `~/Nuxt-Agendador/docs/neoai-dev-conventions.md` para a base viva. Highlights:

- **Multi-tenancy**: TODA query de dados usa `requireAuth(event)` + filtra por `user.organizationId`. RLS via `withOrgContext(sql, orgId, cb)`. Nunca expor dados cross-tenant.
- **LGPD**: nunca hard DELETE — anonimizar.
- **SQL**: só tagged templates do postgres.js. Nunca interpolação.
- **Zod** em todo body POST/PATCH.
- **Provider ofuscação**: MiniMax/Groq/Gemini NUNCA expostos na UI/SEO/marketing. Usar `maskProviderInString` antes de retornar strings user-facing.
- **i18n**: 3 locales (pt-BR/es/en) — atualizar os 3 juntos.
- **Deploy**: `git push origin` → `pnpm deploy:prod` → SSH/rsync → build no servidor. Sem CI, sem registry.
- **BMAD**: toda feature passa por story aprovada + cross-review MiniMax+Kimi via `scripts/cross-review/bmad-cross-review.sh`.

### Frameworks canônicos de apoio

- **Neodoo19Framework** (`/Users/andersongoliveira/projects/neodoo19_framework/`) — framework de validação + padrões para módulos Odoo 19. Validator: `python3 framework/validator/validate.py`.
- **NeoAI dev conventions** — atualizada a cada iteração (seção 8 = changelog de aprendizados).

## Input contract (o que recebe do `system-dissector`)

Esta skill consome o output do `system-dissector` em paths relativos a `dissects/<sistema>/`. Os paths abaixo são os **canônicos** — o que o `system-dissector` realmente produz. Se algum estiver ausente, registre como **gap** no output e peça para re-rodar `system-dissector` antes de prosseguir.

```
dissects/<sistema>/
├── triagem.md                # Phase 1 (sempre presente)
├── deep-dive/                # Phase 2
│   ├── architecture.md
│   ├── data-flows.md
│   ├── key-structures.md
│   └── <modulo>-analysis.md
├── wiki/                     # Phase 3
│   ├── index.md              # Sumário executivo (entry point)
│   ├── README.md
│   ├── architecture/
│   │   ├── c4-context.md
│   │   └── c4-container.md
│   ├── modules/<mod>.md
│   ├── api/
│   ├── security/
│   ├── glossary.md
│   └── decisions.md          # ADRs extraídos (MADR-style)
├── extract/                  # Phase 4 — INPUT principal desta skill
│   ├── components.md         # Lista priorizada com scoring C1-C6 /60
│   ├── patterns.md           # Patterns portáveis identificados
│   ├── algorithms.md
│   ├── dependencies.md       # Deps brutas do sistema-alvo
│   ├── api.md                # Mapeamento de APIs externas (machine-readable)
│   └── license-audit.md      # SPDX por dependência (veredito por componente)
├── risk-raw.md               # Notas brutas de risco (pré-scoring)
├── integrate/                # Phase 5 — OUTPUT desta skill
│   ├── integrate.md
│   ├── port-plan/<componente>-port.md
│   └── risk-score.md
└── state.json
```

### Schema esperado de `extract/components.md`

`extract/components.md` é a **fonte primária** do scoring desta skill. Ele já traz a rubrica canônica C1-C6 aplicada por componente (veja §"Reusability scoring"). Esta skill **lê** os scores de lá — não recalcula.

```yaml
# Cada bloco YAML descreve um componente extraível
- id: pos.order.sync
  name: "Sincronização de ordens PDV → Odoo backend"
  type: integration | ui | business-logic | data-model | infra
  source_stack: "Odoo 14 CE + custom"
  dependencies: ["queue", "websocket", "postgres"]
  scoring:
    c1_compatibility: 10     # Python → Odoo (native match)
    c2_code_quality: 7
    c3_license: 8            # Apache-2.0 (LGPL-compatible via dynamic linking)
    c4_maintenance: 9        # last commit < 30d
    c5_dependency_footprint: 8   # ≤ 2 deps novas
    c6_reversibility: 10     # wrap + adapter
    total: 52                # /60 → Tier 1
    tier: T1
  port_strategy_hint: source-port
  evidence: verified | estimated
  notes: "Pattern de outbox + retry exponencial; não copiar código"
```

### Schema esperado de `extract/patterns.md`

```yaml
- id: webhook-dispatcher-retry
  name: "Webhook dispatcher com retry exponencial + DLQ"
  domain: integration
  description: "..."
  reusability_hint: 9
  applicable_to: ["NeoGo", "UniversalOne", "MIA"]
  notes: "Pattern recorrente em Stripe, GitHub, Shopify SDKs"
```

### Schema esperado de `extract/api.md`

```yaml
- endpoint: POST /v1/charges
  method: POST
  auth: Bearer
  rate_limit: "100 req/s"
  equivalent_in_neoai: null     # ou "apps/web/server/api/billing/charges.post.ts"
  port_strategy: reference      # source-port | wrap | extract-pattern | reference | drop-in
  license: MIT
  evidence: repo/path/file.py:42
```

### Schema esperado de `license-audit.md` (veredito por componente)

O §6 de `license-audit.md` é a fonte do C3 da rubrica. Esta skill lê dali.

```yaml
component_licenses:
  - component: pos.order.sync
    license: Apache-2.0
    verdict: safe                 # safe | conditional | blocking
    notes: dynamic linking OK
```

### Schema esperado de `wiki/decisions.md` (ADRs)

Os ADRs observados no sistema-alvo entram em `port-plan/<componente>-port.md` §"Invariantes de negócio". Esta skill **lê** ADRs de lá e os propaga como restrições.

Se algum input estiver ausente, registre isso como **gap** em `integrate/integrate.md` §"Input gaps" e peça para re-rodar `system-dissector` antes de prosseguir.

## Reusability scoring (rubrica canônica C1-C6 /60)

Esta skill **não recalcula** scores — ela consome `extract/components.md` e adiciona contexto de port (target stack, effort, blockers). Os scores vêm da rubrica canônica do `system-dissector`:

| Critério | Peso máx | Como pontuar (resumo — detalhes em `extract-components.md.template` §1.1) |
|---|---|---|
| **C1 — Compatibility** (lang/framework/runtime) | 0-10 | Native match (Python ↔ Odoo, TS/JS ↔ Nuxt, Go ↔ NeoGo) +10; rewrite −10 |
| **C2 — Code quality** (tests, docs, idioms) | 0-10 | >80% coverage + ADRs + docstrings +10; untested 0 |
| **C3 — License compatibility** | 0-10 | MIT/Apache/BSD +10; LGPL dynamic linking +5; GPL/AGPL/proprietary 0 (block) |
| **C4 — Maintenance velocity** | 0-10 | Last commit < 30d + responsive maintainers +10; stale (>18mo) 0 |
| **C5 — Dependency footprint** | 0-10 | ≤ 2 new deps +10; > 5 deps or native C lib −10 |
| **C6 — Reversibility** | 0-10 | Wrap/adapter +10; lock-in core 0 |

**Total**: 0-60.

### Tabela de decisão por score (Tier mapping)

| Score total | Tier | Ação |
|---|---|---|
| **≥ 50** | **Tier 1** | **Port imediato.** Criar story BMAD P1; cross-review MiniMax+Kimi obrigatório. |
| **40-49** | **Tier 2** | **Avaliar caso a caso.** Story BMAD M1; analisar no próximo sprint. |
| **< 40** | **Tier 3** | **Não portar.** Marcar como "estudado, não aplicável" — reference design apenas. |

### Cálculo (pseudo-script)

```python
def port_tier(extract_components_row: dict) -> tuple[int, str]:
    """Lê scores já atribuídos pelo dissector; decide tier."""
    s = extract_components_row["scoring"]
    total = (
        s["c1_compatibility"]
        + s["c2_code_quality"]
        + s["c3_license"]
        + s["c4_maintenance"]
        + s["c5_dependency_footprint"]
        + s["c6_reversibility"]
    )
    if total >= 50:
        return total, "T1"
    if total >= 40:
        return total, "T2"
    return total, "T3"


def port_strategy(extract_components_row: dict, license_verdict: dict) -> str:
    """Mapeia score + license → estratégia de port."""
    s = extract_components_row["scoring"]
    if license_verdict == "blocking":
        return "reference-only"
    if s["c6_reversibility"] >= 8 and license_verdict == "safe":
        return "wrap"
    if s["c1_compatibility"] >= 9 and license_verdict == "safe":
        return "source-port"
    if s["c2_code_quality"] >= 7 and license_verdict in ("safe", "conditional"):
        return "extract-pattern"
    if s["c1_compatibility"] >= 10 and s["c3_license"] >= 10 and license_verdict == "safe":
        return "drop-in"
    return "reference-only"
```

## Porting patterns (5 tipos)

### 1. Source-port

Reescrever o componente no stack NeoAI, mantendo **semântica idêntica** mas com código novo.

**Quando usar:**
- Score ≥ 7
- Componente crítico para o produto
- Licença compatível (MIT/Apache/BSD) **E** código limpo (LGPL/GPL = NÃO, é melhor reference)

**Exemplos reais:**
- "Portar módulo `point_of_sale` do Odoo CE para NeoAI" — recriar em `addons/neoai_pos/`, mantendo a API REST de checkout.
- "Portar pattern de webhook dispatcher do Stripe SDK para NeoGo gateway" — reescrever em Go idiomático.

**Workflow:**
1. Mapear contratos (input/output) — usar `extract/api.md`.
2. Identificar invariantes de negócio — usar `wiki/decisions.md`.
3. Escrever testes **antes** do código (TDD).
4. Implementar no stack alvo (Odoo 19 / Nuxt 4 / NeoGo).
5. Validar contra os invariantes extraídos.
6. Cross-review MiniMax+Kimi.

### 2. Wrap

Manter o binário/código original rodando, criando um **adapter/proxy** que fala a língua NeoAI.

**Quando usar:**
- Componente é grande demais para reescrever
- Time-to-market é crítico
- Componente roda em outro runtime (ex: Python Flask + NeoAI é Nuxt/TS)

**Exemplos reais:**
- Wrapper Python para um serviço de cálculo de impostos que não pode ser reescrito.
- Adapter REST que converte API legada em Odoo JSON-RPC → Nuxt fetch wrapper.

**Workflow:**
1. Criar serviço separado (`infra/docker-compose.swarm.yml`) — manter isolado.
2. Escrever adapter (Go ou TS) que consome a API original + expõe no contrato NeoAI.
3. Tracing distribuído entre adapter e NeoAI (Langfuse).
4. Plano de deprecação documentado (quando source-port for viável).

### 3. Extract pattern

Isolar o **padrão/algoritmo** e reimplementar, sem copiar código.

**Quando usar:**
- Score 5-8 com licença GPL/LGPL/proprietary
- Pattern é recorrente no ecossistema (ex: outbox, retry exponencial, idempotency keys)
- Não é viável reescrever o componente inteiro

**Exemplos reais:**
- Pattern "outbox transactional" do Stripe → implementar em `apps/web/server/utils/outbox.ts`.
- Pattern "idempotency key" do Shopify → implementar em NeoGo `pkg/idempotency/`.

**Workflow:**
1. Documentar o pattern em linguagem natural (NÃO código).
2. Criar testes que validem o pattern isoladamente.
3. Reimplementar no stack alvo com idioms nativos.
4. Marcar origem clara no header do arquivo:
   ```typescript
   // apps/web/server/utils/outbox.ts
   // Pattern extracted from Stripe webhook dispatcher (2026-09-22).
   // Reimplemented for NeoAI; no code copied.
   ```

### 4. Reference design

Usar como inspiração sem portar código. Documentar para futuras decisões.

**Quando usar:**
- Score 3-5
- Componente é arquitetural (não dá para extrair pattern simples)
- Licença bloqueia (proprietary)

**Exemplos reais:**
- "Arquitetura de agente IA do DeskcommCRM" — estudar para informar design do MIA.
- "Pipeline de mídia do WhatsApp WaCalls" — entender, mas não portar (codec proprietário).

**Workflow:**
1. Escrever ADR NeoAI descrevendo o que foi estudado.
2. Marcar lições aprendidas no `extract/components.md` como `reference-only`.
3. Adicionar ao `~/.agent/projects/neoai-architecture-patterns.md` se for cross-system.

### 5. Drop-in

Copiar com mudanças mínimas. **Raro** — requer licença perfeita + stack match exato.

**Quando usar:**
- Score 9-10 E licença MIT/Apache E código limpo E zero deps novas
- Componente é pequeno (< 500 linhas)

**Exemplos reais:**
- Utility TS isolado (slugify, hash determinístico) de uma lib MIT → copiar direto com attribution.

**Workflow:**
1. Verificar SPDX header e licença arquivo por arquivo.
2. Adicionar `// Original: <repo> <commit>; License: MIT; Modifications: <lista>`.
3. Manter em diretório `_vendored/` separado.
4. Atualizar `THIRD_PARTY_LICENSES.txt` (LGPD + compliance).

## Odoo 19 module port template

Quando o componente extraído casa com um **modelo de dados Odoo** (account.move, res.partner, sale.order, etc.) ou é uma **feature Odoo-like** (workflow, relatório, kanban), a portabilidade canônica é um **módulo Odoo 19**.

### Estrutura do módulo

```
neoai_<component>/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── <component_model>.py
├── views/
│   ├── <component>_views.xml
│   └── <component>_menu.xml
├── security/
│   ├── ir.model.access.csv
│   └── <component>_security.xml
├── data/
│   └── <component>_data.xml
├── static/
│   └── description/
│       └── icon.png
└── tests/
    └── test_<component>.py
```

### `__manifest__.py` válido (Odoo 19)

```python
{
    'name': 'NeoAI <Component>',
    'version': '19.0.1.0.0',
    'category': 'Operations',
    'summary': 'Port from <source-system> for NeoAI',
    'description': """
Ported component from <source-system> (<version>).
Original license: <license> | Original authors: <authors>
NeoAI modifications: <list>.
    """,
    'author': 'NeoAnd',
    'website': 'https://neoai.systems',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',          # security PRIMEIRO
        'security/<component>_security.xml',
        'views/<component>_views.xml',
        'views/<component>_menu.xml',
        'data/<component>_data.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',  # ou 'OPL-1' ou 'MIT' dependendo do componente
}
```

### `models/<component>_model.py` válido (Odoo 19)

```python
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class NeoaiComponent(models.Model):
    _name = 'neoai.component'
    _description = 'NeoAI Component (ported from <source>)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(string='Name', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    organization_id = fields.Many2one(
        'res.partner',
        string='Organization',
        required=True,
        index=True,
        ondelete='restrict',
        check_company=True,   # OBRIGATÓRIO em multi-company
    )
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived')],
        string='State',
        default='draft',
        tracking=True,
    )
    computed_total = fields.Float(
        string='Computed Total',
        compute='_compute_total',
        store=True,
    )

    # Odoo 19: models.Constraint, NAO _sql_constraints
    _name_unique = models.Constraint(
        'unique(name, organization_id)',
        'Name must be unique per organization!',
    )

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for record in self:
            record.computed_total = sum(record.line_ids.mapped('amount'))

    @api.constrains('name')
    def _check_name(self):
        for record in self:
            if not record.name or len(record.name) < 3:
                raise ValidationError(_("Name must be at least 3 characters"))

    def action_activate(self):
        self.ensure_one()
        self.write({'state': 'active'})
        return True

    # Odoo 19: use _compute_display_name, NAO name_get()
    @api.depends('name', 'organization_id.name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.organization_id.name}] {record.name}"
```

### `views/<component>_views.xml` válido (Odoo 19)

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- List view: SEMPRE <list>, NUNCA <tree> -->
    <record id="neoai_component_view_list" model="ir.ui.view">
        <field name="name">neoai.component.view.list</field>
        <field name="model">neoai.component</field>
        <field name="arch" type="xml">
            <list string="Components">
                <field name="name"/>
                <field name="organization_id"/>
                <field name="state"/>
                <field name="computed_total"/>
            </list>
        </field>
    </record>

    <!-- Form view -->
    <record id="neoai_component_view_form" model="ir.ui.view">
        <field name="name">neoai.component.view.form</field>
        <field name="model">neoai.component</field>
        <field name="arch" type="xml">
            <form string="Component">
                <header>
                    <button name="action_activate" type="object"
                            string="Activate" class="btn-primary"
                            invisible="state != 'draft'"/>
                    <field name="state" widget="statusbar"/>
                </header>
                <sheet>
                    <group>
                        <field name="name"/>
                        <field name="organization_id"/>
                        <field name="active"/>
                    </group>
                </sheet>
                <chatter/>
            </form>
        </field>
    </record>

    <!-- Search view: <group> SEM expand="0" e SEM string="" -->
    <record id="neoai_component_view_search" model="ir.ui.view">
        <field name="name">neoai.component.view.search</field>
        <field name="model">neoai.component</field>
        <field name="arch" type="xml">
            <search string="Components">
                <field name="name"/>
                <field name="organization_id"/>
                <field name="state"/>
                <group>
                    <filter name="state_draft" string="Draft"
                            domain="[('state', '=', 'draft')]"/>
                    <filter name="state_active" string="Active"
                            domain="[('state', '=', 'active')]"/>
                </group>
            </search>
        </field>
    </record>

    <!-- Action: view_mode=list,form (NUNCA tree,form) -->
    <record id="neoai_component_action" model="ir.actions.act_window">
        <field name="name">Components</field>
        <field name="res_model">neoai.component</field>
        <field name="view_mode">list,form</field>
        <field name="search_view_id" ref="neoai_component_view_search"/>
    </record>

    <!-- Menu -->
    <menuitem id="neoai_component_menu"
              name="Components"
              action="neoai_component_action"
              sequence="50"/>

</odoo>
```

### `security/ir.model.access.csv` válido

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_neoai_component_user,neoai.component.user,model_neoai_component,base.group_user,1,0,0,0
access_neoai_component_manager,neoai.component.manager,model_neoai_component,base.group_system,1,1,1,1
```

### `security/<component>_security.xml` válido (Odoo 19)

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <!-- Odoo 19: privilege_id, NAO category_id -->
    <record id="module_category_neoai" model="ir.module.category">
        <field name="name">NeoAI</field>
        <field name="sequence">100</field>
    </record>

    <record id="neoai_privilege" model="res.groups.privilege">
        <field name="name">NeoAI Component</field>
        <field name="category_id" ref="module_category_neoai"/>
    </record>

    <record id="neoai_component_group" model="res.groups">
        <field name="name">NeoAI Component / User</field>
        <field name="privilege_id" ref="neoai_privilege"/>
    </record>

    <!-- Record rule: multi-company -->
    <record id="neoai_component_rule" model="ir.rule">
        <field name="name">NeoAI Component multi-company</field>
        <field name="model_id" ref="model_neoai_component"/>
        <field name="domain_force">[('organization_id.company_id', 'in', company_ids)]</field>
        <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    </record>

</odoo>
```

### Validação do módulo

```bash
# Rodar validator do Neodoo19Framework
python3 ~/projects/neodoo19_framework/framework/validator/validate.py \
    --module-path neoai_component/

# Em container Odoo 19 oficial
docker exec -it <odoo19-container> \
    odoo module uninstall -d probe_db -c /etc/odoo/odoo.conf neoai_component
docker exec -it <odoo19-container> \
    odoo -d probe_db -i neoai_component --test-enable \
    --test-tags '/neoai_component' \
    --stop-after-init --without-demo=True \
    --http-port=8991 --gevent-port=8992
```

### ⚠️ O que NÃO fazer em Odoo 19 (gotchas verificadas)

- **NUNCA** usar `<tree>` → sempre `<list>`.
- **NUNCA** usar `attrs=` ou `states=` → usar `invisible=`, `readonly=`, `required=` direto.
- **NUNCA** usar `_sql_constraints` (é ignorado silenciosamente) → usar `models.Constraint`.
- **NUNCA** usar `res.partner.mobile` (não existe) → usar `res.partner.phone`.
- **NUNCA** usar `def name_get(self)` → usar `@api.depends(...) _compute_display_name`.
- **NUNCA** usar `from odoo.osv import expression` → `from odoo.fields import Domain`.
- **NUNCA** usar `res.groups.category_id` → usar `res.groups.privilege` + `ir.module.category`.
- **NUNCA** omitir `check_company=True` em M2O multi-company.
- **NUNCA** usar `self._cr` → `self.env.cr`.
- **SEMPRE** colocar `<group>` SEM `expand="0"` e SEM `string=""` dentro de `<search>`.
- **SEMPRE** `self.ensure_one()` em métodos de ação.
- **SEMPRE** listar security (CSV + XML) **antes** de views em `__manifest__.py` data.

## Nuxt 4 + Vue 3 component port template

Quando o componente extraído é **UI/frontend** ou **composable/utility**, a portabilidade canônica é um componente Nuxt 4 + Vue 3.5.

### Estrutura Nuxt 4 (apps/web)

```
apps/web/
├── pages/
│   └── <feature>/index.vue          # rota /<feature>
├── components/
│   └── <Feature>/
│       ├── <Feature>Card.vue        # bloco
│       ├── <Feature>List.vue
│       └── <Feature>Detail.vue
├── composables/
│   └── use<Feature>.ts              # lógica reutilizável
├── stores/                          # Pinia
│   └── <feature>.ts
├── server/
│   └── api/<feature>/
│       ├── index.get.ts             # GET /api/<feature>
│       ├── index.post.ts            # POST /api/<feature>
│       └── [id].get.ts              # GET /api/<feature>/:id
├── types/
│   └── <feature>.ts                 # TS types
└── tests/
    └── unit/<feature>.test.ts       # Vitest
```

### Componente Vue 3.5 + Nuxt UI v4 (copy-paste)

```vue
<!-- apps/web/components/Feature/FeatureCard.vue -->
<script setup lang="ts">
import type { Feature } from '~/types/feature'

const props = defineProps<{
  feature: Feature
}>()

const emit = defineEmits<{
  select: [id: string]
  archive: [id: string]
}>()

const formattedDate = computed(() =>
  new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' })
    .format(new Date(props.feature.createdAt))
)
</script>

<template>
  <UCard class="feature-card">
    <template #header>
      <h3 class="text-highlighted">{{ feature.name }}</h3>
    </template>

    <p class="text-toned">{{ feature.description }}</p>

    <div class="mt-2 text-sm text-muted">
      Criado em {{ formattedDate }}
    </div>

    <template #footer>
      <div class="flex gap-2">
        <UButton
          variant="ghost"
          color="primary"
          :label="$t('feature.actions.select')"
          @click="emit('select', feature.id)"
        />
        <UButton
          variant="ghost"
          color="error"
          :label="$t('feature.actions.archive')"
          @click="emit('archive', feature.id)"
        />
      </div>
    </template>
  </UCard>
</template>
```

### Server route (Nitro)

```typescript
// apps/web/server/api/feature/index.get.ts
import { z } from 'zod'
import { sql } from '~/server/utils/db'
import { requireAuth } from '~/server/utils/auth'
import { withOrgContext } from '~/server/utils/rls'

const querySchema = z.object({
  limit: z.coerce.number().int().min(1).max(100).default(20),
  offset: z.coerce.number().int().min(0).default(0),
})

export default defineEventHandler(async (event) => {
  const user = requireAuth(event)
  const query = querySchema.parse(getQuery(event))

  const features = await withOrgContext(sql, user.organizationId, async (tx) => {
    return tx`
      SELECT id, name, description, state, created_at
      FROM features
      WHERE organization_id = ${user.organizationId}
        AND active = true
      ORDER BY created_at DESC
      LIMIT ${query.limit} OFFSET ${query.offset}
    `
  })

  return { features }
})
```

### Composable (Pinia store + composable)

```typescript
// apps/web/composables/useFeature.ts
import type { Feature } from '~/types/feature'

export function useFeature() {
  const { data, refresh, pending, error } = useFetch<{ features: Feature[] }>(
    '/api/feature',
    {
      default: () => ({ features: [] }),
      watch: false,
    }
  )

  async function archive(id: string) {
    await $fetch(`/api/feature/${id}/archive`, { method: 'POST' })
    await refresh()
  }

  return {
    features: computed(() => data.value?.features ?? []),
    pending,
    error,
    refresh,
    archive,
  }
}
```

### TypeScript types

```typescript
// apps/web/types/feature.ts
export interface Feature {
  id: string
  name: string
  description: string
  state: 'draft' | 'active' | 'archived'
  createdAt: string  // ISO 8601
  organizationId: string
}
```

### i18n (3 locales — atualizar juntos)

```typescript
// apps/web/i18n/locales/pt-BR.ts
export default {
  feature: {
    title: 'Funcionalidade',
    actions: {
      select: 'Selecionar',
      archive: 'Arquivar',
    },
  },
}

// apps/web/i18n/locales/es.ts
export default {
  feature: {
    title: 'Funcionalidad',
    actions: {
      select: 'Seleccionar',
      archive: 'Archivar',
    },
  },
}

// apps/web/i18n/locales/en.ts
export default {
  feature: {
    title: 'Feature',
    actions: {
      select: 'Select',
      archive: 'Archive',
    },
  },
}
```

### ⚠️ Gotchas Nuxt 4 + Vue 3 + Nuxt UI v4

- **v4 API**: `UTable :data` (não `:rows`), `USwitch` (não UToggle), `UDropdownMenu` flat `:items` (não UDropdown), `UToaster` (não UNotifications).
- **Modais**: sempre `NeoBottomSheet` (UModal desktop + UDrawer mobile).
- **Tokens**: `text-highlighted/default/toned/muted/dimmed`, `bg-default/elevated/accented`. Dark mode: `bg-{color}/10` (nunca `bg-red-50 dark:bg-red-950`).
- **i18n**: escapar `@` com `{'@'}`; nunca hardcode PT-BR — usar `$t()` ou `useTenantConfig().labels`. Atualizar os 3 locales juntos.
- **Provider ofuscação**: nunca expor MiniMax/Groq/Gemini em UI strings — usar `maskProviderInString`.
- **Multi-tenancy**: server routes sempre `requireAuth(event)` + `withOrgContext(sql, user.organizationId, ...)`.

## NeoGo service port template

Quando o componente extraído é **infraestrutura Go** (gateway, proxy, dispatcher, codec), a portabilidade canônica é um serviço NeoGo (Go 1.26 + Gin + GORM).

### Estrutura cmd/internal

```
pkg/<domain>/
├── cmd/
│   └── neogo/main.go           # bootstrap
├── internal/
│   ├── <domain>/
│   │   ├── handler/            # Gin handlers
│   │   ├── service/            # business logic
│   │   ├── repository/         # GORM ou raw SQL
│   │   └── model/              # DTOs + domain models
│   ├── config/                 # env-driven config
│   ├── observability/          # logs estruturados, metrics
│   └── middleware/             # auth, rate limit, tracing
├── migrations/                 # golang-migrate embed FS
│   └── 00000N_<name>.{up,down}.sql
└── go.mod
```

### Service skeleton (Go 1.26 + Gin)

```go
// pkg/<domain>/internal/<domain>/service/service.go
package service

import (
    "context"
    "fmt"
    "log/slog"
    "time"

    "github.com/neoand/<domain>/internal/<domain>/repository"
    "github.com/neoand/<domain>/internal/<domain>/model"
)

type Service struct {
    repo   *repository.Repository
    logger *slog.Logger
}

func NewService(repo *repository.Repository, logger *slog.Logger) *Service {
    return &Service{repo: repo, logger: logger}
}

// Process executa a lógica portada do sistema-alvo.
// Original: <source-system> <version>, <license>.
func (s *Service) Process(ctx context.Context, req model.Request) (*model.Result, error) {
    // 1. Idempotency check (pattern: Stripe webhook)
    if existing, err := s.repo.GetByIdempotencyKey(ctx, req.IdempotencyKey); err == nil && existing != nil {
        s.logger.Info("idempotent hit", "key", req.IdempotencyKey)
        return existing.Result, nil
    }

    // 2. Transactional outbox
    tx, err := s.repo.Begin(ctx)
    if err != nil {
        return nil, fmt.Errorf("begin tx: %w", err)
    }
    defer tx.Rollback()

    result, err := s.processInTx(ctx, tx, req)
    if err != nil {
        return nil, err
    }

    if err := tx.OutboxEnqueue("domain.event", result); err != nil {
        return nil, fmt.Errorf("outbox enqueue: %w", err)
    }

    if err := tx.Commit(); err != nil {
        return nil, fmt.Errorf("commit: %w", err)
    }

    return result, nil
}

// processInTx encapsula a lógica de negócio portada.
func (s *Service) processInTx(ctx context.Context, tx *repository.Tx, req model.Request) (*model.Result, error) {
    // ... lógica específica do componente portado ...
    return &model.Result{ /* ... */ }, nil
}
```

### Handler (Gin)

```go
// pkg/<domain>/internal/<domain>/handler/handler.go
package handler

import (
    "net/http"

    "github.com/gin-gonic/gin"
    "github.com/neoand/<domain>/internal/<domain>/service"
    "github.com/neoand/<domain>/internal/<domain>/model"
)

type Handler struct {
    svc *service.Service
}

func NewHandler(svc *service.Service) *Handler {
    return &Handler{svc: svc}
}

func (h *Handler) Register(rg *gin.RouterGroup) {
    rg.POST("/process", h.process)
}

// POST /api/v1/<domain>/process
func (h *Handler) process(c *gin.Context) {
    var req model.Request
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }

    ctx := c.Request.Context()
    result, err := h.svc.Process(ctx, req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }

    c.JSON(http.StatusOK, result)
}
```

### Config via env (12-factor)

```go
// pkg/<domain>/internal/config/config.go
package config

import (
    "fmt"
    "os"
    "strconv"
    "time"
)

type Config struct {
    HTTPPort       int
    DBURL          string
    RedisURL       string
    RabbitMQURL    string
    LogLevel       string
    ShutdownGrace  time.Duration
    MaxConcurrency int
}

func Load() (*Config, error) {
    cfg := &Config{
        HTTPPort:       getEnvInt("HTTP_PORT", 8080),
        DBURL:          getEnv("DATABASE_URL", ""),
        RedisURL:       getEnv("REDIS_URL", ""),
        RabbitMQURL:    getEnv("RABBITMQ_URL", ""),
        LogLevel:       getEnv("LOG_LEVEL", "info"),
        ShutdownGrace:  getEnvDuration("SHUTDOWN_GRACE", 30*time.Second),
        MaxConcurrency: getEnvInt("MAX_CONCURRENCY", 100),
    }
    if cfg.DBURL == "" {
        return nil, fmt.Errorf("DATABASE_URL is required")
    }
    return cfg, nil
}

func getEnv(key, fallback string) string {
    if v, ok := os.LookupEnv(key); ok {
        return v
    }
    return fallback
}

func getEnvInt(key string, fallback int) int {
    if v, ok := os.LookupEnv(key); ok {
        if n, err := strconv.Atoi(v); err == nil {
            return n
        }
    }
    return fallback
}

func getEnvDuration(key string, fallback time.Duration) time.Duration {
    if v, ok := os.LookupEnv(key); ok {
        if d, err := time.ParseDuration(v); err == nil {
            return d
        }
    }
    return fallback
}
```

### Observability (logs estruturados + healthcheck)

```go
// pkg/<domain>/internal/observability/logger.go
package observability

import (
    "log/slog"
    "os"
)

func NewLogger(level string) *slog.Logger {
    var lvl slog.Level
    switch level {
    case "debug":
        lvl = slog.LevelDebug
    case "warn":
        lvl = slog.LevelWarn
    case "error":
        lvl = slog.LevelError
    default:
        lvl = slog.LevelInfo
    }
    h := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: lvl})
    return slog.New(h)
}

// pkg/<domain>/internal/observability/health.go
package observability

import (
    "context"
    "github.com/gin-gonic/gin"
)

type Pinger interface {
    Ping(ctx context.Context) error
}

func HealthHandler(db, redis Pinger) gin.HandlerFunc {
    return func(c *gin.Context) {
        ctx := c.Request.Context()
        if err := db.Ping(ctx); err != nil {
            c.JSON(503, gin.H{"status": "degraded", "db": err.Error()})
            return
        }
        if err := redis.Ping(ctx); err != nil {
            c.JSON(503, gin.H{"status": "degraded", "redis": err.Error()})
            return
        }
        c.JSON(200, gin.H{"status": "ok"})
    }
}
```

### Docker Swarm deploy (compose snippet)

```yaml
# infra/docker-compose.swarm.yml (snippet)
services:
  neogo_<domain>:
    image: neogo_<domain>:latest
    build:
      context: ./services/neogo_<domain>
    environment:
      HTTP_PORT: "8080"
      DATABASE_URL: "postgres://neogo:<secret>@neogo_db:5432/neogo_<domain>?sslmode=disable"
      REDIS_URL: "redis://:<secret>@neogo_redis:6379/0"
      RABBITMQ_URL: "amqp://neogo:<secret>@neogo_rabbitmq:5672/"
      LOG_LEVEL: "info"
      SHUTDOWN_GRACE: "30s"
      MAX_CONCURRENCY: "100"
    deploy:
      replicas: 1
      update_config:
        order: stop-first           # CRÍTICO para não estourar PG
        parallelism: 1
      restart_policy:
        condition: on-failure
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
    networks:
      - netpevo
```

### Migrations (golang-migrate embed FS)

```go
// pkg/<domain>/migrations/embed.go
package migrations

import "embed"

//go:embed *.sql
var FS embed.FS
```

```sql
-- migrations/000001_create_table.up.sql
CREATE TABLE IF NOT EXISTS domain_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    idempotency_key TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, idempotency_key)
);

CREATE INDEX idx_domain_records_org ON domain_records(organization_id);
```

### Validação

```bash
# Build + test
cd pkg/<domain>
go test ./...
go vet ./...

# Lint
golangci-lint run

# Build Docker
docker buildx build --platform linux/amd64 \
    -t neogo_<domain>:latest \
    --load .

# Deploy (sem CI, manual via SSH)
ssh neoaiops@74.208.36.71
cd /opt/neogo
docker stack deploy -c docker-compose.swarm.yml neogo --with-registry-auth

# Validar
curl -s http://localhost:8080/health
```

### ⚠️ Gotchas NeoGo

- **Swarm update**: sempre `--update-order=stop-first` (senão estoura "too many clients" no PG durante overlap).
- **PG dump/restore**: verificar `instances_pkey` e outras PKs (perdeu constraints em PG16→17).
- **Migrations dirty**: se uma falha, destrava com `UPDATE schema_migrations SET dirty=false WHERE version=N` (cuidado).
- **LID/PN dual-addressing** (WhatsApp): sempre `whatsmeow_service.CanonicalChatJID(ctx, lidStore, jid)` antes de gravar `chat_jid`.
- **Manager dark mode**: nunca usar `:global(.dark-mode)` em scoped CSS — Vite quebra. Adicionar overrides em `manager/src/theme/neogo-theme.css` (global).
- **Webhook URLs**: montar via `PUBLIC_BASE_URL` env.
- **Crypto**: `NEOGO_CRYPTO_KEY` é AES-GCM 32 bytes hex (criptografa Chatwoot api_token). Gerar com `openssl rand -hex 32`.

## Validation gates (BMAD-aligned)

Antes de qualquer port ser mergeado em NeoAI/NeoAISystems, ele passa por **6 gates** alinhados ao BMAD v6.10.0.

### Gate 1 — Code review contra standards

**Owner:** Amelia (BMAD Dev persona) + specialists (`neoai-backend-dev`, `neoai-postgres-dba`).

Para Odoo 19:
```bash
python3 ~/projects/neodoo19_framework/framework/validator/validate.py \
    --module-path <module-path> --json
```

Para Nuxt 4 / Vue 3:
```bash
cd ~/Nuxt-Agendador
pnpm typecheck
pnpm lint
pnpm test:unit
```

Para NeoGo / Go:
```bash
cd ~/NeoGo
go test ./...
go vet ./...
golangci-lint run
```

### Gate 2 — License audit

**Owner:** agente LLM com skill `cred-omega` ou auditoria manual.

Checklist:
- [ ] SPDX header em cada arquivo portado (ou não — mas se não, documentar).
- [ ] `THIRD_PARTY_LICENSES.txt` atualizado.
- [ ] Nenhuma GPL/AGPL em projeto comercial (NeoAI é SaaS proprietário).
- [ ] LGPL apenas com dynamic linking (verificar dependências Go).
- [ ] MIT/Apache/BSD permitidos com attribution.
- [ ] Proprietary bloqueia port (a menos que acordo formal).

⚠️ **Verify nuances LGPL**: LGPL permite linking dinâmico. Em Go, isso significa que o módulo LGPL pode ser usado como biblioteca **sem ser modificado e recompilado junto** com o binário principal. Se houver modificação no código LGPL, o resultado precisa ser LGPL (viral parcial).

### Gate 3 — Security review

**Owner:** skill `007` (Security audit).

Checklist:
- [ ] Nenhuma credencial hardcoded.
- [ ] Inputs validados (Zod em TS, `models.Constraint` em Odoo, validators em Go).
- [ ] SQL parametrizado (postgres.js tagged templates, GORM em Go, ORM Odoo).
- [ ] Multi-tenant isolation preservada (RLS, `withOrgContext`, `requireAuth`).
- [ ] LGPD: anonimização em vez de hard DELETE.
- [ ] Secrets via env / vault (não em código).
- [ ] Auditoria de `extract/dependencies.md` contra CVEs públicas.

### Gate 4 — Performance benchmark

**Owner:** Amelia + `neoai-devops` (para backend).

Para Odoo 19:
```bash
# Profiling de queries
docker exec -it <odoo19-container> \
    odoo -d probe_db --log-level=sql --stop-after-init --no-http
```

Para Nuxt 4:
```bash
pnpm build
# Lighthouse / k6 contra staging
```

Para NeoGo:
```bash
# k6 contra staging
k6 run --vus 100 --duration 30s scripts/load-test.js
```

### Gate 5 — Integration smoke test

**Owner:** Amelia + beta tester humano (Anderson sinalizou que esse é o GAP prioritário).

Checklist:
- [ ] Pelo menos 1 happy-path E2E (Playwright ou curl).
- [ ] Pelo menos 1 edge case adversarial (entrada inválida, network failure, timeout).
- [ ] Verificação contra staging (não contra checkout local).
- [ ] Plano de rollback documentado.
- [ ] LGPD: opt-out propagado em todos os canais.

### Gate 6 — Documentation update

**Owner:** Amelia + tech writer.

Checklist:
- [ ] ADR NeoAI criado se decisão arquitetural nova (`/Users/andersongoliveira/Nuxt-Agendador/docs/decisions/ADR-NNN-<name>.md`).
- [ ] `neoai-dev-conventions.md` atualizado (seção 8 — changelog de aprendizados) com gotcha novo.
- [ ] Story BMAD fechada em `_bmad-output/implementation-artifacts/`.
- [ ] Cross-review MiniMax+Kimi registrado em `_bmad-output/cross-reviews/`.

### Cross-review MiniMax+Kimi (obrigatório)

Toda story Tier M/L roda via:
```bash
~/Nuxt-Agendador/scripts/cross-review/bmad-cross-review.sh \
    --story <story-id> --mode adversarial
```

Saída fica em `_bmad-output/cross-reviews/<ts>-<label>/synthesis.md` com decisão `MERGE / PATCH / HALT`.

## Cross-system pattern extraction

Quando você disserca **múltiplos sistemas** (ex: DeskcommCRM + WaCalls + Stripe SDK + Shopify SDK), extrair patterns comuns.

### Workflow

1. **Coletar** `extract/patterns.md` de todos os sistemas disseccados.
2. **Agrupar** por domínio (webhook dispatcher, idempotency, outbox, retry, rate limit, etc.).
3. **Verificar recorrência**: pattern aparece em ≥ 3 sistemas = forte candidato.
4. **Avaliar aplicabilidade** NeoAI: cada pattern vai em uma tabela com colunas `applicable_to`, `effort_to_port`, `license_clean`.
5. **Persistir** em `~/.agent/projects/neoai-architecture-patterns.md` (criar se não existir).

### Template do arquivo

```markdown
# NeoAI — Architecture Patterns Catalog

> Patterns extraídos via dissecação de múltiplos sistemas. Cada pattern foi
> observado em ≥ 3 sistemas antes de ser promovido para o catálogo.

## Index por domínio

| Pattern | Sistemas onde apareceu | Effort | License | Status |
|---|---|---|---|---|
| Idempotency key (header) | Stripe, Shopify, GitHub, DeskcommCRM | P | MIT | Adopted |
| Transactional outbox | Stripe, GitHub, WaCalls | M | MIT | Draft |
| Webhook retry exponencial + DLQ | Stripe, Shopify, GitHub | P | MIT | Adopted |
| Soft delete (LGPD) | DeskcommCRM, UniversalOne | P | MIT | Adopted |
| ... | ... | ... | ... | ... |

## Pattern: Idempotency Key

**Descrição:** Cliente envia header `Idempotency-Key: <UUID>` em POST crítico.
Servidor deduplica por (org, key, endpoint). Retorna 200 com resultado cacheado
se a key já foi vista.

**Sistemas onde apareceu:**
- Stripe API (`Idempotency-Key` header)
- Shopify Admin API
- GitHub webhook redelivery
- DeskcommCRM `send_ledger` (ADR-0010)

**Implementação canônica NeoAI:**
- TS: `apps/web/server/utils/idempotency.ts`
- Go: `pkg/idempotency/`
- Odoo: `models.Constraint('unique(...)')` + helper

**License:** MIT (todos os sistemas)

**Status:** Adopted em NeoAI 1.4.

## Pattern: Transactional Outbox

**Descrição:** Escrita no DB + enqueue de evento na mesma transação. Worker
assíncrono drena a outbox e publica no broker.

**Sistemas onde apareceu:**
- Stripe (payments)
- GitHub (webhooks)
- WaCalls (NeoGo voipengine)

[... continua ...]
```

### Criar/atualizar

```bash
# Criar se não existir
if [ ! -f ~/.agent/projects/neoai-architecture-patterns.md ]; then
    touch ~/.agent/projects/neoai-architecture-patterns.md
    echo "# NeoAI — Architecture Patterns Catalog" >> ~/.agent/projects/neoai-architecture-patterns.md
    echo "" >> ~/.agent/projects/neoai-architecture-patterns.md
    echo "> Patterns extraídos via dissecação de múltiplos sistemas." >> ~/.agent/projects/neoai-architecture-patterns.md
fi

# Atualizar seção (automatizável via skill ou manual)
```

### Clean-room check no consolidador

Quando consolidar patterns de múltiplos dissects em `cross-system-patterns.md`, validar:

- Cada pattern tem clean-room score ≥ 8 (ver `Clean-room methodology` abaixo)
- Patterns de mesma categoria (ex: vector search) usam **nomenclaturas DIFERENTES** entre origens (para garantir reimplementação genuína, não contaminação por tradução)
- Não há "copy-paste with rename" entre patterns de origens diferentes — se dois patterns compartilham ≥ 3 nomes de funções/variáveis idênticos, descartar um deles e refazer com abstração própria
- Cada consolidação registra `[verified]` (vi no source em pelo menos uma origem) ou `[estimated]` (infiro de padrão cross-domain)

## Output templates

Esta skill gera 3 tipos de artefato, sob `dissects/<sistema>/integrate/` (canônico — bate com `system-dissector` Phase 5 spec):

### 1. `dissects/<sistema>/integrate/integrate.md` — plano de port agregado

```markdown
# Port Plan: <sistema> → NeoAI/NeoAISystems

**Data:** 2026-09-22
**Sistema-alvo:** <sistema> <versão>
**Skill origem:** system-dissector (YYYY-MM-DD)
**Reviewer:** Anderson Oliveira

## TL;DR

- Score médio de reusabilidade: X.X / 60 (rubrica canônica C1-C6)
- Componentes Tier 1 (≥ 50): N / M → port imediato
- Componentes Tier 2 (40-49): N → avaliar caso a caso
- Componentes Tier 3 (< 40): N → não portar
- Effort total estimado: ~X sprints (P=1 dia, M=1 sprint, G=2+ sprints)

## Input gaps (se houver)

> Esta skill **lê** os artefatos do `system-dissector` conforme o contrato
> canônico em §"Input contract". Marque aqui o que não veio e peça para
> re-rodar a fase correspondente antes de prosseguir.

- [ ] `extract/components.md` — OK / missing
- [ ] `extract/license-audit.md` — OK / missing (afeta C3 scoring)
- [ ] `extract/api.md` — OK / missing
- [ ] `wiki/decisions.md` — OK / missing (afeta port-plan invariants)

## Tabela consolidada

| Componente | Total /60 | Tier | Tipo | Effort | License | Decisão |
|---|---|---|---|---|---|---|
| pos.order.sync | 52 | T1 | source-port | M | Apache-2.0 | MERGE (story P1) |
| webhook.dispatcher | 55 | T1 | extract-pattern | P | MIT | MERGE (story P1) |
| agent.orchestrator | 28 | T3 | reference-only | G | Proprietary | HALT (study only) |
| ... | ... | ... | ... | ... | ... | ... |

## Stories BMAD sugeridas

| ID | Título | Tier | Componente | Sprint |
|---|---|---|---|---|
| STORY-001 | Port webhook dispatcher para NeoGo | M | webhook.dispatcher | Sprint 12 |
| STORY-002 | Port módulo pos.order.sync para Odoo 19 | M | pos.order.sync | Sprint 13 |
| ... | ... | ... | ... | ... |

## Validação gates

- [ ] Gate 1 (code review) — owner: Amelia
- [ ] Gate 2 (license audit) — owner: cred-omega
- [ ] Gate 3 (security review) — owner: 007
- [ ] Gate 4 (perf benchmark) — owner: neoai-devops
- [ ] Gate 5 (smoke test) — owner: Amelia + Anderson
- [ ] Gate 6 (docs update) — owner: Paige
- [ ] Cross-review MiniMax+Kimi — obrigatório
```

### 2. `dissects/<sistema>/integrate/port-plan/<componente>-port.md` — plano por componente

```markdown
# Port Plan: <sistema>/<componente> → NeoAI

**Data:** 2026-09-22
**Score reusabilidade:** X / 60 (rubrica canônica C1-C6)
**Tier:** T1 | T2 | T3
**Tipo de port:** source-port | wrap | extract-pattern | reference | drop-in
**Effort:** P | M | G

## Contexto

- Componente extraído em: `dissects/<sistema>/extract/components.md#<componente-id>`
- Pattern relacionado: `dissects/<sistema>/extract/patterns.md#<pattern-id>`
- Wiki: `dissects/<sistema>/wiki/modules/<componente>.md`
- Licença original: <license>
- Decisão: <MERGE | PATCH | HALT>

## Target stack

Escolher UM:

- [ ] **Odoo 19 module** (path: `addons/neoai_<component>/`)
- [ ] **Nuxt 4 + Vue 3** (path: `apps/web/{components,pages,composables,server}/<feature>/`)
- [ ] **NeoGo service** (path: `pkg/<domain>/`)

## Contratos (input/output)

[Copiar de `extract/api.md` ou `wiki/modules/<componente>.md`.]

## Invariantes de negócio

[Listar invariantes críticos extraídos de `wiki/decisions.md`.]

## Plano de implementação

1. Setup de estrutura (path + manifest).
2. Tests FIRST (TDD).
3. Implementação.
4. Validação contra invariantes.
5. Cross-review MiniMax+Kimi.

## Riscos identificados

- [ ] Lock-in de versão (mitigação: ...)
- [ ] Deps não auditadas (mitigação: license audit gate)
- [ ] Performance regression (mitigação: benchmark gate)

## Checklist pré-merge

- [ ] Gate 1: code review OK
- [ ] Gate 2: license audit OK
- [ ] Gate 3: security review OK
- [ ] Gate 4: perf benchmark OK
- [ ] Gate 5: smoke test OK
- [ ] Gate 6: docs atualizadas
- [ ] Cross-review MiniMax+Kimi: MERGE
```

### 3. `dissects/<sistema>/integrate/risk-score.md` — scoring final

```markdown
# Risk Score: <sistema>

**Data:** 2026-09-22
**Rubrica:** C1-C6 canônica (0-60) — fonte: `extract/components.md`

## Resumo

| Componente | C1 | C2 | C3 | C4 | C5 | C6 | **Total** | Tier | Decisão |
|---|---|---|---|---|---|---|---|---|---|
| pos.order.sync | 10 | 7 | 8 | 9 | 8 | 10 | **52** | T1 | MERGE |
| webhook.dispatcher | 10 | 8 | 10 | 10 | 10 | 7 | **55** | T1 | MERGE |
| agent.orchestrator | 8 | 6 | 0 | 7 | 5 | 2 | **28** | T3 | HALT |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

## Justificativas por componente

### pos.order.sync — 52/60 (T1)
- C1 (Compatibility): 10 — Python ↔ Odoo (native match)
- C2 (Code quality): 7 — 71% coverage + ADRs
- C3 (License): 8 — Apache-2.0 (LGPL-compatible via dynamic linking)
- C4 (Maintenance): 9 — last commit < 30d
- C5 (Dependency footprint): 8 — ≤ 2 deps novas
- C6 (Reversibility): 10 — wrap + adapter (trivially reversible)

[... demais ...]
```

## Clean-room methodology (modelo Compaq/IBM 1981-83)

> Anderson implementa dissecação de código no modelo clean-room: time LLM produz SPEC do que o código faz, time DEV humano (separado fisicamente) implementa do zero em NeoAI/NeoAISystems. Nunca cole código-fonte no extract.

### Princípio da parede (segregation of duties)

- **Time A (LLM sub-agente)**: lê código de terceiros, escreve `extract/patterns.md` com APENAS spec funcional. **NUNCA cola trechos literais ≥ 20 linhas contínuas do código fonte.** Marcador `[verified]` significa "vi no source" (path/line), `[estimated]` significa "infiro de padrão".

- **Time B (DEV humano NeoAI/NeoAISystems)**: lê APENAS o spec do Time A. **NUNCA tem acesso ao código-fonte original durante a implementação.** Isso garante que a reimplementação é genuína, não contaminada.

### Rubrica clean-room para `extract/patterns.md` (0-10)

Cada `extract/patterns.md` recebe score clean-room baseado em:

| Critério | Score 0 | Score 5 | Score 10 |
|---|---|---|---|
| **Trechos literais** | ≥10 linhas coladas verbatim | 3-9 linhas | 0-2 linhas (apenas citations curtas) |
| **Pseudo-código vs código real** | Só código-fonte real | Mix | Só pseudocódigo/descrição |
| **Atribuição** | Sem fonte | Fonte vaga | Fonte exata `[verified]` ou `[estimated]` |
| **Especificação vs implementação** | Cola implementação | Mix | Spec puro (entradas/saídas/comportamento) |
| **Independent reimplementability** | Não dá pra reimplementar | Ambíguo | Engenheiro júnior implementa em 2h |

**Score ≥ 8/10**: clean-room OK — Time B pode usar
**Score 5-7**: reescrever antes de passar para Time B
**Score < 5**: descartar, refazer com `[estimated]` rigoroso

### Template "spec funcional" para `extract/patterns.md`

Cada pattern deve seguir este template (NÃO copiar código-fonte):

```markdown
### Pattern N: <nome>

**Fonte**: `<file:line>` [verified] ou "padrão conhecido" [estimated]
**Domínio**: <ex: agent memory, vector search, knowledge graph>
**Complexidade**: <trivial|small|medium|large>
**Clean-room score**: X/10

#### Spec funcional (sem código)

**Inputs**: <lista de entradas com tipos>
**Outputs**: <lista de saídas com tipos>
**Comportamento**: <descrição em prosa ou pseudocódigo de alto nível>
**Edge cases**: <lista>
**Complexidade algorítmica**: <Big-O se aplicável>
**Dependências externas**: <libs/APIs necessárias>

#### Para reimplementar do zero (Time B)

1. <passo 1>
2. <passo 2>
3. <passo 3>

#### Notas de portabilidade

- **Stack target**: <NeoAI/Nuxt 4/NeoGo/Odoo 19 — qual encaixa>
- **Esforço estimado**: <hours/days>
- **Blockers**: <licença, deps externas, etc>

#### Citação controlada (max 5 linhas, se necessário)

\`\`\`python
# Apenas 2-5 linhas ilustrativas se essenciais
# SEMPRE cite: -- from <file:line> [verified]
\`\`\`
```

### Workflow operacional clean-room

1. **LLM (Time A)** gera `extract/patterns.md` usando o template acima
2. **LLM self-check**: score clean-room ≥ 8?
   - Se não: reescrever
3. **DEV humano (Time B)** lê apenas `extract/patterns.md` (NÃO o código original)
4. **DEV implementa** em NeoAI/NeoAISystems seguindo "Para reimplementar do zero"
5. **Atribuição**: no código portado, comentário `// Ported from <pattern_name> via clean-room — see dissects/<s>/extract/patterns.md`

### Anti-patterns (NÃO faça)

- Colar código fonte no extract (mesmo "só um pedacinho")
- Traduzir linha-a-linha Python → Python (mesma estrutura = contaminação)
- Usar nomes de variáveis/funções idênticos (mesmo `def retain(...)` é contaminado)
- Time B ler o código original antes de implementar
- Spec que diz "faz X igual ao código Y" sem descrever X funcionalmente

## Ethical considerations (licenses)

### Tabela de licenças comuns

| Licença | Uso em NeoAI (SaaS proprietário) | Notas |
|---|---|---|
| **MIT** | ✅ Permitido | Attribution obrigatória |
| **Apache-2.0** | ✅ Permitido | Patent grant + attribution |
| **BSD-2/3-Clause** | ✅ Permitido | Attribution obrigatória |
| **ISC** | ✅ Permitido | Equivalente a MIT |
| **LGPL-2.1/3.0** | ⚠️ Permitido com dynamic linking | ⚠️ Verify nuances: requer que o usuário possa re-linkar a versão modificada |
| **MPL-2.0** | ⚠️ Permitido por arquivo | Modificações no arquivo viram MPL |
| **GPL-2.0/3.0** | ❌ Bloqueado | Viralidade exige tornar NeoAI GPL (incompatível com SaaS proprietário) |
| **AGPL-3.0** | ❌ Bloqueado | Viralidade via rede (SaaS fica obrigado a abrir código) |
| **SSPL** | ❌ Bloqueado | Equivalente ao AGPL |
| **BSL / Source-available** | ⚠️ Verify caso a caso | Algumas restrições (ex: não-comercial) |
| **Proprietary** | ❌ Bloqueado sem acordo | Requer licença comercial |

### ⚠️ Verify nuances LGPL

- LGPL exige **dynamic linking** OU que o usuário possa re-linkar manualmente. Em Go, isso significa que o módulo LGPL pode ser importado como dependência **sem modificação**. Se modificarmos o código LGPL, precisamos disponibilizar o código modificado e garantir que o usuário pode re-linkar.
- Em Odoo, módulos LGPL são comuns (LGPL é a licença padrão do Odoo Community). Módulos OCA sob LGPL podem ser usados como dependência.
- **Risco real**: uma dependência LGPL transitiva pode contaminar o ecossistema se aGPL entrar na árvore. Rodar `pip-licenses` (Python) ou `go-licenses` (Go) para auditar.

### DMCA / Lei 9.610 (Brasil)

- Art. 104 da Lei 9.610/98 (direito autoral brasileiro): copiar obra intelectual sem autorização é crime (3 anos reclusão + multa).
- Para componentes extraídos via RE, é **fundamental** que:
  - O port seja feito por **extract-pattern** (reimplementação, não cópia).
  - O port seja feito por **reference design** (estudo, não incorporação).
  - **NUNCA** copiar código fonte literal de sistemas proprietários sem autorização.
  - Para sistemas open-source sob licença permissiva (MIT/Apache/BSD), source-port é OK **com attribution**.
  - Para sistemas sob GPL/AGPL/Proprietary, **NUNCA source-port** (apenas reference ou extract-pattern).

### Marcar origens claras

Sempre que portar código, marcar origem no header do arquivo:

```typescript
// apps/web/server/utils/outbox.ts
//
// Pattern extracted from Stripe webhook dispatcher (2026-09-22).
// Reference: https://stripe.com/docs/webhooks
// Reimplemented for NeoAI; no code copied.
// License of original: MIT (informational only).
```

```python
# addons/neoai_pos/models/pos_order.py
#
# Ported from Odoo CE 18 point_of_sale module (2026-09-22).
# Original: https://github.com/odoo/odoo/tree/18.0/addons/point_of_sale
# License: LGPL-3 (compatible with NeoAI via dynamic linking).
# Modifications:
#   - Renamed models to neoai.* namespace
#   - Added organization_id multi-tenant field
#   - Added RLS-compatible security rules
#   - Migrated <tree> to <list> views (Odoo 19 compliance)
```

```go
// pkg/webhookdispatcher/internal/service/service.go
//
// Pattern extracted from Stripe Go SDK webhook handler (2026-09-22).
// Reference: https://github.com/stripe/stripe-go
// Reimplemented for NeoGo; no code copied.
// License of original: MIT (informational only).
```

## Workflow end-to-end

```
1. system-dissector → dissects/<sistema>/{extract,wiki}/*.md
2. neodoo-integrate → dissects/<sistema>/integrate/{integrate.md, risk-score.md, port-plan/*.md}
3. Anderson review → aprovação ou feedback
4. Story BMAD criada em _bmad-output/implementation-artifacts/
5. Cross-review MiniMax+Kimi (gate obrigatório)
6. Implementação (Amelia + specialists)
7. Validation gates 1-6
8. Merge → deploy (pnpm deploy:prod / Docker Swarm)
9. Retro → atualização de neoai-architecture-patterns.md
```

## Resources

### Skills relacionadas (carregar conforme necessário)

- **`system-dissector`** — gerador dos inputs desta skill.
- **`reverse-engineer`** — RE de binários (IDA/Ghidra/BN/Rizin/Frida).
- **`ai-assisted-re`** — MCP para disassemblers + LLM workflows.
- **`protocol-reverse-engineering`** — RE de protocolos de rede (C2, API).
- **`binary-analysis-patterns`** — pattern library de disassembly.
- **`codebase-audit-pre-push`** — auditoria profunda antes de push.
- **`code-reviewer`** — code review adversarial.
- **`007`** — security audit / hardening.
- **`cred-omega`** — auditoria de credenciais e segredos.
- **`bmad-code-review`** — review adversarial BMAD.
- **`bmad-dev-story`** — execução de story BMAD.
- **`neodoo19-developer`** — skill local para módulos Odoo 19 (Neodoo19Framework).

### Documentos internos do Anderson

- `~/.agent/projects/neoai.md` — postura canônica NeoAI.
- `~/.agent/projects/neodoo19-framework.md` — framework Odoo 19.
- `~/.agent/projects/neogo.md` — canal WhatsApp do NeoAI.
- `~/.agent/projects/universalone.md` — UniversalOne (CGU).
- `~/Nuxt-Agendador/docs/neoai-dev-conventions.md` — base viva de conventions.
- `~/Nuxt-Agendador/CLAUDE.md` — symlink para `.agents/AGENTS.md`.
- `~/projects/neodoo19_framework/framework/standards/ODOO19_CORE_STANDARDS.md` — standards Odoo 19.
- `/Users/andersongoliveira/projects/engenharia reversa/HINDSIGHT/pesquisa-mercado-RE-2025-2026.md` — pesquisa RE 2025-2026.

### Arquivos gerados

- `dissects/<sistema>/integrate/integrate.md`
- `dissects/<sistema>/integrate/risk-score.md`
- `dissects/<sistema>/integrate/port-plan/<componente>-port.md`
- `~/.agent/projects/neoai-architecture-patterns.md` (cross-system)

## References

### Padrões e standards

- **Odoo 19 Core Standards** — `~/projects/neodoo19_framework/framework/standards/ODOO19_CORE_STANDARDS.md` (539 linhas, verificado contra interpretador 2026-08-09).
- **Neodoo19Framework validator** — `python3 framework/validator/validate.py`.
- **BMAD v6.10.0** — instalado em `~/Nuxt-Agendador/_bmad/`.
- **Nuxt 4 docs** — https://nuxt.com/docs/4.x
- **Vue 3.5 docs** — https://vuejs.org/guide/
- **Nuxt UI v4** — `@nuxt/ui` v4 (Free + Pro merged 2026).
- **Vercel AI SDK v7** — provider abstraction + cascade.
- **PostgreSQL 17 docs** — https://www.postgresql.org/docs/17/
- **Go 1.26** — generic features, `slices`, `maps` stdlib.
- **Docker Swarm** — single-node mode (Ubuntu 24.04, 12 vCPU, 23Gi RAM).
- **Stripe API** — idempotency keys, webhook patterns.
- **Shopify Admin API** — webhook redelivery, retry.
- **GitHub Webhooks** — delivery guarantees.
- **LGPL 2.1/3.0** — dynamic linking requirement.
- **Lei 9.610/98** — direito autoral brasileiro (Art. 104).

### Ferramentas de auditoria

- **`go-licenses`** — `go install github.com/google/go-licenses@latest`
- **`pip-licenses`** — `pip install pip-licenses`
- **`licensee`** — Ruby, mas funciona em qualquer repo (GitHub).
- **`reuse lint`** — SPDX compliance (Linux Foundation).

---

**Author note:** skill criada em 2026-09-22 como companion de `system-dissector`. Foco em NeoAI/NeoAISystems (Nuxt 4 + Odoo 19 + NeoGo). Stack refletido em `~/.agent/projects/neoai.md` e conventions em `~/Nuxt-Agendador/docs/neoai-dev-conventions.md`. Toda referência a Odoo 19 segue `ODOO19_CORE_STANDARDS.md` (verificado contra interpretador oficial em 2026-08-09).
