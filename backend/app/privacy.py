import hashlib
from typing import Any


ACCOUNT_NUMBER_KEYS = {
    "acctNo",
    "acct_no",
    "account_no",
    "acnt_no",
    "acntNo",
    "accno",
    "계좌번호",
}


def mask_account(account_no: str) -> str:
    digits = "".join(ch for ch in str(account_no) if ch.isdigit())
    if len(digits) <= 4:
        return "****"
    return f"{digits[:4]}****{digits[-2:]}"


def hash_account(account_no: str, salt: str) -> str:
    normalized = "".join(ch for ch in str(account_no) if ch.isdigit())
    return hashlib.sha256(f"{salt}{normalized}".encode("utf-8")).hexdigest()[:16]


def account_ref(account_no: str, salt: str) -> dict:
    return {
        "account_hash": hash_account(account_no, salt),
        "masked_account": mask_account(account_no),
    }


def is_likely_account_number(value: str) -> bool:
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return len(digits) >= 8


def account_label_for_storage(value: str, salt: str) -> tuple[str, str | None]:
    if not is_likely_account_number(value):
        return (value.strip() or "기타", None)
    return mask_account(value), hash_account(value, salt)


def redact_account_numbers(value: Any, salt: str) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            if key in ACCOUNT_NUMBER_KEYS and item:
                redacted[f"{key}_hash"] = hash_account(str(item), salt)
                redacted[f"{key}_masked"] = mask_account(str(item))
                continue
            redacted[key] = redact_account_numbers(item, salt)
        return redacted
    if isinstance(value, list):
        return [redact_account_numbers(item, salt) for item in value]
    return value
