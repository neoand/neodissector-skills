#!/usr/bin/env python3
"""
capture-network.py — captura HAR completo via Playwright + Chromium.

Usa Playwright sync API + page.context.route() para interceptar todas as
requests. Output = arquivo HAR (HTTP Archive) navegável em
`chrome://net-export/` ou `https://requestbin.github.io/request-inspector/`.

Uso:
    python3 capture-network.py --url https://app.vendor.com/login
    python3 capture-network.py --actions actions.yaml
    python3 capture-network.py --url <url> --username demo@vendor.com --password demo123

Exit codes:
    0 = sucesso
    1 = erro de execução
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from typing import Any


def _import_playwright():
    """Lazy import para erro claro se não instalado."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright não instalado.", file=sys.stderr)
        print("   pip install playwright", file=sys.stderr)
        print("   playwright install chromium", file=sys.stderr)
        sys.exit(1)
    return sync_playwright


def capture(
    url: str,
    output_har: pathlib.Path,
    actions_path: pathlib.Path | None = None,
    username: str | None = None,
    password: str | None = None,
    headless: bool = True,
) -> int:
    sync_playwright = _import_playwright()

    requests_log: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Neodissector-PlaywrightRE/0.1 (Anderson 2026-09-25)",
        )

        # HAR-like log via route
        def on_request(req):
            requests_log.append(
                {
                    "type": "request",
                    "method": req.method,
                    "url": req.url,
                    "headers": dict(req.headers),
                    "post_data": req.post_data,
                    "timestamp": time.time(),
                }
            )

        def on_response(res):
            try:
                body = res.body()
                body_str = body.decode("utf-8", errors="replace")[:4096]
            except Exception:
                body_str = None
            requests_log.append(
                {
                    "type": "response",
                    "url": res.url,
                    "status": res.status,
                    "headers": dict(res.headers),
                    "body_excerpt": body_str,
                    "timestamp": time.time(),
                }
            )

        context.on("request", on_request)
        context.on("response", on_response)

        page = context.new_page()

        # Capture console logs
        console_log: list[dict] = []
        page.on(
            "console",
            lambda msg: console_log.append(
                {
                    "type": msg.type,
                    "text": msg.text,
                    "location": msg.location,
                }
            ),
        )

        # Navigate
        page.goto(url, wait_until="networkidle")

        # Optional login
        if username and password:
            try:
                page.fill('input[name="email"], input[type="email"]', username)
                page.fill('input[name="password"], input[type="password"]', password)
                page.click('button[type="submit"]')
                page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"[!] Login flow falhou: {e}", file=sys.stderr)

        # Optional actions
        if actions_path and actions_path.exists():
            actions = json.loads(actions_path.read_text())
            for action in actions:
                a_type = action.get("type")
                if a_type == "fill":
                    page.fill(action["selector"], action["value"])
                elif a_type == "click":
                    page.click(action["selector"])
                    page.wait_for_load_state("networkidle", timeout=10000)
                elif a_type == "wait":
                    page.wait_for_timeout(action.get("ms", 1000))
                elif a_type == "screenshot":
                    page.screenshot(path=action["path"], full_page=True)

        browser.close()

    # Write HAR-like JSON
    output_har.parent.mkdir(parents=True, exist_ok=True)
    har = {
        "log": {
            "version": "1.2",
            "creator": {"name": "Neodissector Playwright RE", "version": "0.1"},
            "entries": [
                {
                    "startedDateTime": time.strftime(
                        "%Y-%m-%dT%H:%M:%S", time.localtime(req["timestamp"])
                    ),
                    "request": {
                        "method": req.get("method"),
                        "url": req.get("url"),
                        "headers": [
                            {"name": k, "value": v}
                            for k, v in (req.get("headers") or {}).items()
                        ],
                        "postData": {"text": req.get("post_data")}
                        if req.get("post_data")
                        else None,
                    },
                    "response": {
                        "status": req.get("status"),
                        "headers": [
                            {"name": k, "value": v}
                            for k, v in (req.get("headers") or {}).items()
                        ],
                        "content": {"text": req.get("body_excerpt") or ""}
                        if req.get("body_excerpt")
                        else None,
                    },
                    "cache": {},
                    "timings": {"send": 0, "wait": 0, "receive": 0},
                }
                for req in requests_log
                if req["type"] == "request"
            ],
        }
    }
    output_har.write_text(
        json.dumps(har, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Write console log separately
    console_path = output_har.parent / "console.log"
    console_path.write_text(
        "\n".join(f"[{c['type']}] {c['text']}" for c in console_log),
        encoding="utf-8",
    )

    # Write a summary
    requests_only = [r for r in requests_log if r["type"] == "request"]
    responses_only = [r for r in requests_log if r["type"] == "response"]
    summary = f"# Network capture summary\n\n"
    summary += f"- URL: {url}\n"
    summary += f"- Total requests: {len(requests_only)}\n"
    summary += f"- Total responses: {len(responses_only)}\n"
    summary += f"- Console entries: {len(console_log)}\n\n"
    summary += "## Status code distribution\n\n"
    status_dist = {}
    for r in responses_only:
        s = r.get("status") or 0
        status_dist[s] = status_dist.get(s, 0) + 1
    for status, count in sorted(status_dist.items()):
        summary += f"- HTTP {status}: {count}\n"
    summary += "\n## Hosts contacted (unique)\n\n"
    hosts = set()
    for r in requests_only:
        from urllib.parse import urlparse

        try:
            hosts.add(urlparse(r["url"]).netloc)
        except Exception:
            pass
    for h in sorted(hosts):
        summary += f"- {h}\n"

    summary_path = output_har.parent / "capture-summary.md"
    summary_path.write_text(summary, encoding="utf-8")

    print(f"[+] HAR: {output_har} ({len(requests_only)} requests)")
    print(f"[+] Console: {console_path}")
    print(f"[+] Summary: {summary_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="URL inicial")
    parser.add_argument(
        "--output", default="evidence/network/capture.har", help="Path do HAR"
    )
    parser.add_argument("--actions", help="YAML/JSON com ações pós-load")
    parser.add_argument("--username", help="Form login: email")
    parser.add_argument("--password", help="Form login: password")
    parser.add_argument(
        "--no-headless", action="store_true", help="Mostrar browser (debug)"
    )
    args = parser.parse_args()

    return capture(
        url=args.url,
        output_har=pathlib.Path(args.output),
        actions_path=pathlib.Path(args.actions) if args.actions else None,
        username=args.username,
        password=args.password,
        headless=not args.no_headless,
    )


if __name__ == "__main__":
    sys.exit(main())
