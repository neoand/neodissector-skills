# Sanitization Rules — neodissector-sanitizer

Catálogo das regras que `sanitize.py` aplica ao transformar `dissects/<s>/` em `<consumer-package>/`.

## 1. Paths verbatim (BLOCK)

**Pattern**: 
```
addons/[\w_-]+(/[\w_-]+)*\.py
addons/[\w_-]+(/[\w_-]+)*/[\w_-]+/[\w_-]+\.xml
[\w_]+\.py:\d+        # file:line ref
```

**Replacement**: descrição conceitual. 

| Antes | Depois |
|---|---|
| `addons/account_accountant/models/account_reports.py:55` | "Método do módulo de relatórios fiscais que calcula o total" |
| `mail/controller/main.py:18-20` | "Endpoint público do módulo de comms" |
| `i18n/pt_BR.po:42` | "Arquivo de tradução PT-BR" |

O `verify-no-verbatim.py` detecta esses patterns via regex.

## 2. Imports verbatim (BLOCK)

**Pattern**: 
```
^from\s+odoo(\.addons\.[\w_-]+)?(\.[\w_]+)*\s+import\s+.*
^import\s+odoo(\.addons)?[\w_.]*
```

**Replacement**: referência genérica à API.

| Antes | Depois |
|---|---|
| `from odoo.addons.account_accountant.models.account_move import AccountMove` | "API Odoo ORM (modelos de domínio)" |
| `from odoo import models, fields, api` | "API Odoo framework core" |
| `import odoo.addons.mail.models.mail_thread` | "API de modelo cross-cutting (chat/activity)" |

## 3. Function/Method signatures (BLOCK)

**Pattern**:
```
^\s*(def|async\s+def)\s+\w+\(.*?\)\s*[:-].*?
```

Captura só a primeira linha de uma assinatura (até `:` ou `->`).

**Replacement**: "Função que <verbo>...".

| Antes | Depois |
|---|---|
| `def _compute_tax_amount(base, rate, precision):` | "Função que calcula imposto a partir de base, alíquota e precisão" |
| `def message_post(self, body='', subtype_xmlid=None, **kwargs):` | "Função que publica mensagem no chatter, com tipo e kwargs" |

## 4. Class names verbatim (BLOCK)

**Pattern**: uppercase inicial + ends em `View`, `Template`, `Model`, `Wizard`, `Mixin`:

**Replacement**: descrição genérica do papel.

| Antes | Depois |
|---|---|
| `class AccountMoveTemplate(models.Model)` | "Modelo ORM que representa template de movimento contábil" |
| `class SaleSubscriptionCloseReasonWizard(models.TransientModel)` | "Wizard que captura o motivo do encerramento de subscription" |

## 5. Constants verbatim (BLOCK)

**Pattern**:
```
^\s*\w+\s*=\s*\d+(\.\d+)?\s*$
```
em um contexto onde se parece "constant" (não tabela de constantes).

Mais heurístico: número `> 100` numa linha contextualmente "weight", "timeout", "threshold".

**Replacement**: descrição qualitativa.

| Antes | Depois |
|---|---|
| `_DEFAULT_PURCHASE_AMOUNT = 250.00` | "Valor padrão configurável (recuperar de .env)" |
| `TIMEOUT_SECONDS = 1200` | "Timeout recomendado 120s (não 1200)" |
| `MIN_AMOUNT_THRESHOLD = 0.01` | "Threshold mínimo fracional" |

## 6. Vendor SDK references (BLOCK)

**Pattern**: imports de bibliotecas específicas do vendor-A.

**Replacement**: "biblioteca de mercado sob licença compatível".

## 7. URL/process/host verbatim (BLOCK)

**Pattern**: 
- `localhost:\d+`
- `127\.0\.0\.1`
- `https?://[\w.-]+\.odoo\.com`
- `https?://[\w.-]+\.vendor-A\.com`

**Replacement**: descrição genérica ou remoção.

## 8. Manifest / __manifest__.py (SPECIAL)

**Pattern**: nome do módulo (`'name': 'Account Account'`), versão, depende (módulos).

**Replacement**: manter categoria (`Accounting`) + descrição funcional, removendo nome verbatim + path.

## 9. Tabelas/SQL verbatim (WARN)

Tabelas com nomes explícitos (`account_move_line`, `sale_order_line`) são permitidas (são de domínio). Mas **SQL statements verbatim** (`SELECT ... FROM account_move WHERE...`) viram descrição do que a query faz.

## 10. Frases-gatilho de verbatim (PADRÃO)

Detecta frases que geralmente indicam citação direta: "the original source code", "from the file", "in `<file>`", etc.

**Replacement**: paráfrase.

## Padrão geral de substituição

A skill mantém uma **tabela de substituições** que pode ser customizada pelo Anderson. Para v1, todas as substituições são **determinísticas** (regex-based). Para casos ambíguos, a skill chama o `inspect` mode para revisão humana.

## Limitações conhecidas

- Comentários em código fonte com texto rico não são detectados
- Documentação que explica "WHY" é passada intacta (informação factual)
- Nomes de técnicas/patterns públicos (CRC, BFS, FSM) passam

Para os casos difíceis, a skill recomenda **consulta ao legal counsel**.