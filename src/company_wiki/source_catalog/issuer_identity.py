"""Canonical issuer keys shared by registered originals and listing browse."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Any
from urllib.parse import urlsplit

from .models import RegisteredIssuerFacts
from .security_code import canonical_security_code
from .security_identity import normalize_identity_text


ISSUER_NAMESPACE_HK_LISTING = "hkex.listed-issuer"
ISSUER_VERIFIER_HK_SOURCE_FACTS = "hkex-registered-source-facts/1"
ISSUER_NAMESPACE_SEC_CIK = "sec.cik"
ISSUER_VERIFIER_SEC_DEI = "sec-primary-dei/1"


@dataclass(frozen=True)
class IssuerKey:
    """One exact issuer key in a supported namespace."""

    namespace: str
    value: str

    def qualified(self) -> str:
        return self.namespace + ":" + self.value


def hk_issuer_key(ticker: Any, issuer_name: Any) -> IssuerKey | None:
    code = canonical_security_code(ticker, "HK")
    if not isinstance(code, str) or not re.fullmatch(r"[0-9]{5}", code) or not isinstance(issuer_name, str):
        return None
    name = normalize_identity_text(issuer_name)
    if not name:
        return None
    # The issuer name guards against historic ticker reassignment.
    return IssuerKey(ISSUER_NAMESPACE_HK_LISTING, f"{code}:{hashlib.sha256(name.encode()).hexdigest()}")


def official_hk_source_issuer(facts: RegisteredIssuerFacts | None) -> IssuerKey | None:
    if facts is None or facts.market != "HK" or facts.provider != "hkexnews":
        return None
    try:
        location = urlsplit(facts.source_url)
        official = (
            location.scheme == "https"
            and location.hostname in {"www.hkexnews.hk", "www1.hkexnews.hk"}
            and location.username is None
            and location.password is None
            and location.port in {None, 443}
        )
    except ValueError:
        return None
    return hk_issuer_key(facts.security_id, facts.entity) if official else None
