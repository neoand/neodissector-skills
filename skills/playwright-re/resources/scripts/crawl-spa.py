#!/usr/bin/env python3
"""
crawl-spa.py — crawler para SPAs (React/Angular/Vue).

Siga links internos + tira screenshots de cada rota + extrai DOM.
Útil para SPAs que escondem rotas atrás de JavaScript routing.

Uso:
    python3 crawl-spa.py --base-url https://app.vendor.com --max-depth 3
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
from urllib.parse import urljoin, urlparse


def _import_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright não instalado.", file=sys.stderr)
        sys.exit(1)
    return sync_playwright


def is_same_domain(url: str, base_domain: str) -> bool:
    try:
        return urlparse(url).netloc == base_domain
    except Exception:
        return False


def normalize(url: str) -> str:
    """Remove fragment + trailing slash."""
    try:
        u = urlparse(url)
        return u._replace(fragment="").geturl().rstrip("/")
    except Exception:
        return url


def crawl(
    base_url: str,
    max_depth: int = 2,
    output_dir: pathlib.Path = pathlib.Path("evidence/web"),
    route_filter_regex: str | None = None,
) -> int:
    sync_playwright = _import_playwright()

    base_domain = urlparse(base_url).netloc
    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(base_url, 0)]
    routes: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        while queue:
            url, depth = queue.pop(0)
            if depth > max_depth:
                continue
            url_norm = normalize(url)
            if url_norm in visited:
                continue
            visited.add(url_norm)

            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
            except Exception as e:
                continue

            # Extract DOM
            html = page.content()
            dom_path = (
                output_dir
                / "dom"
                / f"{url_norm.replace('/', '_').replace(':', '_')}.html"
            )
            dom_path.parent.mkdir(parents=True, exist_ok=True)
            dom_path.write_text(html, encoding="utf-8")

            # Screenshot
            screenshot_path = (
                output_dir
                / "screenshots"
                / f"{url_norm.replace('/', '_').replace(':', '_')}.png"
            )
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot_path), full_page=True)

            routes.append(
                {
                    "url": url_norm,
                    "depth": depth,
                    "title": page.title(),
                    "screenshot": str(screenshot_path.relative_to(output_dir)),
                    "dom_size_bytes": len(html),
                }
            )

            # Discover links
            if depth < max_depth:
                import re

                link_pattern = re.compile(r'href=["\']([^"\']+)["\']')
                for href in link_pattern.findall(html):
                    full_url = urljoin(url_norm + "/", href)
                    full_url = normalize(full_url)
                    if not is_same_domain(full_url, base_domain):
                        continue
                    if route_filter_regex and not re.search(
                        route_filter_regex, full_url
                    ):
                        continue
                    if "#" in full_url:
                        continue
                    if "javascript:" in full_url.lower():
                        continue
                    if full_url not in visited:
                        queue.append((full_url, depth + 1))

        browser.close()

    # Write routes index
    index_path = output_dir / "routes.md"
    index_md = f"# SPA crawl: {base_url}\n\n"
    index_md += f"- Visited: {len(visited)} routes\n"
    index_md += f"- Screenshots: {output_dir}/screenshots/\n"
    index_md += f"- DOM dumps: {output_dir}/dom/\n\n"
    index_md += (
        "| Depth | URL | Title | DOM size |\n|-------|-----|-------|-----------|\n"
    )
    for r in sorted(routes, key=lambda x: (x["depth"], x["url"])):
        index_md += f"| {r['depth']} | `{r['url']}` | {r['title']} | {r['dom_size_bytes']:,} |\n"

    index_path.write_text(index_md, encoding="utf-8")

    # Write machine-readable
    (output_dir / "routes.json").write_text(
        json.dumps(
            {"routes": routes, "visited": sorted(visited)}, indent=2, ensure_ascii=False
        ),
        encoding="utf-8",
    )

    print(f"[+] {len(visited)} rotas")
    print(f"[+] {index_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="URL base do SPA")
    parser.add_argument(
        "--max-depth", type=int, default=2, help="Profundidade máxima de links"
    )
    parser.add_argument(
        "--output-dir", default="evidence/web", help="Diretório de output"
    )
    parser.add_argument(
        "--route-pattern", help="Regex para filtrar rotas (ex: '/api/v1/.*')"
    )
    args = parser.parse_args()
    return crawl(
        base_url=args.base_url,
        max_depth=args.max_depth,
        output_dir=pathlib.Path(args.output_dir),
        route_filter_regex=args.route_pattern,
    )


if __name__ == "__main__":
    sys.exit(main())
