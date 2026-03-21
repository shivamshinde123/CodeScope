"""Tests for input validation utilities."""

import pytest
from examples.utils.validators import validate_email, validate_project_name, validate_password


class TestValidateEmail:
    def test_valid_email(self):
        assert validate_email("user@example.com") is True

    def test_valid_email_with_dots(self):
        assert validate_email("first.last@company.co.uk") is True

    def test_invalid_no_at(self):
        assert validate_email("userexample.com") is False

    def test_invalid_empty(self):
        assert validate_email("") is False

    def test_invalid_too_long(self):
        assert validate_email("a" * 250 + "@b.com") is False


class TestValidateProjectName:
    def test_valid_name(self):
        assert validate_project_name("my-project-123") is True

    def test_invalid_starts_with_hyphen(self):
        assert validate_project_name("-bad-name") is False

    def test_invalid_empty(self):
        assert validate_project_name("") is False

    def test_invalid_special_chars(self):
        assert validate_project_name("project@name!") is False


class TestValidatePassword:
    def test_valid_password(self):
        is_valid, msg = validate_password("MyP@ss1234")
        assert is_valid is True

    def test_too_short(self):
        is_valid, msg = validate_password("Ab1")
        assert is_valid is False
        assert "8 characters" in msg

    def test_no_uppercase(self):
        is_valid, msg = validate_password("lowercase123")
        assert is_valid is False

    def test_no_digit(self):
        is_valid, msg = validate_password("NoDigitsHere")
        assert is_valid is False
