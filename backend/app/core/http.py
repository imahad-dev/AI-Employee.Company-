from __future__ import annotations

import httpx

_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("Shared HTTP client is not initialized")
    return _client


def set_http_client(client: httpx.AsyncClient | None) -> None:
    global _client
    _client = client
