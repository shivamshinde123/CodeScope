"""Tests for authentication service."""

from examples.services.auth_service import generate_token, verify_token
from examples.models.user import User


class TestAuthService:
    def setup_method(self):
        User._store.clear()

    def test_generate_and_verify_token(self):
        user = User(email="test@example.com", name="Test User")
        user.save()
        token = generate_token(user)
        verified_user = verify_token(token)
        assert verified_user is not None
        assert verified_user.id == user.id

    def test_verify_invalid_token(self):
        assert verify_token("invalid:token:here") is None

    def test_verify_malformed_token(self):
        assert verify_token("completely-wrong") is None
