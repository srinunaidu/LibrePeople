"""Client address, host and scheme, honouring forwarded headers only from a trusted proxy.

A request's forwarded headers (``X-Forwarded-For``, ``X-Forwarded-Host``,
``X-Forwarded-Proto``) are written by whoever sent the request unless a proxy
the deployment controls overwrites them. Believing them unconditionally lets a
client:

* rotate ``X-Forwarded-For`` on every attempt, so the per-IP login limiter
  never fills;
* send ``X-Forwarded-Host`` naming another tenant's hostname;
* claim ``X-Forwarded-Proto: https``.

So the headers are honoured only when the *direct TCP peer* is inside
``TRUSTED_PROXY_CIDRS``. The default is empty, so nothing is trusted and the
peer address is the client. No platform or cloud address is listed here; the
deployment names its own proxy.

When the peer is trusted, ``X-Forwarded-For`` is read right to left, skipping
trusted proxies, and the first untrusted address is the client. Reading the
left-most entry would hand the choice to the client.
"""
from __future__ import annotations

import ipaddress
from functools import lru_cache

from fastapi import Request

from app.core.config import settings


def _parse_ip(value: str | None):
    if not value:
        return None
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


@lru_cache(maxsize=8)
def _networks_for(raw: str):
    # Cached on the raw string, so a settings change is picked up by a new
    # value. Tests that change TRUSTED_PROXY_CIDRS get a fresh parse.
    import ipaddress as _ip

    raw = (raw or "").strip()
    if not raw:
        return ()
    return tuple(
        _ip.ip_network(item.strip(), strict=False)
        for item in raw.split(",")
        if item.strip()
    )


def _networks():
    return _networks_for(settings.TRUSTED_PROXY_CIDRS)


def is_trusted_address(value: str | None) -> bool:
    """True when ``value`` is an address inside a configured trusted proxy network."""
    ip = _parse_ip(value)
    if ip is None:
        return False
    return any(ip in net for net in _networks())


def _peer(request: Request) -> str | None:
    return request.client.host if request.client else None


def peer_is_trusted(request: Request) -> bool:
    """True when the direct TCP peer is a trusted proxy."""
    return is_trusted_address(_peer(request))


def client_ip(request: Request) -> str:
    """The address of the client that made the request.

    The direct peer, unless the peer is a trusted proxy, in which case the
    right-most ``X-Forwarded-For`` entry that is not itself a trusted proxy.
    """
    peer = _peer(request)
    if not peer_is_trusted(request):
        return peer or "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if not forwarded:
        return peer or "unknown"
    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    for hop in reversed(hops):
        if _parse_ip(hop) is None:
            # Not an address: refuse to guess, fall back to the peer.
            return peer or "unknown"
        if not is_trusted_address(hop):
            return hop
    return hops[0] if hops else (peer or "unknown")


def forwarded_host(request: Request) -> str | None:
    """``X-Forwarded-Host`` when the peer is trusted, otherwise ``None``."""
    if not peer_is_trusted(request):
        return None
    value = request.headers.get("x-forwarded-host")
    if not value:
        return None
    return value.split(",")[0].strip().lower() or None


def forwarded_proto(request: Request) -> str | None:
    """``X-Forwarded-Proto`` when the peer is trusted, otherwise ``None``."""
    if not peer_is_trusted(request):
        return None
    value = request.headers.get("x-forwarded-proto")
    if not value:
        return None
    return value.split(",")[0].strip().lower() or None
