# Playwright RE Recipes — 7 padrões prontos

Casos típicos de dissecação UI-only. **Sempre rodar `discover-api.py` primeiro.**

## Recipe 1 — OpenAPI/GraphQL discovery automático

```python
import subprocess
subprocess.run([
    "python3", "/Users/andersongoliveira/.agents/skills/playwright-re/resources/scripts/discover-api.py",
    "--base-url", "https://app.vendor.com",
    "--output-dir", "evidence/api-spec",
])
```

Output esperado: `evidence/api-spec/{openapi.json, endpoints.txt, examples.json, discovery.log}`.

## Recipe 2 — Login flow + capture screenshots

```python
# screenshot-flow.py --config auth-flow.yaml
python3 /Users/andersongoliveira/.agents/skills/playwright-re/resources/scripts/screenshot-flow.py \
  --config evidence/auth-flow.yaml
```

`auth-flow.yaml`:
```yaml
- name: login
  url: https://app.vendor.com/login
  actions:
    - fill: 'input[name="email"]' = "demo@vendor.com"
    - fill: 'input[name="password"]' = "demo123"
    - click: 'button[type="submit"]'
    - wait_for: networkidle
- name: dashboard
  url: https://app.vendor.com/dashboard
  actions:
    - wait_for: networkidle
    - screenshot: "evidence/screenshots/dashboard.png"
```

## Recipe 3 — Network capture full session

```python
# capture-network.py (full HAR)
python3 /Users/andersongliveira/.agents/skills/playwright-re/resources/scripts/capture-network.py \
  --url "https://app.vendor.com/explore?action=run" \
  --actions-file "actions.yaml" \
  --output evidence/network/full-session.har
```

Resulta em HAR completo (request + response + headers + body), navegável com `playwright-trace` ou `chrome://net-export/`.

## Recipe 4 — SPA crawl (descobre rotas + DOM)

```python
# crawl-spa.py — para Angular/React/Vue SPAs
python3 /Users/andersongoliveira/.agents/skills/playwright-re/resources/scripts/crawl-spa.py \
  --base-url "https://app.vendor.com" \
  --max-depth 3 \
  --route-pattern "/api/v1/{path}" \
  --output evidence/web/
```

Output: `evidence/web/dom-{path}.html`, lista de rotas descobertas, JS asset URLs.

## Recipe 5 — GraphQL introspection

```python
# discover-api.py detecta GraphQL em /api/graphql ou /graphql
# Para introspection:
python3 -c "
from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    response = page.request.post(
        'https://api.vendor.com/graphql',
        data={'query': '{ __schema { queryType { name } } }'},
    )
    schema = response.json()  # JSON Schema of the API
    with open('evidence/api-spec/graphql-schema.json', 'w') as f:
        json.dump(schema, f, indent=2)
"
```

## Recipe 6 — Console + trace capture (deep debugging)

```python
# trace-session.py
python3 /Users/andersongoliveira/.agents/skills/playwright-re/resources/scripts/trace-session.py \
  --url "https://app.vendor.com/buggy-page" \
  --steps-file "buggy-steps.yaml" \
  --output evidence/trace.zip
```

`trace.zip` é o Playwright Trace Viewer — abre em `https://trace.playwright.dev/` para replay visual.

## Recipe 7 — Auth flow + token persistence

```python
import subprocess
# Login uma vez, salvar cookies + localStorage
python3 -c "
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context()
    page = ctx.new_page()
    page.goto('https://app.vendor.com/login')
    page.fill('input[name=email]', 'demo@vendor.com')
    page.fill('input[name=password]', 'demo123')
    page.click('button[type=submit]')
    page.wait_for_load_state('networkidle')
    ctx.storage_state(path='evidence/auth/cookies.json')
    b.close()
"

# Replay em sessões futuras (sem re-login)
python3 -c "
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(storage_state='evidence/auth/cookies.json')
    page = ctx.new_page()
    page.goto('https://app.vendor.com/dashboard')
    page.screenshot(path='evidence/replay-dashboard.png')
    b.close()
"
```

> ⚠️ **Cookies persistidos NUNCA vão para consumer-package**. Use sanitizer.