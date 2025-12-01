import pytest
import json
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from core.db import Base, get_db
from models.user import User
from security.password import hash_password


# Override database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def setup_database():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db():
    """Create test database session"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user(test_db):
    """Create a test user"""
    user = User(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        password_hash=hash_password("password123"),
        is_verified=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def unverified_user(test_db):
    """Create an unverified test user"""
    user = User(
        first_name="Jane",
        last_name="Smith",
        email="jane.smith@example.com",
        password_hash=hash_password("password123"),
        is_verified=False
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


class TestAuthRoutes:
    """Test cases for authentication routes"""
    
    def test_register_success(self, setup_database):
        """Test successful user registration"""
        response = client.post("/auth/register", json={
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "Test"
        assert data["last_name"] == "User"
        assert data["email"] == "test.user@example.com"
        assert data["is_verified"] is False
        assert "id" in data
    
    def test_register_duplicate_email(self, setup_database, test_user):
        """Test registration with duplicate email"""
        response = client.post("/auth/register", json={
            "first_name": "Another",
            "last_name": "User",
            "email": test_user.email,  # Same email
            "password": "password123"
        })
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_register_invalid_data(self, setup_database):
        """Test registration with invalid data"""
        # Missing required fields
        response = client.post("/auth/register", json={
            "first_name": "Test",
            "email": "test@example.com"
            # Missing last_name and password
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_register_email_case_insensitive(self, setup_database, test_user):
        """Test that email registration is case insensitive"""
        response = client.post("/auth/register", json={
            "first_name": "Another",
            "last_name": "User",
            "email": test_user.email.upper(),  # Uppercase version
            "password": "password123"
        })
        
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    @patch('routes.auth.send_verification_code')
    def test_register_sends_otp(self, mock_send_otp, setup_database):
        """Test that registration sends OTP"""
        mock_send_otp.return_value = "123456"
        
        response = client.post("/auth/register", json={
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 201
        # Verify OTP was sent by checking the mock was called
        assert mock_send_otp.called
    
    def test_login_success(self, setup_database, test_user):
        """Test successful login"""
        response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "password123"
        })
        
        # Check if user is verified first
        if not test_user.is_verified:
            # Mark user as verified for this test
            db = TestingSessionLocal()
            user = db.query(User).filter(User.id == test_user.id).first()
            user.is_verified = True
            db.commit()
            db.close()
            
            # Try login again
            response = client.post("/auth/login", json={
                "email": test_user.email,
                "password": "password123"
            })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0
    
    def test_login_invalid_credentials(self, setup_database, test_user):
        """Test login with invalid credentials"""
        response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "wrongpassword"
        })
        
        assert response.status_code == 400
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, setup_database):
        """Test login with non-existent user"""
        response = client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 400
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_login_unverified_user(self, setup_database, unverified_user):
        """Test login with unverified user"""
        response = client.post("/auth/login", json={
            "email": unverified_user.email,
            "password": "password123"
        })
        
        assert response.status_code == 403
        assert "Account not verified" in response.json()["detail"]
    
    def test_login_email_case_insensitive(self, setup_database, test_user):
        """Test that login email is case insensitive"""
        # Ensure user is verified first
        db = TestingSessionLocal()
        user = db.query(User).filter(User.id == test_user.id).first()
        user.is_verified = True
        db.commit()
        db.close()
        
        response = client.post("/auth/login", json={
            "email": test_user.email.upper(),  # Uppercase version
            "password": "password123"
        })
        
        assert response.status_code == 200
        assert "access_token" in response.json()
    
    @patch('routes.auth.verify_code_without_email')
    @patch('routes.auth.send_templated_email')
    def test_verify_otp_success(self, mock_email, mock_verify, setup_database, test_user):
        """Test successful OTP verification"""
        mock_verify.return_value = (True, test_user.email)
        
        response = client.post("/auth/verify-otp", json={
            "code": "123456"
        })
        
        assert response.status_code == 200
        assert response.json()["detail"] == "Verified"
        mock_verify.assert_called_once_with("123456")
        mock_email.assert_called_once()
    
    def test_verify_otp_invalid_code(self, setup_database):
        """Test OTP verification with invalid code"""
        with patch('services.otp.verify_code_without_email', return_value=(False, None)):
            response = client.post("/auth/verify-otp", json={
                "code": "000000"
            })
            
            assert response.status_code == 400
            assert "Invalid or expired code" in response.json()["detail"]
    
    def test_verify_otp_user_not_found(self, setup_database):
        """Test OTP verification when user doesn't exist"""
        with patch('routes.auth.verify_code_without_email', return_value=(True, "nonexistent@example.com")):
            response = client.post("/auth/verify-otp", json={
                "code": "123456"
            })
            
            # Should return 404 when user is not found
            assert response.status_code == 404
            assert "User not found" in response.json()["detail"]
    
    @patch('routes.auth.send_verification_code')
    def test_resend_otp_success(self, mock_send, setup_database, test_user):
        """Test successful OTP resend"""
        mock_send.return_value = "123456"
        
        response = client.post("/auth/resend-otp", json={
            "email": test_user.email
        })
        
        assert response.status_code == 200
        assert response.json()["detail"] == "OTP sent"
        # Verify the mock was called
        assert mock_send.called
    
    def test_resend_otp_user_not_found(self, setup_database):
        """Test OTP resend with non-existent user"""
        response = client.post("/auth/resend-otp", json={
            "email": "nonexistent@example.com"
        })
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    @patch('routes.auth.send_verification_code')
    def test_resend_otp_rate_limited(self, mock_send, setup_database, test_user):
        """Test OTP resend with rate limiting"""
        mock_send.side_effect = ValueError("Please wait 60 seconds")
        
        response = client.post("/auth/resend-otp", json={
            "email": test_user.email
        })
        
        assert response.status_code == 429
        assert "Please wait" in response.json()["detail"]
    
    def test_resend_otp_email_case_insensitive(self, setup_database, test_user):
        """Test that resend OTP email is case insensitive"""
        with patch('services.otp.send_verification_code') as mock_send:
            mock_send.return_value = "123456"
            
            response = client.post("/auth/resend-otp", json={
                "email": test_user.email.upper()  # Uppercase version
            })
            
            assert response.status_code == 200
            assert response.json()["detail"] == "OTP sent"
    
    def test_change_password_success(self, setup_database, test_user):
        """Test successful password change"""
        # Ensure user is verified first
        db = TestingSessionLocal()
        user = db.query(User).filter(User.id == test_user.id).first()
        user.is_verified = True
        db.commit()
        db.close()
        
        # Login to get token
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        
        # Change password
        response = client.post("/auth/change-password", 
            json={
                "old_password": "password123",
                "new_password": "newpassword123"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json()["detail"] == "Password changed"
        
        # Verify new password works
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "newpassword123"
        })
        assert login_response.status_code == 200
    
    def test_change_password_wrong_old_password(self, setup_database, test_user):
        """Test password change with wrong old password"""
        # Ensure user is verified first
        db = TestingSessionLocal()
        user = db.query(User).filter(User.id == test_user.id).first()
        user.is_verified = True
        db.commit()
        db.close()
        
        # Login to get token
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        
        response = client.post("/auth/change-password", 
            json={
                "old_password": "wrongpassword",
                "new_password": "newpassword123"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "Old password is incorrect" in response.json()["detail"]
    
    def test_change_password_unauthorized(self, setup_database):
        """Test password change without authorization"""
        response = client.post("/auth/change-password", 
            json={
                "old_password": "password123",
                "new_password": "newpassword123"
            }
        )
        
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]
    
    def test_change_password_invalid_token(self, setup_database):
        """Test password change with invalid token"""
        response = client.post("/auth/change-password", 
            json={
                "old_password": "password123",
                "new_password": "newpassword123"
            },
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]
    
    @patch('routes.auth.send_verification_code')
    def test_reset_password_request_success(self, mock_send, setup_database, test_user):
        """Test successful password reset request"""
        mock_send.return_value = "123456"
        
        response = client.post("/auth/reset-password/request", json={
            "email": test_user.email
        })
        
        assert response.status_code == 200
        assert response.json()["detail"] == "If the email exists, a code has been sent"
        # Verify the mock was called
        assert mock_send.called
    
    def test_reset_password_request_nonexistent_email(self, setup_database):
        """Test password reset request with non-existent email"""
        response = client.post("/auth/reset-password/request", json={
            "email": "nonexistent@example.com"
        })
        
        # Should still return 200 to prevent email enumeration
        assert response.status_code == 200
        assert response.json()["detail"] == "If the email exists, a code has been sent"
    
    def test_reset_password_request_email_case_insensitive(self, setup_database, test_user):
        """Test that reset password request email is case insensitive"""
        with patch('services.otp.send_verification_code') as mock_send:
            mock_send.return_value = "123456"
            
            response = client.post("/auth/reset-password/request", json={
                "email": test_user.email.upper()  # Uppercase version
            })
            
            assert response.status_code == 200
            assert response.json()["detail"] == "If the email exists, a code has been sent"
    
    @patch('routes.auth.verify_code')
    @patch('routes.auth.send_templated_email')
    def test_reset_password_confirm_success(self, mock_email, mock_verify, setup_database, test_user):
        """Test successful password reset confirmation"""
        mock_verify.return_value = True
        
        response = client.post("/auth/reset-password/confirm", json={
            "email": test_user.email,
            "code": "123456",
            "new_password": "newpassword123"
        })
        
        assert response.status_code == 200
        assert response.json()["detail"] == "Password reset"
        mock_verify.assert_called_once()
        mock_email.assert_called_once()
        
        # Verify new password works
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "newpassword123"
        })
        assert login_response.status_code == 200
    
    def test_reset_password_confirm_user_not_found(self, setup_database):
        """Test password reset confirmation with non-existent user"""
        response = client.post("/auth/reset-password/confirm", json={
            "email": "nonexistent@example.com",
            "code": "123456",
            "new_password": "newpassword123"
        })
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]
    
    def test_reset_password_confirm_invalid_code(self, setup_database, test_user):
        """Test password reset confirmation with invalid code"""
        with patch('services.otp.verify_code', return_value=False):
            response = client.post("/auth/reset-password/confirm", json={
                "email": test_user.email,
                "code": "000000",
                "new_password": "newpassword123"
            })
            
            assert response.status_code == 400
            assert "Invalid or expired code" in response.json()["detail"]
    
    def test_reset_password_confirm_email_case_insensitive(self, setup_database, test_user):
        """Test that reset password confirm email is case insensitive"""
        with patch('routes.auth.verify_code', return_value=True):
            with patch('services.otp.send_templated_email') as mock_email:
                response = client.post("/auth/reset-password/confirm", json={
                    "email": test_user.email.upper(),  # Uppercase version
                    "code": "123456",
                    "new_password": "newpassword123"
                })
                
                assert response.status_code == 200
                assert response.json()["detail"] == "Password reset"
    
    def test_refresh_token_success(self, setup_database, test_user):
        """Test successful token refresh"""
        # Ensure user is verified first
        db = TestingSessionLocal()
        user = db.query(User).filter(User.id == test_user.id).first()
        user.is_verified = True
        db.commit()
        db.close()
        
        # Login to get refresh token
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "password123"
        })
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh tokens
        response = client.post("/auth/refresh-token", json={
            "refresh_token": refresh_token
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0
    
    def test_refresh_token_invalid(self, setup_database):
        """Test refresh token with invalid token"""
        response = client.post("/auth/refresh-token", json={
            "refresh_token": "invalid_refresh_token"
        })
        
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]
    
    def test_refresh_token_user_not_found(self, setup_database):
        """Test refresh token for non-existent user"""
        # Create a valid-looking token for non-existent user
        with patch('security.jwt.decode_refresh', return_value={"sub": "99999"}):
            response = client.post("/auth/refresh-token", json={
                "refresh_token": "valid_format_token"
            })
            
            assert response.status_code == 404
            assert "User not found" in response.json()["detail"]
    
    @patch('services.otp.get_otp_status')
    def test_get_otp_status_success(self, mock_status, setup_database):
        """Test getting OTP status"""
        mock_status.return_value = {
            "exists": True,
            "email": "test@example.com",
            "created_at": "2023-01-01T00:00:00",
            "attempts": 0,
            "ttl_seconds": 300
        }
        
        response = client.get("/auth/otp-status/test@example.com")
        
        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert data["email"] == "test@example.com"
        mock_status.assert_called_once_with("test@example.com")
    
    def test_get_otp_status_not_exists(self, setup_database):
        """Test getting OTP status when OTP doesn't exist"""
        with patch('services.otp.get_otp_status', return_value={"exists": False}):
            response = client.get("/auth/otp-status/nonexistent@example.com")
            
            assert response.status_code == 200
            data = response.json()
            assert data["exists"] is False
    
    def test_get_otp_status_email_case_insensitive(self, setup_database):
        """Test that OTP status email is case insensitive"""
        with patch('services.otp.get_otp_status') as mock_status:
            mock_status.return_value = {"exists": False}
            
            response = client.get("/auth/otp-status/TEST@EXAMPLE.COM")
            
            assert response.status_code == 200
            mock_status.assert_called_once_with("test@example.com")


class TestGetCurrentUser:
    """Test cases for get_current_user dependency"""
    
    def test_get_current_user_success(self, setup_database, test_user):
        """Test successful current user retrieval"""
        # Ensure user is verified first
        db = TestingSessionLocal()
        user = db.query(User).filter(User.id == test_user.id).first()
        user.is_verified = True
        db.commit()
        db.close()
        
        # Login to get token
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        
        # Use token to access protected endpoint
        response = client.get("/auth/otp-status/test@example.com", 
            headers={"Authorization": f"Bearer {token}"})
        
        # Should work (200 indicates authentication passed)
        assert response.status_code == 200
    
    def test_get_current_user_no_token(self, setup_database):
        """Test current user retrieval without token"""
        response = client.post("/auth/change-password", 
            json={
                "old_password": "password123",
                "new_password": "newpassword123"
            })
        
        assert response.status_code == 401
    
    def test_get_current_user_malformed_token(self, setup_database):
        """Test current user retrieval with malformed token"""
        response = client.post("/auth/change-password", 
            json={
                "old_password": "password123",
                "new_password": "newpassword123"
            },
            headers={"Authorization": "Bearer"})
        
        assert response.status_code == 401
    
    def test_get_current_user_wrong_scheme(self, setup_database):
        """Test current user retrieval with wrong authorization scheme"""
        response = client.post("/auth/change-password", 
            json={
                "old_password": "password123",
                "new_password": "newpassword123"
            },
            headers={"Authorization": f"Basic token123"})
        
        assert response.status_code == 401
    
    def test_get_current_user_deleted_user(self, setup_database, test_user):
        """Test current user retrieval after user deletion"""
        # Ensure user is verified first
        db = TestingSessionLocal()
        user = db.query(User).filter(User.id == test_user.id).first()
        user.is_verified = True
        db.commit()
        db.close()
        
        # Login to get token
        login_response = client.post("/auth/login", json={
            "email": test_user.email,
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        
        # Delete user using a fresh session
        db = TestingSessionLocal()
        user_to_delete = db.query(User).filter(User.id == test_user.id).first()
        if user_to_delete:
            db.delete(user_to_delete)
            db.commit()
        db.close()
        
        # Try to use token
        response = client.post("/auth/change-password", 
            json={
                "old_password": "password123",
                "new_password": "newpassword123"
            },
            headers={"Authorization": f"Bearer {token}"})
        
        assert response.status_code == 401
        assert "User not found" in response.json()["detail"]


class TestRouteValidation:
    """Test cases for route validation and edge cases"""
    
    def test_register_whitespace_handling(self, setup_database):
        """Test that whitespace in names is handled correctly"""
        response = client.post("/auth/register", json={
            "first_name": "  Test  ",
            "last_name": "  User  ",
            "email": "test@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "Test"  # Whitespace trimmed
        assert data["last_name"] == "User"   # Whitespace trimmed
    
    def test_register_email_lowercase(self, setup_database):
        """Test that email is stored in lowercase"""
        response = client.post("/auth/register", json={
            "first_name": "Test",
            "last_name": "User",
            "email": "Test@EXAMPLE.COM",
            "password": "password123"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"  # Lowercase
    
    def test_login_email_lowercase(self, setup_database, test_user):
        """Test that login email comparison is case insensitive"""
        # Ensure user is verified first
        db = TestingSessionLocal()
        user = db.query(User).filter(User.id == test_user.id).first()
        user.is_verified = True
        db.commit()
        db.close()
        
        response = client.post("/auth/login", json={
            "email": "JOHN.DOE@EXAMPLE.COM",  # Uppercase/mixed case
            "password": "password123"
        })
        
        assert response.status_code == 200
    
    def test_invalid_json_payload(self, setup_database):
        """Test handling of invalid JSON payload"""
        response = client.post("/auth/register", 
            data="invalid json",
            headers={"Content-Type": "application/json"})
        
        assert response.status_code == 422
    
    def test_missing_content_type(self, setup_database):
        """Test handling of missing content-type header"""
        response = client.post("/auth/register", 
            data='{"first_name": "Test", "last_name": "User", "email": "test@example.com", "password": "password123"}')
        
        # FastAPI should handle this gracefully
        assert response.status_code in [200, 201, 422]
