import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.db import Base
from models.user import User
from services.email import send_email, render_template, send_templated_email, _send_email_direct
from services.otp import (
    _generate_code, send_verification_code, verify_code, verify_code_without_email,
    get_otp_status, _FakeRedis, redis_client, OTP_PREFIX, OTP_CODE_PREFIX,
    OTP_LAST_SENT_PREFIX, OTP_EXPIRY
)


@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user"""
    user = User(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        password_hash="hashed_password",
        is_verified=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def fake_redis():
    """Create a fake Redis instance for testing"""
    return _FakeRedis()


@pytest.fixture(autouse=True)
def clear_redis():
    """Clear Redis before each test"""
    # Clear all test keys
    for key in list(redis_client._store.keys()) if hasattr(redis_client, '_store') else []:
        redis_client.delete(key)


class TestEmailService:
    """Test cases for email service"""
    
    def test_render_template_success(self):
        """Test successful template rendering"""
        context = {"code": "123456", "first_name": "John"}
        result = render_template("emails/verification_code.txt", context)
        
        assert "123456" in result
        # Template only contains code, not first_name
    
    def test_render_template_with_missing_context(self):
        """Test template rendering with missing context variables"""
        context = {"code": "123456"}  # Missing first_name
        result = render_template("emails/verification_code.txt", context)
        
        assert "123456" in result
        # Should not crash, template handles missing variables
    
    def test_render_template_not_found(self):
        """Test template rendering with non-existent template"""
        with pytest.raises(Exception):  # Should raise TemplateNotFound
            render_template("non_existent.txt", {})
    
    @patch('services.email.USE_CELERY', True)
    @patch('services.email.send_email_task')
    def test_send_email_with_celery_success(self, mock_task):
        """Test sending email with Celery available"""
        mock_task.delay = Mock()
        
        send_email("test@example.com", "Test Subject", "Test Body")
        
        mock_task.delay.assert_called_once_with("test@example.com", "Test Subject", "Test Body")
    
    @patch('services.email.USE_CELERY', True)
    @patch('services.email.send_email_task')
    @patch('services.email.settings')
    def test_send_email_with_celery_fallback(self, mock_settings, mock_task):
        """Test falling back to direct email when Celery fails"""
        mock_task.delay.side_effect = Exception("Celery not available")
        mock_settings.DEBUG = True
        
        with patch('services.email._send_email_direct') as mock_direct:
            send_email("test@example.com", "Test Subject", "Test Body")
            mock_direct.assert_called_once_with("test@example.com", "Test Subject", "Test Body")
    
    @patch('services.email.USE_CELERY', False)
    @patch('services.email._send_email_direct')
    def test_send_email_without_celery(self, mock_direct):
        """Test sending email without Celery"""
        send_email("test@example.com", "Test Subject", "Test Body")
        
        mock_direct.assert_called_once_with("test@example.com", "Test Subject", "Test Body")
    
    @patch('services.email.settings')
    @patch('smtplib.SMTP')
    def test_send_email_direct_placeholder_credentials(self, mock_smtp, mock_settings):
        """Test direct email sending with placeholder credentials"""
        mock_settings.SMTP_PASSWORD = "your-gmail-app-password"
        
        with patch('builtins.print') as mock_print:
            _send_email_direct("test@example.com", "Test Subject", "Test Body")
            
            # Should print debug messages instead of sending
            assert any("DEBUG: Email would be sent" in str(call) for call in mock_print.call_args_list)
            mock_smtp.assert_not_called()
    
    @patch('services.email.settings')
    @patch('smtplib.SMTP')
    def test_send_email_direct_real_credentials(self, mock_smtp, mock_settings):
        """Test direct email sending with real credentials"""
        mock_settings.SMTP_PASSWORD = "real_password"
        mock_settings.SMTP_HOST = "smtp.gmail.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USERNAME = "test@gmail.com"
        mock_settings.SMTP_FROM = None
        
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        _send_email_direct("test@example.com", "Test Subject", "Test Body")
        
        # Should attempt to send email
        mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@gmail.com", "real_password")
        mock_server.send_message.assert_called_once()
    
    @patch('services.email.settings')
    @patch('smtplib.SMTP')
    def test_send_email_direct_failure_debug(self, mock_smtp, mock_settings):
        """Test direct email sending failure in debug mode"""
        mock_settings.SMTP_PASSWORD = "real_password"
        mock_settings.DEBUG = True
        mock_smtp.side_effect = Exception("SMTP connection failed")
        
        with patch('builtins.print') as mock_print:
            _send_email_direct("test@example.com", "Test Subject", "Test Body")
            
            # Should print error message
            assert any("Failed to send email" in str(call) for call in mock_print.call_args_list)
    
    @patch('services.email.settings')
    @patch('smtplib.SMTP')
    def test_send_email_direct_failure_production(self, mock_smtp, mock_settings):
        """Test direct email sending failure in production"""
        mock_settings.SMTP_PASSWORD = "real_password"
        mock_settings.DEBUG = False
        mock_smtp.side_effect = Exception("SMTP connection failed")
        
        with patch('builtins.print') as mock_print:
            _send_email_direct("test@example.com", "Test Subject", "Test Body")
            
            # Should print generic error message
            assert any("Email sending failed" in str(call) for call in mock_print.call_args_list)
    
    @patch('services.email.send_email')
    @patch('services.email.render_template')
    def test_send_templated_email(self, mock_render, mock_send):
        """Test sending templated email"""
        mock_render.return_value = "Rendered content"
        
        send_templated_email("test@example.com", "Test Subject", "template.txt", {"key": "value"})
        
        mock_render.assert_called_once_with("template.txt", {"key": "value"})
        mock_send.assert_called_once_with("test@example.com", "Test Subject", "Rendered content")


class TestOTPService:
    """Test cases for OTP service"""
    
    def test_generate_code(self):
        """Test OTP code generation"""
        code = _generate_code()
        
        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()
        
        # Test multiple generations
        codes = [_generate_code() for _ in range(100)]
        assert len(set(codes)) > 50  # Should be mostly unique
    
    @patch('services.otp.settings')
    def test_send_verification_code_success(self, mock_settings, test_user, fake_redis):
        """Test successful OTP generation and sending"""
        mock_settings.OTP_RESEND_INTERVAL_SECONDS = 60
        mock_settings.OTP_TTL_SECONDS = 600
        
        with patch('services.otp.redis_client', fake_redis):
            with patch('services.otp.send_templated_email') as mock_email:
                code = send_verification_code(None, test_user)  # Pass None for db_session
                
                assert isinstance(code, str)
                assert len(code) == 6
                assert code.isdigit()
                
                # Check Redis storage
                otp_key = f"{OTP_PREFIX}{test_user.email}"
                otp_data_str = fake_redis.get(otp_key)
                assert otp_data_str is not None
                
                otp_data = json.loads(otp_data_str)
                assert otp_data["code"] == code
                assert otp_data["user_id"] == test_user.id
                assert otp_data["email"] == test_user.email
                assert otp_data["attempts"] == 0
                
                # Check code mapping
                code_key = f"{OTP_CODE_PREFIX}{code}"
                assert fake_redis.get(code_key) == test_user.email
                
                # Check rate limiter
                last_key = f"{OTP_LAST_SENT_PREFIX}{test_user.email}"
                assert fake_redis.exists(last_key) == 1
                
                # Check email was sent
                mock_email.assert_called_once()
    
    @patch('services.otp.settings')
    def test_send_verification_code_rate_limit(self, mock_settings, test_user, fake_redis):
        """Test OTP rate limiting"""
        mock_settings.OTP_RESEND_INTERVAL_SECONDS = 60
        mock_settings.OTP_TTL_SECONDS = 600
        
        with patch('services.otp.redis_client', fake_redis):
            with patch('services.otp.send_templated_email'):
                # Send first OTP
                send_verification_code(None, test_user)
                
                # Try to send second OTP immediately
                with pytest.raises(ValueError, match="Please wait"):
                    send_verification_code(None, test_user)
    
    @patch('services.otp.settings')
    def test_send_verification_code_no_rate_limit(self, mock_settings, test_user, fake_redis):
        """Test OTP sending without rate limiting"""
        mock_settings.OTP_RESEND_INTERVAL_SECONDS = 0  # Disabled
        mock_settings.OTP_TTL_SECONDS = 600
        
        with patch('services.otp.redis_client', fake_redis):
            with patch('services.otp.send_templated_email') as mock_email:
                # Send multiple OTPs
                code1 = send_verification_code(None, test_user)
                code2 = send_verification_code(None, test_user)
                
                # Should succeed both times
                assert code1 != code2  # Different codes
                assert mock_email.call_count == 2
    
    def test_verify_code_success(self, test_user, fake_redis):
        """Test successful OTP verification"""
        # Store OTP in Redis
        code = "123456"
        otp_data = {
            "code": code,
            "user_id": test_user.id,
            "email": test_user.email,
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 0
        }
        
        with patch('services.otp.redis_client', fake_redis):
            otp_key = f"{OTP_PREFIX}{test_user.email}"
            fake_redis.setex(otp_key, OTP_EXPIRY, json.dumps(otp_data))
            
            result = verify_code(None, test_user, code)
            
            assert result is True
            # OTP should be deleted after successful verification
            assert fake_redis.get(otp_key) is None
    
    def test_verify_code_invalid(self, test_user, fake_redis):
        """Test OTP verification with invalid code"""
        # Store OTP in Redis
        code = "123456"
        otp_data = {
            "code": code,
            "user_id": test_user.id,
            "email": test_user.email,
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 0
        }
        
        with patch('services.otp.redis_client', fake_redis):
            otp_key = f"{OTP_PREFIX}{test_user.email}"
            fake_redis.setex(otp_key, OTP_EXPIRY, json.dumps(otp_data))
            
            result = verify_code(None, test_user, "654321")
            
            assert result is False
            # OTP should still exist with incremented attempts
            updated_data_str = fake_redis.get(otp_key)
            updated_data = json.loads(updated_data_str)
            assert updated_data["attempts"] == 1
    
    def test_verify_code_not_found(self, test_user, fake_redis):
        """Test OTP verification when OTP doesn't exist"""
        with patch('services.otp.redis_client', fake_redis):
            result = verify_code(None, test_user, "123456")
            
            assert result is False
    
    def test_verify_code_max_attempts(self, test_user, fake_redis):
        """Test OTP verification when max attempts exceeded"""
        # Store OTP with max attempts
        code = "123456"
        otp_data = {
            "code": code,
            "user_id": test_user.id,
            "email": test_user.email,
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 5  # Max attempts reached
        }
        
        with patch('services.otp.redis_client', fake_redis):
            otp_key = f"{OTP_PREFIX}{test_user.email}"
            fake_redis.setex(otp_key, OTP_EXPIRY, json.dumps(otp_data))
            
            result = verify_code(None, test_user, code)
            
            assert result is False
            # OTP should be deleted
            assert fake_redis.get(otp_key) is None
    
    def test_verify_code_corrupted_data(self, test_user, fake_redis):
        """Test OTP verification with corrupted data"""
        with patch('services.otp.redis_client', fake_redis):
            otp_key = f"{OTP_PREFIX}{test_user.email}"
            fake_redis.setex(otp_key, OTP_EXPIRY, "corrupted_json_data")
            
            result = verify_code(None, test_user, "123456")
            
            assert result is False
            # Corrupted data should be deleted
            assert fake_redis.get(otp_key) is None
    
    def test_verify_code_without_email_success(self, test_user, fake_redis):
        """Test OTP verification without email success"""
        code = "123456"
        otp_data = {
            "code": code,
            "user_id": test_user.id,
            "email": test_user.email,
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 0
        }
        
        with patch('services.otp.redis_client', fake_redis):
            # Store OTP and code mapping
            otp_key = f"{OTP_PREFIX}{test_user.email}"
            code_key = f"{OTP_CODE_PREFIX}{code}"
            
            fake_redis.setex(otp_key, OTP_EXPIRY, json.dumps(otp_data))
            fake_redis.setex(code_key, OTP_EXPIRY, test_user.email)
            
            result, email = verify_code_without_email(code)
            
            assert result is True
            assert email == test_user.email
            # Both keys should be deleted
            assert fake_redis.get(otp_key) is None
            assert fake_redis.get(code_key) is None
    
    def test_verify_code_without_email_invalid(self, test_user, fake_redis):
        """Test OTP verification without email with invalid code"""
        with patch('services.otp.redis_client', fake_redis):
            result, email = verify_code_without_email("654321")
            
            assert result is False
            assert email is None
    
    def test_verify_code_without_email_max_attempts(self, test_user, fake_redis):
        """Test OTP verification without email when max attempts exceeded"""
        code = "123456"
        otp_data = {
            "code": code,
            "user_id": test_user.id,
            "email": test_user.email,
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 5  # Max attempts reached
        }
        
        with patch('services.otp.redis_client', fake_redis):
            # Store OTP and code mapping
            otp_key = f"{OTP_PREFIX}{test_user.email}"
            code_key = f"{OTP_CODE_PREFIX}{code}"
            
            fake_redis.setex(otp_key, OTP_EXPIRY, json.dumps(otp_data))
            fake_redis.setex(code_key, OTP_EXPIRY, test_user.email)
            
            result, email = verify_code_without_email(code)
            
            assert result is False
            assert email is None
            # Both keys should be deleted
            assert fake_redis.get(otp_key) is None
            assert fake_redis.get(code_key) is None
    
    def test_get_otp_status_exists(self, test_user, fake_redis):
        """Test getting OTP status when OTP exists"""
        otp_data = {
            "code": "123456",
            "user_id": test_user.id,
            "email": test_user.email,
            "created_at": datetime.utcnow().isoformat(),
            "attempts": 2
        }
        
        with patch('services.otp.redis_client', fake_redis):
            otp_key = f"{OTP_PREFIX}{test_user.email}"
            fake_redis.setex(otp_key, OTP_EXPIRY, json.dumps(otp_data))
            
            status = get_otp_status(test_user.email)
            
            assert status["exists"] is True
            assert status["email"] == test_user.email
            assert status["created_at"] == otp_data["created_at"]
            assert status["attempts"] == 2
            assert "ttl_seconds" in status
    
    def test_get_otp_status_not_exists(self, fake_redis):
        """Test getting OTP status when OTP doesn't exist"""
        with patch('services.otp.redis_client', fake_redis):
            status = get_otp_status("nonexistent@example.com")
            
            assert status["exists"] is False
    
    def test_get_otp_status_corrupted_data(self, test_user, fake_redis):
        """Test getting OTP status with corrupted data"""
        with patch('services.otp.redis_client', fake_redis):
            otp_key = f"{OTP_PREFIX}{test_user.email}"
            fake_redis.setex(otp_key, OTP_EXPIRY, "corrupted_json")
            
            status = get_otp_status(test_user.email)
            
            assert status["exists"] is False
            # Corrupted data should be deleted
            assert fake_redis.get(otp_key) is None


class TestFakeRedis:
    """Test cases for FakeRedis implementation"""
    
    def test_fake_redis_setex_get(self):
        """Test FakeRedis setex and get operations"""
        redis = _FakeRedis()
        
        redis.setex("test_key", 60, "test_value")
        assert redis.get("test_key") == "test_value"
    
    def test_fake_redis_expiry(self):
        """Test FakeRedis key expiration"""
        redis = _FakeRedis()
        
        # Set key with 1 second TTL
        redis.setex("test_key", 1, "test_value")
        assert redis.get("test_key") == "test_value"
        
        # Wait for expiration
        import time
        time.sleep(1.1)
        
        assert redis.get("test_key") is None
    
    def test_fake_redis_exists(self):
        """Test FakeRedis exists operation"""
        redis = _FakeRedis()
        
        assert redis.exists("test_key") == 0
        
        redis.setex("test_key", 60, "test_value")
        assert redis.exists("test_key") == 1
    
    def test_fake_redis_ttl(self):
        """Test FakeRedis TTL operation"""
        redis = _FakeRedis()
        
        # Non-existent key
        assert redis.ttl("nonexistent") == -2
        
        # Set key with TTL
        redis.setex("test_key", 60, "test_value")
        ttl = redis.ttl("test_key")
        assert 0 <= ttl <= 60
        
        # Test expired key by manually removing it
        redis.delete("test_key")
        assert redis.ttl("test_key") == -2
    
    def test_fake_redis_delete(self):
        """Test FakeRedis delete operation"""
        redis = _FakeRedis()
        
        redis.setex("test_key", 60, "test_value")
        assert redis.get("test_key") == "test_value"
        
        redis.delete("test_key")
        assert redis.get("test_key") is None
        assert redis.exists("test_key") == 0
    
    def test_fake_redis_cleanup_on_operation(self):
        """Test that expired keys are cleaned up during operations"""
        redis = _FakeRedis()
        
        # Set key with short TTL and manually expire
        redis.setex("test_key", 1, "test_value")
        assert redis.get("test_key") == "test_value"
        
        # Manually expire by setting past expiry
        redis._exp["test_key"] = datetime.utcnow().timestamp() - 1
        
        # Any operation should clean up the expired key
        assert redis.exists("test_key") == 0
        assert redis.ttl("test_key") == -2
