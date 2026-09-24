# Market Benchmarks — neodissector-pricing

> Benchmarks simplificados para o Cenário 3 (Market) do pricing-estimate.
> NÃO exaustivo — apenas anchors. Atualizar conforme pesquisa de mercado real.

## Estrutura

```yaml
<country>:
  <seniority>:
    hourly_min: <USD/hora>
    hourly_max: <USD/hora>
    source: "<fonte>"
    year: <YYYY>
```

## Tabela (USD/hora, 2026)

### Brasil

| Senioridade | Mín | Máx | Fonte |
|---|---|---|---|
| junior | 8 | 20 | Glassdoor 2026 |
| mid | 18 | 40 | Glassdoor 2026 |
| senior | 35 | 70 | Glassdoor 2026 |
| staff_lead | 60 | 100 | Glassdoor 2026 |
| principal | 90 | 150 | Glassdoor 2026 |

### EUA

| Senioridade | Mín | Máx | Fonte |
|---|---|---|---|
| junior | 50 | 80 | levels.fyi 2026 |
| mid | 80 | 130 | levels.fyi 2026 |
| senior | 130 | 200 | levels.fyi 2026 |
| staff_lead | 200 | 300 | levels.fyi 2026 |
| principal | 300 | 500 | levels.fyi 2026 |

### México

| Senioridade | Mín | Máx | Fonte |
|---|---|---|---|
| junior | 12 | 25 | mercado freelance MX 2026 |
| mid | 25 | 50 | mercado freelance MX 2026 |
| senior | 45 | 90 | mercado freelance MX 2026 |
| staff_lead | 80 | 130 | mercado freelance MX 2026 |
| principal | 120 | 200 | mercado freelance MX 2026 |

---

## Como atualizar

1. Adicionar nova entrada country/seniority.
2. Documentar `source` (URL + data de acesso).
3. Atualizar `year` no frontmatter se mudar ano-base.
4. Manter consistência: rates crescem com senioridade; senior ≥ staff ≥ principal (min).

---

## Histórico

- **2026-09-24**: v1 — tabela inicial (BR, US, MX). Inspirado em `sandeco/reversa` `market-benchmarks.md` v2, simplificado para 3 países.