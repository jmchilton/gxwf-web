"""Content Security Policy header construction for gxwf-web.

Mirrors packages/gxwf-web/src/router.ts buildCspHeader/buildMonacoCspHeader in the
TypeScript reference server.
"""

from typing import (
    List,
    Optional,
    Sequence,
)

# Baseline connect-src origins: the public Galaxy ToolShed for direct tool-cache
# reads. Per-deployment tool-cache proxies or alternate ToolShed mirrors extend
# this via extra_connect_src. The Monaco extension is served from /ext/ on this
# same origin (staged-unpacked .vsix), so no extra origins are needed for the
# extension file fetches.
CSP_CONNECT_SRC_BASE = ["https://toolshed.g2.bx.psu.edu"]


def _join_connect_src(extra: Optional[Sequence[str]]) -> str:
    parts: List[str] = ["'self'", *CSP_CONNECT_SRC_BASE]
    if extra:
        parts.extend(extra)
    return " ".join(parts)


def build_csp_header(extra_connect_src: Optional[Sequence[str]] = None) -> str:
    """Baseline CSP for the Vue shell and API responses."""
    connect_src = _join_connect_src(extra_connect_src)
    return "; ".join(
        [
            "default-src 'self'",
            "script-src 'self' 'wasm-unsafe-eval'",
            "worker-src 'self' blob:",
            "frame-src 'self' blob:",
            f"connect-src {connect_src}",
            "style-src 'self' 'unsafe-inline'",
            "font-src 'self' data:",
            "img-src 'self' data:",
        ]
    )


def build_monaco_csp_header(extra_connect_src: Optional[Sequence[str]] = None) -> str:
    """Permissive CSP served only for /monaco/* assets (extension-host iframe + workers).

    The iframe ships its own meta CSP tight enough for the extension host; the HTTP
    CSP here just needs to be permissive enough not to intersect that meta policy
    into uselessness. Inline scripts + 'unsafe-eval' are the extension host's
    baseline requirements.
    """
    connect_src = _join_connect_src(extra_connect_src)
    return "; ".join(
        [
            "default-src 'self' blob: data:",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' blob:",
            "worker-src 'self' blob:",
            "frame-src 'self' blob:",
            f"connect-src {connect_src}",
            "style-src 'self' 'unsafe-inline'",
            "font-src 'self' data:",
            "img-src 'self' data: blob:",
        ]
    )
