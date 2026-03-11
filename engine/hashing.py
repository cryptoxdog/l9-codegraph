"""
PII hashing utilities for Google Enhanced Conversions and Customer Match.
All hashing follows Google's normalization spec exactly.
"""
import hashlib
import re
from typing import Optional


def sha256_hash(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_and_hash_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    email = email.strip().lower()
    if "@" not in email:
        return None
    local, domain = email.rsplit("@", 1)
    if domain in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")
        plus_idx = local.find("+")
        if plus_idx != -1:
            local = local[:plus_idx]
    normalized = f"{local}@{domain}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def normalize_phone_e164(phone: Optional[str], default_country: str = "US") -> Optional[str]:
    if not phone:
        return None
    digits = re.sub(r"[^\d+]", "", phone)
    if not digits:
        return None
    if digits.startswith("+"):
        return digits if len(digits) >= 8 else None
    if default_country == "US":
        digits_only = digits.lstrip("+")
        if len(digits_only) == 10:
            return f"+1{digits_only}"
        elif len(digits_only) == 11 and digits_only.startswith("1"):
            return f"+{digits_only}"
    return None


def hash_phone(phone: Optional[str], default_country: str = "US") -> Optional[str]:
    normalized = normalize_phone_e164(phone, default_country)
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def hash_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    cleaned = re.sub(r"[^a-z\s]", "", name.strip().lower())
    cleaned = " ".join(cleaned.split())
    if not cleaned:
        return None
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def normalize_state(state: Optional[str]) -> Optional[str]:
    if not state:
        return None
    cleaned = state.strip().upper()
    STATE_MAP = {
        "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
        "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
        "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
        "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
        "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
        "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
        "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
        "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
        "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
        "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
        "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
        "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
        "WISCONSIN": "WI", "WYOMING": "WY", "DISTRICT OF COLUMBIA": "DC",
    }
    if len(cleaned) == 2 and cleaned in STATE_MAP.values():
        return cleaned
    return STATE_MAP.get(cleaned)


def normalize_postal_code(postal_code: Optional[str], country: str = "US") -> Optional[str]:
    if not postal_code:
        return None
    cleaned = re.sub(r"[^\d]", "", postal_code.strip())
    if country == "US":
        if len(cleaned) >= 9:
            return cleaned[:9]
        elif len(cleaned) >= 5:
            return cleaned[:5]
    return cleaned if cleaned else None


def normalize_country_code(country: Optional[str]) -> Optional[str]:
    if not country:
        return None
    cleaned = country.strip().upper()
    COUNTRY_MAP = {
        "UNITED STATES": "US", "USA": "US", "U.S.A.": "US", "U.S.": "US",
        "CANADA": "CA", "MEXICO": "MX", "UNITED KINGDOM": "GB", "UK": "GB",
    }
    if len(cleaned) == 2:
        return cleaned
    return COUNTRY_MAP.get(cleaned)
