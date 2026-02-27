# tests/test_api/test_authentication.py
import pytest
from fastapi import HTTPException

from app.core.security import generate_api_key, verify_secret, hashed_secret
from app.api.deps import get_project_id_from_api_key


class TestAPIKeyAuthentication:
    """Test API key generation and validation"""

    def test_generate_api_key_format(self):
        raw_key, prefix, hashed = generate_api_key()

        # raw_key format: prefix.secret
        assert "." in raw_key
        parts = raw_key.split(".")
        assert len(parts) == 2
        assert parts[0] == prefix

        # Prefix is hex, length 8 by default
        assert len(prefix) == 8
        assert all(c in "0123456789abcdef" for c in prefix)

        # bcrypt hash format (starts with $2a$ or $2b$ etc.)
        assert hashed.startswith("$2")
        assert len(hashed) >= 50

        # secret should verify against stored hash
        secret = parts[1]
        assert verify_secret(secret, hashed) is True

    def test_verify_secret_correct(self):
        raw_key, _, hashed = generate_api_key()
        secret = raw_key.split(".", 1)[1]
        assert verify_secret(secret, hashed) is True

    def test_verify_secret_incorrect(self):
        raw_key, _, hashed = generate_api_key()
        assert verify_secret("wrong-secret", hashed) is False

    def test_hashed_secret_is_not_deterministic_but_verifies(self):
        secret = "test-secret-123"
        hash1 = hashed_secret(secret)
        hash2 = hashed_secret(secret)

        # bcrypt uses salt => same input produces different hashes
        assert hash1 != hash2

        # but both hashes should validate
        assert verify_secret(secret, hash1) is True
        assert verify_secret(secret, hash2) is True

    def test_hashed_secret_different_for_different_inputs(self):
        h1 = hashed_secret("secret1")
        h2 = hashed_secret("secret2")
        assert h1 != h2
        assert verify_secret("secret1", h1) is True
        assert verify_secret("secret2", h2) is True


class TestAPIKeyDependency:
    """Test the FastAPI dependency that extracts project_id from X-API-Key"""

    def test_valid_api_key_returns_project_id(self, db_session, test_api_key):
        project_id = get_project_id_from_api_key(db=db_session, x_api_key=test_api_key.raw_key)
        assert project_id == test_api_key.project_id

    def test_missing_api_key_rejected(self, db_session):
        with pytest.raises(HTTPException) as exc:
            get_project_id_from_api_key(db=db_session, x_api_key=None)
        assert exc.value.status_code == 401

    def test_invalid_format_api_key_rejected(self, db_session):
        with pytest.raises(HTTPException) as exc:
            get_project_id_from_api_key(db=db_session, x_api_key="invalid-no-dot")
        assert exc.value.status_code == 403

    def test_unknown_prefix_rejected(self, db_session):
        with pytest.raises(HTTPException) as exc:
            get_project_id_from_api_key(db=db_session, x_api_key="unknown12.somesecret")
        assert exc.value.status_code == 403

    def test_wrong_secret_rejected(self, db_session, test_api_key):
        wrong_key = f"{test_api_key.prefix}.wrong-secret"
        with pytest.raises(HTTPException) as exc:
            get_project_id_from_api_key(db=db_session, x_api_key=wrong_key)
        assert exc.value.status_code == 403

    def test_revoked_api_key_rejected(self, db_session, test_api_key):
        from datetime import datetime, timezone

        test_api_key.revoked_at = datetime.now(timezone.utc)
        db_session.commit()

        with pytest.raises(HTTPException) as exc:
            get_project_id_from_api_key(db=db_session, x_api_key=test_api_key.raw_key)
        assert exc.value.status_code == 403
