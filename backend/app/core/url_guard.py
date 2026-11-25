"""Outbound URL guard: every server-side HTTP request goes through :func:`fetch`.

The platform makes outbound requests on behalf of users: the client-onboarding
connectivity check, the migration job fetch and webhook delivery. Each one can
be pointed at an address the server can reach but the caller should not, such
as the cloud metadata service or an internal database. This module is the one
place those requests are validated.

Rules
-----
* **https only.** ``http`` is refused. (Default choice, recorded for the owner.)
* **No embedded credentials** in the URL. Credentials come from the stored
  configuration, never from the URL.
* **Blocked destinations**, refused whether given as a literal or resolved from
  a name: loopback (``127.0.0.0/8``, ``::1``), link-local (``169.254.0.0/16``,
  which includes the metadata address ``169.254.169.254``, and ``fe80::/10``),
  RFC 1918 private (``10/8``, ``172.16/12``, ``192.168/16``), carrier-grade NAT
  (``100.64.0.0/10``), ``0.0.0.0/8`` and ``::``, IPv6 unique-local
  (``fc00::/7``), and also multicast and reserved ranges. IPv4-mapped and
  NAT64 IPv6 forms are unwrapped and checked as IPv4.
* **Fail closed on names.** If a name resolves to *any* blocked address the
  whole name is refused, not just the blocked answer.
* **Resolve once, connect to the validated address.** The name is resolved one
  time per hop. The connection goes to that address, with TLS verified against
  the original name. A second DNS answer (DNS rebinding) is never used.
* **Redirects are not followed silently.** Each ``Location`` is validated as a
  new request, the number of hops is capped, and ``Authorization`` is dropped
  when a redirect leaves the original host.

The resolver and the transport are injectable so the rules can be tested
without a network. Production code calls :func:`fetch` with the defaults.
"""
from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
from dataclasses import dataclass
from typing import Callable, Mapping
from urllib.parse import urljoin, urlsplit

#: Redirects followed before the request is refused.
MAX_REDIRECTS = 3

#: Largest response body read. Integration payloads are JSON lists; a larger
#: body is refused rather than buffered.
MAX_RESPONSE_BYTES = 2 * 1024 * 1024

REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

_BLOCKED_NETWORKS: tuple = tuple(
    ipaddress.ip_network(n)
    for n in (
        # IPv4
        "0.0.0.0/8",  # "this network", includes 0.0.0.0
        "10.0.0.0/8",  # RFC 1918
        "100.64.0.0/10",  # carrier-grade NAT
        "127.0.0.0/8",  # loopback
        "169.254.0.0/16",  # link-local, includes the metadata address
        "172.16.0.0/12",  # RFC 1918
        "192.168.0.0/16",  # RFC 1918
        "224.0.0.0/4",  # multicast
        "240.0.0.0/4",  # reserved
        "255.255.255.255/32",  # broadcast
        # IPv6
        "::/128",  # unspecified
        "::1/128",  # loopback
        "fc00::/7",  # unique local
        "fe80::/10",  # link-local
        "ff00::/8",  # multicast
    )
)

_NAT64 = ipaddress.ip_network("64:ff9b::/96")


class UnsafeURLError(ValueError):
    """The URL may not be fetched by the server. The message says why."""


@dataclass(frozen=True)
class ValidatedTarget:
    """A URL that has passed validation, with the one address it may use."""

    url: str
    scheme: str
    host: str  # the name, used for TLS verification and the Host header
    port: int
    ip: str  # the validated address the connection is made to
    path: str  # path and query, as requested

    @property
    def host_header(self) -> str:
        default = 443 if self.scheme == "https" else 80
        return self.host if self.port == default else f"{self.host}:{self.port}"


@dataclass(frozen=True)
class OutboundResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


Resolver = Callable[[str, int], list]
Transport = Callable[[ValidatedTarget, str, Mapping[str, str], bytes | None, float], OutboundResponse]


def _unwrap(ip):
    """IPv4-mapped (::ffff:a.b.c.d) and NAT64 (64:ff9b::a.b.c.d) forms as IPv4."""
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return ip.ipv4_mapped
        if ip in _NAT64:
            return ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)
    return ip


def is_blocked_address(value: str) -> bool:
    """True when an address is in any range the server may not connect to."""
    try:
        ip = _unwrap(ipaddress.ip_address(value.split("%", 1)[0]))
    except ValueError:
        # Not an address at all: refuse rather than guess.
        return True
    if ip.is_loopback or ip.is_link_local or ip.is_private or ip.is_unspecified:
        return True
    if ip.is_multicast or ip.is_reserved:
        return True
    return any(ip in net for net in _BLOCKED_NETWORKS if net.version == ip.version)


def default_resolver(host: str, port: int) -> list:
    """Resolve ``host`` once and return the distinct addresses, in order."""
    infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    seen: list = []
    for info in infos:
        address = info[4][0]
        if address not in seen:
            seen.append(address)
    return seen


def validate_outbound_url(
    url: str,
    *,
    resolver: Resolver | None = None,
) -> ValidatedTarget:
    """Validate ``url`` and pin it to one address, or raise :class:`UnsafeURLError`."""
    if not isinstance(url, str) or not url.strip():
        raise UnsafeURLError("no URL was given")
    url = url.strip()
    parts = urlsplit(url)
    scheme = (parts.scheme or "").lower()
    if scheme != "https":
        raise UnsafeURLError("only https URLs may be fetched")
    if parts.username is not None or parts.password is not None:
        raise UnsafeURLError("URLs with embedded credentials are refused")
    host = (parts.hostname or "").strip().lower().rstrip(".")
    if not host:
        raise UnsafeURLError("the URL has no host")
    try:
        port = parts.port or 443
    except ValueError:
        raise UnsafeURLError("the URL has an invalid port") from None
    if host == "localhost" or host.endswith(".localhost"):
        raise UnsafeURLError("the destination is blocked: localhost")

    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"

    # An address literal is checked directly; no resolution takes place.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if is_blocked_address(str(literal)):
            raise UnsafeURLError("the destination is blocked")
        return ValidatedTarget(url, scheme, host, port, str(literal), path)

    resolve = resolver or default_resolver
    try:
        answers = list(resolve(host, port))
    except UnsafeURLError:
        raise
    except Exception:  # noqa: BLE001
        raise UnsafeURLError("the host name could not be resolved") from None
    if not answers:
        raise UnsafeURLError("the host name could not be resolved")
    # Fail closed: one blocked answer refuses the whole name.
    if any(is_blocked_address(str(a)) for a in answers):
        raise UnsafeURLError("the destination is blocked")
    return ValidatedTarget(url, scheme, host, port, str(answers[0]), path)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connects to a validated address, verifying TLS against the real name."""

    def __init__(self, host: str, ip: str, port: int, timeout: float, context: ssl.SSLContext):
        super().__init__(host, port=port, timeout=timeout, context=context)
        self._pinned_ip = ip
        self._ssl_context = context

    def connect(self) -> None:
        sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        self.sock = self._ssl_context.wrap_socket(sock, server_hostname=self.host)


def _https_transport(
    target: ValidatedTarget,
    method: str,
    headers: Mapping[str, str],
    body: bytes | None,
    timeout: float,
) -> OutboundResponse:
    context = ssl.create_default_context()
    conn = _PinnedHTTPSConnection(target.host, target.ip, target.port, timeout, context)
    try:
        send = {"Host": target.host_header, "User-Agent": "karmathy-outbound/1"}
        send.update(headers)
        conn.request(method, target.path, body=body, headers=send)
        resp = conn.getresponse()
        data = resp.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise UnsafeURLError("the response is larger than the permitted size")
        return OutboundResponse(
            status=resp.status,
            headers={k.lower(): v for k, v in resp.getheaders()},
            body=data,
        )
    finally:
        conn.close()


def fetch(
    url: str,
    *,
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    body: bytes | None = None,
    timeout: float = 10,
    max_redirects: int = MAX_REDIRECTS,
    resolver: Resolver | None = None,
    transport: Transport | None = None,
) -> OutboundResponse:
    """Make an outbound request that passes the guard. Every hop is validated.

    Returns the final response, including 4xx and 5xx. Raises
    :class:`UnsafeURLError` for a refused URL or too many redirects.
    """
    send = transport or _https_transport
    current = url
    current_method = method.upper()
    current_body = body
    current_headers = dict(headers or {})
    origin_host = None
    for hop in range(max_redirects + 1):
        target = validate_outbound_url(current, resolver=resolver)
        if origin_host is None:
            origin_host = target.host
        elif target.host != origin_host:
            # Credentials for the original host are not sent to another host.
            current_headers.pop("Authorization", None)
        response = send(target, current_method, current_headers, current_body, timeout)
        if response.status not in REDIRECT_STATUSES:
            return response
        location = response.headers.get("location")
        if not location:
            return response
        if hop == max_redirects:
            raise UnsafeURLError("too many redirects")
        current = urljoin(current, location)
        if response.status == 303 or (response.status in (301, 302) and current_method == "POST"):
            current_method = "GET"
            current_body = None
    raise UnsafeURLError("too many redirects")
