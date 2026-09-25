#!/usr/bin/env python3
"""
discover-api.py — descoberta automática de OpenAPI/Swagger/GraphQL endpoints.

Tenta URLs canônicas onde vendors costumam publicar specs:
- /api/v1/openapi.json
- /api/openapi.json
- /openapi.json
- /api/v2/openapi.json
- /swagger.json
- /swagger/v1/swagger.json
- /api/graphql (introspection query)
- /graphql (introspection)
- /api-docs
- /docs/openapi.json
- /.well-known/openapi

Também tenta detectar:
- Stack via HTTP headers (Server, X-Powered-By)
- Stack via HTML (meta name="generator", link to /docs/)
- Auth flow via WWW-Authenticate
- WAF/Reverse-proxy via Server + Via

Uso:
    python3 discover-api.py --base-url https://app.vendor.com
    python3 discover-api.py --base-url https://app.vendor.com --output-dir evidence/
    python3 discover-api.py --help

Exit codes:
    0 = achou pelo menos 1 endpoint
    1 = nada encontrado (apenas headers/HTML)
    2 = erro de uso
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.parse


# URL candidates em ordem de probabilidade
URL_CANDIDATES = (
    "/api/v1/openapi.json",
    "/api/openapi.json",
    "/api/v2/openapi.json",
    "/api/v3/openapi.json",
    "/openapi.json",
    "/openapi.yaml",
    "/swagger.json",
    "/swagger.yaml",
    "/swagger/v1/swagger.json",
    "/api-docs",
    "/v1/api-docs",
    "/v2/api-docs",
    "/api/graphql",
    "/graphql",
    "/.well-known/openapi",
    "/docs/openapi.json",
    "/redoc",
    "/spec",
)


def _try_url(base_url: str, path: str) -> dict | None:
    """Tenta GET em base_url/path e retorna JSON parseável, ou None."""
    url = urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
    try:
        # Import lazy
        import urllib.request

        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json, application/yaml, text/yaml"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            ctype = resp.headers.get("content-type", "").lower()
            body = resp.read().decode("utf-8", errors="replace")
            if "json" in ctype or body.lstrip().startswith(("{", "[")):
                try:
                    return json.loads(body)
                except json.JSONDecodeError:
                    return None
            return None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        return None


def discover(base_url: str) -> dict:
    """Tenta cada URL candidate. Retorna summary."""
    results = {
        "base_url": base_url,
        "candidates_tried": [],
        "openapi": None,  # spec parseada
        "graphql_introspection": None,  # se /graphql responde com introspection
        "headers": {},  # meta-stack via headers
        "html_meta": {},  # generator/version
    }

    for path in URL_CANDIDATES:
        candidate_url = urllib.parse.urljoin(
            base_url.rstrip("/") + "/", path.lstrip("/")
        )
        data = _try_url(base_url, path)
        results["candidates_tried"].append(
            {"path": path, "url": candidate_url, "ok": data is not None}
        )

        if (
            data
            and "openapi" in str(data)[:200].lower()
            or (isinstance(data, dict) and "openapi" in data)
        ):
            results["openapi"] = {
                "url": candidate_url,
                "spec": data,
                "title": data.get("info", {}).get("title", "?"),
                "version": data.get("info", {}).get("version", "?"),
            }
            break

        # GraphQL introspection
        if path == "/graphql" or path == "/api/graphql":
            try:
                import urllib.request

                req = urllib.request.Request(
                    urllib.parse.urljoin(base_url.rstrip("/") + "/", path.lstrip("/")),
                    data=b'{"query":"{ __schema { queryType { name } } }"}',
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                    if "data" in payload and "__schema" in payload["data"]:
                        results["graphql_introspection"] = {
                            "url": candidate_url,
                            "endpoint": path,
                            "schema_root": payload["data"]["__schema"],
                        }
            except Exception:
                pass

    # Headers (root)
    try:
        import urllib.request

        req = urllib.request.Request(base_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            for k in ("Server", "X-Powered-By", "Via", "X-Generator", "Content-Type"):
                if k in resp.headers:
                    results["headers"][k] = resp.headers[k]
    except Exception:
        pass

    return results


def flatten_endpoints(openapi_spec: dict) -> list[dict]:
    """OpenAPI 3.x → flat list de endpoints."""
    endpoints = []
    paths = openapi_spec.get("paths", {})
    for path, methods in paths.items():
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            endpoints.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operation_id": op.get("operationId", ""),
                    "summary": op.get("summary", ""),
                    "tags": op.get("tags", []),
                    "parameters": [
                        {
                            "name": p.get("name"),
                            "in": p.get("in"),
                            "required": p.get("required", False),
                        }
                        for p in op.get("parameters", [])
                    ],
                }
            )
    return endpoints


def render_endpoints_table(endpoints: list[dict]) -> str:
    md = "| Method | Path | Operation ID | Tags |\n"
    md += "|--------|------|---------------|------|\n"
    for e in endpoints:
        tags = ", ".join(e.get("tags", []))
        md += f"| {e['method']} | `{e['path']}` | `{e['operation_id']}` | {tags} |\n"
    return md


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="URL base do sistema-alvo")
    parser.add_argument(
        "--output-dir", default="evidence/api-spec", help="Diretório de output"
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    out = pathlib.Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    result = discover(args.base_url)

    # Save full discovery log
    (out / "discovery.log.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Save OpenAPI spec if found
    if result["openapi"]:
        spec_path = out / "openapi.json"
        spec_path.write_text(
            json.dumps(result["openapi"]["spec"], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        # Flatten endpoints
        endpoints = flatten_endpoints(result["openapi"]["spec"])
        (out / "endpoints.json").write_text(
            json.dumps(endpoints, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (out / "endpoints.md").write_text(
            f"# Endpoints descobertos: {result['openapi']['title']} v{result['openapi']['version']}\n\n"
            f"Source: `{result['openapi']['url']}`\n\n"
            + render_endpoints_table(endpoints),
            encoding="utf-8",
        )

    # Save GraphQL schema if found
    if result["graphql_introspection"]:
        (out / "graphql-introspection.json").write_text(
            json.dumps(result["graphql_introspection"], indent=2, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

    # Save detected stack
    stack_md = f"# Detected stack\n\n**Base URL**: {result['base_url']}\n\n"
    stack_md += "## HTTP headers (root)\n\n"
    if result["headers"]:
        for k, v in result["headers"].items():
            stack_md += f"- `{k}`: `{v}`\n"
    else:
        stack_md += "_(none captured)_\n"
    stack_md += "\n## Candidates tried\n\n"
    stack_md += "| Path | URL | Hit? |\n|------|-----|------|\n"
    for c in result["candidates_tried"]:
        stack_md += f"| `{c['path']}` | {c['url']} | {'✓' if c['ok'] else '✗'} |\n"
    stack_md += "\n## Results\n\n"
    if result["openapi"]:
        stack_md += f"- ✓ **OpenAPI**: `{result['openapi']['url']}` ({result['openapi']['title']} v{result['openapi']['version']})\n"
    else:
        stack_md += "- ✗ No OpenAPI/Swagger spec found\n"
    if result["graphql_introspection"]:
        stack_md += (
            f"- ✓ **GraphQL**: `{result['graphql_introspection']['endpoint']}`\n"
        )
    else:
        stack_md += "- ✗ No GraphQL endpoint found\n"
    (out / "detected-stack.md").write_text(stack_md, encoding="utf-8")

    if not args.quiet:
        print(f"[*] Output: {out}")
        if result["openapi"]:
            print(f"[+] OpenAPI: {result['openapi']['url']}")
            print(
                f"    Title: {result['openapi']['title']} v{result['openai']['version']}"
            )
            endpoints = flatten_endpoints(result["openai"]["spec"])
            print(f"    Endpoints: {len(endpoints)}")
        if result["graphql_introspection"]:
            print(f"[+] GraphQL: {result['graphql_introspection']['endpoint']}")
        if not result["openapi"] and not result["graphql_introspection"]:
            print("[-] Nenhuma API pública descoberta nos URLs canônicas")
            print("    Próximo: usar capture-network.py + screenshot-flow.py")

    return 0 if (result["openapi"] or result["graphql_introspection"]) else 1


if __name__ == "__main__":
    sys.exit(main())
