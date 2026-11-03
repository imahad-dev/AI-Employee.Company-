import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.vault import VaultError, decrypt_secret, encrypt_secret
from app.db.sqlite import SQLiteStore


class VaultTests(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        key = "test-secret-key-with-enough-length"
        encrypted = encrypt_secret("secret-value", key)
        self.assertNotIn("secret-value", encrypted)
        self.assertEqual(decrypt_secret(encrypted, key), "secret-value")

    def test_wrong_key_fails_integrity_check(self):
        encrypted = encrypt_secret("secret-value", "test-secret-key-with-enough-length")
        with self.assertRaises(VaultError):
            decrypt_secret(encrypted, "different-secret-key-with-enough-length")

    def test_sqlite_store_secret_status(self):
        store = SQLiteStore(Path.cwd() / ".testdata" / "vault-test.db", "test-secret-key-with-enough-length")
        store.set_secret("proj_secret", "provider_api_key", "abc123")
        self.assertTrue(store.has_secret("proj_secret", "provider_api_key"))
        self.assertEqual(store.get_secret("proj_secret", "provider_api_key"), "abc123")
        status = store.secret_status("proj_secret")
        self.assertTrue(status["provider_api_key"])
        self.assertFalse(status["github_token"])


if __name__ == "__main__":
    unittest.main()
