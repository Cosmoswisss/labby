import datetime as dt
import ssl

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509.oid import AuthorityInformationAccessOID, NameOID

from pipeline import tls
from pipeline.fetch import Fetcher, RateLimiter


def make_cert(subject, issuer_name, issuer_key, key, ca, aia_url=None):
    now = dt.datetime.now(dt.UTC)
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject)]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer_name)]))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
    )
    if aia_url:
        builder = builder.add_extension(
            x509.AuthorityInformationAccess(
                [
                    x509.AccessDescription(
                        AuthorityInformationAccessOID.CA_ISSUERS,
                        x509.UniformResourceIdentifier(aia_url),
                    )
                ]
            ),
            critical=False,
        )
    return builder.sign(issuer_key, hashes.SHA256())


def chain():
    root_key, int_key, leaf_key = (ec.generate_private_key(ec.SECP256R1()) for _ in range(3))
    root = make_cert("Test Root", "Test Root", root_key, root_key, ca=True)
    intermediate = make_cert(
        "Test Intermediate", "Test Root", root_key, int_key, ca=True,
        aia_url="http://ca.test/root.der",
    )  # fmt: skip
    leaf = make_cert(
        "lts2.test", "Test Intermediate", int_key, leaf_key, ca=False,
        aia_url="http://ca.test/intermediate.der",
    )  # fmt: skip
    return root, intermediate, leaf


def test_ca_issuer_urls():
    _, intermediate, leaf = chain()
    assert tls.ca_issuer_urls(leaf) == ["http://ca.test/intermediate.der"]
    assert tls.ca_issuer_urls(intermediate) == ["http://ca.test/root.der"]


def test_fetch_intermediates_stops_at_the_root():
    root, intermediate, leaf = chain()
    served = {
        "http://ca.test/intermediate.der": intermediate.public_bytes(Encoding.DER),
        "http://ca.test/root.der": root.public_bytes(Encoding.DER),
    }
    got = tls.fetch_intermediates(leaf, get=served.__getitem__)
    # the intermediate is collected; the self-signed root is never trusted from the network
    assert got == [intermediate]


def test_parse_pem_and_der():
    _, intermediate, _ = chain()
    assert tls.parse_certificates(intermediate.public_bytes(Encoding.PEM)) == [intermediate]
    assert tls.parse_certificates(intermediate.public_bytes(Encoding.DER)) == [intermediate]
    assert tls.parse_certificates(b"not a certificate") == []


def test_context_keeps_full_verification():
    _, intermediate, _ = chain()
    ctx = tls.context_with_intermediates([intermediate])
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    subjects = [dict(x[0] for x in c["subject"]).get("commonName") for c in ctx.get_ca_certs()]
    assert "Test Intermediate" in subjects


def test_missing_issuer_error_detection():
    err = httpx.ConnectError(
        "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local "
        "issuer certificate (_ssl.c:1011)"
    )
    assert tls.is_missing_issuer_error(err)
    assert not tls.is_missing_issuer_error(httpx.ConnectError("getaddrinfo failed"))


def test_fetcher_retries_with_completed_chain(tmp_path, web):
    def broken(request):
        raise httpx.ConnectError(
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local "
            "issuer certificate",
            request=request,
        )

    fixed_web = httpx.MockTransport(
        lambda r: httpx.Response(
            200, content=b"<html>ok</html>", headers={"content-type": "text/html"}
        )
    )
    calls = {"fixer": 0}

    def fixer(host):
        calls["fixer"] += 1
        assert host == "lts2.test"
        return ssl.create_default_context()

    web.routes["https://lts2.test/projects/list"] = broken
    fetcher = Fetcher(
        tmp_path / "cache",
        client=httpx.Client(transport=httpx.MockTransport(web.handler)),
        rate_limiter=RateLimiter(0.0),
        sleep=lambda _s: None,
        chain_fixer=fixer,
        client_factory=lambda ctx: httpx.Client(transport=fixed_web),
    )
    result = fetcher.fetch("https://lts2.test/projects/list")
    assert result.ok and result.body == b"<html>ok</html>"
    assert calls["fixer"] == 1
    # later requests to the same host go straight to the fixed client
    assert fetcher.fetch("https://lts2.test/projects/142").ok
    assert calls["fixer"] == 1
