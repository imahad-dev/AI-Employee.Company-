from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken


class VaultError(ValueError):
    pass


def _fernet(master_key: str) -> Fernet:
    if len(master_key.strip()) < 16:
        raise VaultError("SECRET_VAULT_KEY must be at least 16 characters for encrypted secret storage.")
    digest = hashlib.sha256(master_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str, master_key: str) -> str:
    return _fernet(master_key).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(payload: str, master_key: str) -> str:
    try:
        return _fernet(master_key).decrypt(payload.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise VaultError("Encrypted secret integrity check failed.") from exc
