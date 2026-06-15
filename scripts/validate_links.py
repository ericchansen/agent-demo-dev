#!/usr/bin/env python3
"""Validate public external links in markdown documentation.

The validator intentionally ignores code fences, localhost URLs, template URLs,
and authenticated service endpoints such as Foundry project API URLs. Those are
configuration examples, not public browser links.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = (ROOT / "README.md", ROOT / "website" / "docs", ROOT / "docs")
URL_PATTERN = re.compile(r"https?://[^\s\)\]\}\"<>]+")
SUCCESS_STATUS_RANGE = range(200, 400)


@dataclass(frozen=True)
class LinkCheck:
    """Result for one public external link."""

    url: str
    status: int | None
    ok: bool
    reason: str


def iter_markdown_files(paths: Iterable[Path]) -> list[Path]:
    """Return markdown files from explicit files or directories."""

    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() in {".md", ".mdx"}:
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(item for item in path.rglob("*") if item.suffix.lower() in {".md", ".mdx"}))
    return sorted(dict.fromkeys(files))


def extract_public_urls(markdown: str) -> set[str]:
    """Extract public URLs while ignoring fenced code samples and placeholders."""

    urls: set[str] = set()
    in_fence = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for match in URL_PATTERN.finditer(line):
            url = match.group(0).rstrip(".,;:`")
            if should_validate(url):
                urls.add(url)
    return urls


def should_validate(url: str) -> bool:
    """Return whether a URL should be treated as a public link."""

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1"}:
        return False
    if host.endswith(".example.com") or host in {"example.com", "your-endpoint.openai.azure.com"}:
        return False
    if "{" in url or "}" in url or "<" in url or ">" in url:
        return False
    if host.endswith(".services.ai.azure.com") and "/api/projects/" in parsed.path:
        return False
    return True


def check_url(url: str, timeout_seconds: float) -> LinkCheck:
    """Check a URL with HEAD and fall back to GET for hosts that reject HEAD."""

    headers = {"User-Agent": "agent-demo-dev-link-validator/1.0"}
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                status = response.getcode()
                return LinkCheck(url=url, status=status, ok=status in SUCCESS_STATUS_RANGE, reason="http")
        except urllib.error.HTTPError as exc:
            if method == "HEAD" and exc.code in {403, 405, 429}:
                continue
            return LinkCheck(url=url, status=exc.code, ok=exc.code in SUCCESS_STATUS_RANGE, reason="http-error")
        except urllib.error.URLError as exc:
            if method == "HEAD":
                continue
            return LinkCheck(url=url, status=None, ok=False, reason=str(exc.reason))
        except TimeoutError:
            if method == "HEAD":
                continue
            return LinkCheck(url=url, status=None, ok=False, reason="timeout")
    return LinkCheck(url=url, status=None, ok=False, reason="unknown")


def collect_urls(files: Iterable[Path]) -> set[str]:
    """Collect unique public URLs from markdown files."""

    urls: set[str] = set()
    for path in files:
        urls.update(extract_public_urls(path.read_text(encoding="utf-8")))
    return urls


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate public documentation links.")
    parser.add_argument("paths", nargs="*", type=Path, default=list(DEFAULT_PATHS))
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-request timeout in seconds.")
    args = parser.parse_args(argv)

    files = iter_markdown_files(path if path.is_absolute() else ROOT / path for path in args.paths)
    urls = sorted(collect_urls(files))
    results = [check_url(url, args.timeout) for url in urls]
    failures = [result for result in results if not result.ok]

    print(f"Markdown files: {len(files)}")
    print(f"Public external links checked: {len(results)}")
    if failures:
        print("Failed links:")
        for failure in failures:
            status = failure.status if failure.status is not None else "n/a"
            print(f"- {failure.url} [{status}] {failure.reason}")
        return 1
    print("All public external links resolved.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
