"""
Unit tests for security manager.
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import jwt

from open_logistics.core.security import SecurityManager
from open_logistics.core.config import get_settings


class TestSecurityManager:
    """Tests for the SecurityManager class."""

    def setup_method(self):
        """Setup test fixtures."""
        self.security_manager = SecurityManager()

    def test_encryption_decryption(self):
        """Test basic encryption and decryption."""
        test_data = "test_data"
        encrypted = self.security_manager.encrypt(test_data)
        decrypted = self.security_manager.decrypt(encrypted)
        assert decrypted == test_data

    def test_encrypt_decrypt_string(self):
        """Test string encryption and decryption."""
        test_string = "Sensitive military data"
        encrypted = self.security_manager.encrypt_string(test_string)
        decrypted = self.security_manager.decrypt_string(encrypted)
        assert decrypted == test_string
        assert encrypted != test_string

    def test_encrypt_decrypt_data_bytes(self):
        """Test byte data encryption and decryption."""
        test_data = b"Binary sensitive data"
        encrypted = self.security_manager.encrypt_data(test_data)
        decrypted = self.security_manager.decrypt_data(encrypted)
        assert decrypted == test_data
        assert encrypted != test_data

    def test_generate_jwt_token(self):
        """Test JWT token generation."""
        user_id = "test_user"
        role = "admin"
        token = self.security_manager.generate_jwt_token(user_id, role)
        
        # Verify token structure
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify payload
        decoded = jwt.decode(token, self.security_manager._jwt_secret, algorithms=["HS256"])
        assert decoded["user_id"] == user_id
        assert decoded["role"] == role
        assert decoded["iss"] == "open_logistics"
        assert "permissions" in decoded
        assert "exp" in decoded

    def test_generate_jwt_token_custom_expiry(self):
        """Test JWT token generation with custom expiry."""
        user_id = "test_user"
        role = "operator"
        expires_in = 12
        token = self.security_manager.generate_jwt_token(user_id, role, expires_in)
        
        decoded = jwt.decode(token, self.security_manager._jwt_secret, algorithms=["HS256"])
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(decoded["iat"], tz=timezone.utc)
        
        # Check expiry is approximately 12 hours from issued time
        time_diff = exp_time - iat_time
        assert abs(time_diff.total_seconds() - (expires_in * 3600)) < 60  # Within 1 minute

    def test_validate_jwt_token_valid(self):
        """Test JWT token validation with valid token."""
        user_id = "test_user"
        role = "admin"
        token = self.security_manager.generate_jwt_token(user_id, role)
        
        payload = self.security_manager.validate_jwt_token(token)
        
        assert payload is not None
        assert payload["user_id"] == user_id
        assert payload["role"] == role

    def test_validate_jwt_token_invalid(self):
        """Test JWT token validation with invalid token."""
        invalid_token = "invalid.token.here"
        payload = self.security_manager.validate_jwt_token(invalid_token)
        assert payload is None

    def test_validate_jwt_token_expired(self):
        """Test JWT token validation with expired token."""
        # Create an expired token
        expired_payload = {
            "user_id": "test_user",
            "role": "admin",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "iss": "open_logistics"
        }
        
        expired_token = jwt.encode(expired_payload, self.security_manager._jwt_secret, algorithm="HS256")
        payload = self.security_manager.validate_jwt_token(expired_token)
        assert payload is None

    def test_check_permission_admin(self):
        """Test permission check for admin role."""
        assert self.security_manager.check_permission("admin", "read") is True
        assert self.security_manager.check_permission("admin", "write") is True
        assert self.security_manager.check_permission("admin", "delete") is True
        assert self.security_manager.check_permission("admin", "configure") is True
        assert self.security_manager.check_permission("admin", "audit") is True

    def test_check_permission_operator(self):
        """Test permission check for operator role."""
        assert self.security_manager.check_permission("operator", "read") is True
        assert self.security_manager.check_permission("operator", "write") is True
        assert self.security_manager.check_permission("operator", "configure") is True
        assert self.security_manager.check_permission("operator", "delete") is False
        assert self.security_manager.check_permission("operator", "audit") is False

    def test_check_permission_viewer(self):
        """Test permission check for viewer role."""
        assert self.security_manager.check_permission("viewer", "read") is True
        assert self.security_manager.check_permission("viewer", "write") is False
        assert self.security_manager.check_permission("viewer", "delete") is False
        assert self.security_manager.check_permission("viewer", "configure") is False

    def test_check_permission_invalid_role(self):
        """Test permission check for invalid role."""
        assert self.security_manager.check_permission("invalid_role", "read") is False

    def test_check_classification_access_admin(self):
        """Test classification access for admin role."""
        assert self.security_manager.check_classification_access("admin", "UNCLASSIFIED") is True
        assert self.security_manager.check_classification_access("admin", "CONFIDENTIAL") is True
        assert self.security_manager.check_classification_access("admin", "SECRET") is True
        assert self.security_manager.check_classification_access("admin", "TOP_SECRET") is True

    def test_check_classification_access_operator(self):
        """Test classification access for operator role."""
        assert self.security_manager.check_classification_access("operator", "UNCLASSIFIED") is True
        assert self.security_manager.check_classification_access("operator", "CONFIDENTIAL") is True
        assert self.security_manager.check_classification_access("operator", "SECRET") is False
        assert self.security_manager.check_classification_access("operator", "TOP_SECRET") is False

    def test_check_classification_access_viewer(self):
        """Test classification access for viewer role."""
        assert self.security_manager.check_classification_access("viewer", "UNCLASSIFIED") is True
        assert self.security_manager.check_classification_access("viewer", "CONFIDENTIAL") is False
        assert self.security_manager.check_classification_access("viewer", "SECRET") is False

    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = self.security_manager.hash_password(password)
        
        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = self.security_manager.hash_password(password)
        
        assert self.security_manager.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = self.security_manager.hash_password(password)
        
        assert self.security_manager.verify_password(wrong_password, hashed) is False

    def test_verify_password_invalid_hash(self):
        """Test password verification with invalid hash."""
        password = "test_password_123"
        invalid_hash = "invalid_hash"
        
        assert self.security_manager.verify_password(password, invalid_hash) is False

    def test_generate_api_key(self):
        """Test API key generation."""
        user_id = "test_user"
        description = "Test API key"
        
        api_key = self.security_manager.generate_api_key(user_id, description)
        
        assert isinstance(api_key, str)
        assert api_key.startswith("ol_")
        assert len(api_key) > 10

    def test_generate_api_key_no_description(self):
        """Test API key generation without description."""
        user_id = "test_user"
        
        api_key = self.security_manager.generate_api_key(user_id)
        
        assert isinstance(api_key, str)
        assert api_key.startswith("ol_")

    def test_get_security_audit_log(self):
        """Test security audit log retrieval."""
        # Generate some security events
        self.security_manager.encrypt_string("test")
        self.security_manager.generate_jwt_token("user", "admin")
        
        audit_log = self.security_manager.get_security_audit_log()
        
        assert isinstance(audit_log, list)
        assert len(audit_log) >= 2  # At least 2 events generated above

    def test_get_security_audit_log_with_limit(self):
        """Test security audit log retrieval with limit."""
        # Generate multiple security events
        for i in range(5):
            self.security_manager.encrypt_string(f"test_{i}")
        
        audit_log = self.security_manager.get_security_audit_log(limit=3)
        
        assert isinstance(audit_log, list)
        assert len(audit_log) <= 3

    def test_encryption_failure_handling(self):
        """Test encryption failure handling."""
        with patch.object(self.security_manager._fernet, 'encrypt') as mock_encrypt:
            mock_encrypt.side_effect = Exception("Encryption failed")
            
            with pytest.raises(Exception):
                self.security_manager.encrypt_data(b"test")

    def test_decryption_failure_handling(self):
        """Test decryption failure handling."""
        with patch.object(self.security_manager._fernet, 'decrypt') as mock_decrypt:
            mock_decrypt.side_effect = Exception("Decryption failed")
            
            with pytest.raises(Exception):
                self.security_manager.decrypt_data(b"invalid_encrypted_data")

    def test_jwt_generation_failure_handling(self):
        """Test JWT generation failure handling."""
        with patch('jwt.encode') as mock_encode:
            mock_encode.side_effect = Exception("JWT encoding failed")
            
            with pytest.raises(Exception):
                self.security_manager.generate_jwt_token("user", "admin")

    def test_audit_log_memory_management(self):
        """Test audit log memory management (keeps only last 1000 entries)."""
        # Fill audit log beyond 1000 entries
        original_log = self.security_manager._audit_log
        
        # Simulate 1500 entries
        for i in range(1500):
            self.security_manager._audit_log.append({"test": f"entry_{i}"})
        
        # Trigger the cleanup by logging a new event
        self.security_manager._log_security_event("test_event", {"test": "data"})
        
        # Should keep only last 1000 entries
        assert len(self.security_manager._audit_log) <= 1001  # 1000 + 1 new entry

    @patch('loguru.logger.info')
    def test_security_event_logging(self, mock_logger):
        """Test that security events are logged to file."""
        self.security_manager._log_security_event("test_event", {"key": "value"})
        
        mock_logger.assert_called_once()
        call_args = mock_logger.call_args
        assert "Security event: test_event" in call_args[0][0] 