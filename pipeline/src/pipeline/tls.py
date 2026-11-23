"""Complete incomplete TLS certificate chains (missing intermediate certificates).

Some sites send only their own certificate, not the intermediate that links it to a
trusted root. Browsers and Windows fetch the missing intermediate from the URL written
in the certificate (Authority Information Access, "CA Issuers"); OpenSSL on Linux does
not, so such sites fail with "unable to get local issuer certificate".

This module does what browsers do: read the site's certificate, download its issuer
chain via AIA, and return an SSL context that trusts the system roots *plus* those
intermediates. Verification is never disabled: the final connection is fully verified
against a root of the system store.
"""

from __future__ import annotations

import socket
import ssl

import httpx
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding, pkcs7
from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID

MAX_DEPTH = 3


def is_missing_issuer_error(exc: BaseException) -> bool:
    text = str(exc)
    return "CERTIFICATE_VERIFY_FAILED" in text and "unable to get local issuer" in text


def leaf_certificate(host: str, port: int = 443, timeout: float = 15.0) -> x509.Certificate:
    """The server's own certificate (read during the handshake, no data exchanged)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # only to *read* the certificate; never used to fetch
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            der = tls.getpeercert(binary_form=True)
    return x509.load_der_x509_certificate(der)


def ca_issuer_urls(cert: x509.Certificate) -> list[str]:
    try:
        aia = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS)
    except x509.ExtensionNotFound:
        return []
    return [
        d.access_location.value
        for d in aia.value
        if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS
        and isinstance(d.access_location, x509.UniformResourceIdentifier)
    ]


def parse_certificates(data: bytes) -> list[x509.Certificate]:
    """Certificates served at an AIA URL: DER, PEM or PKCS#7 bundle."""
    for loader in (
        lambda d: [x509.load_der_x509_certificate(d)],
        lambda d: x509.load_pem_x509_certificates(d),
        lambda d: pkcs7.load_der_pkcs7_certificates(d),
        lambda d: pkcs7.load_pem_pkcs7_certificates(d),
    ):
        try:
            certs = loader(data)
            if certs:
                return certs
        except ValueError:
            continue
    return []


def is_self_signed(cert: x509.Certificate) -> bool:
    return cert.issuer == cert.subject


def fetch_intermediates(
    leaf: x509.Certificate, get=lambda url: httpx.get(url, timeout=15.0).content
) -> list[x509.Certificate]:
    """Follows AIA "CA Issuers" links from the leaf up to MAX_DEPTH certificates."""
    chain: list[x509.Certificate] = []
    current = leaf
    for _ in range(MAX_DEPTH):
        urls = [u for u in ca_issuer_urls(current) if u.startswith(("http://", "https://"))]
        if not urls:
            break
        certs = parse_certificates(get(urls[0]))
        if not certs:
            break
        issuer = certs[0]
        if is_self_signed(issuer):
            break  # a root: it must come from the system store, never from the network
        chain.append(issuer)
        current = issuer
    return chain


def context_with_intermediates(intermediates: list[x509.Certificate]) -> ssl.SSLContext:
    """System trust store + the given intermediates; hostname and chain fully verified."""
    ctx = ssl.create_default_context()
    pem = "".join(c.public_bytes(Encoding.PEM).decode() for c in intermediates)
    if pem:
        ctx.load_verify_locations(cadata=pem)
    return ctx


def completed_chain_context(host: str, port: int = 443) -> ssl.SSLContext | None:
    """An SSL context able to verify `host` despite a missing intermediate, or None."""
    try:
        intermediates = fetch_intermediates(leaf_certificate(host, port))
    except (OSError, ssl.SSLError, httpx.HTTPError, ValueError):
        return None
    return context_with_intermediates(intermediates) if intermediates else None
