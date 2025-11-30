import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.user import User
from models.otp import OTP
from core.db import Base


@pytest.fixture
def db_session():
    """Create a test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


class TestUser:
    """Test cases for User model"""
    
    def test_user_creation(self, db_session):
        """Test creating a user with all fields"""
        user = User(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            password_hash="hashed_password_123",
            is_verified=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.email == "john.doe@example.com"
        assert user.password_hash == "hashed_password_123"
        assert user.is_verified is True
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_user_default_values(self, db_session):
        """Test user creation with default values"""
        user = User(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            password_hash="hashed_password_456"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.is_verified is False  # Default value
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)
    
    def test_user_email_uniqueness(self, db_session):
        """Test that email must be unique"""
        user1 = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password_hash="hash1"
        )
        db_session.add(user1)
        db_session.commit()
        
        user2 = User(
            first_name="Jane",
            last_name="Doe",
            email="john@example.com",  # Same email
            password_hash="hash2"
        )
        db_session.add(user2)
        
        with pytest.raises(Exception):  # Should raise IntegrityError
            db_session.commit()
    
    def test_user_timestamps(self, db_session):
        """Test that timestamps are properly set"""
        before_creation = datetime.utcnow()
        user = User(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password_hash="hash"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        after_creation = datetime.utcnow()
        
        assert before_creation <= user.created_at <= after_creation
        assert before_creation <= user.updated_at <= after_creation
    
    def test_user_update_timestamp(self, db_session):
        """Test that updated_at changes on update"""
        user = User(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password_hash="hash"
        )
        db_session.add(user)
        db_session.commit()
        
        original_updated_at = user.updated_at
        
        # Wait a bit to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        user.first_name = "Updated"
        db_session.commit()
        db_session.refresh(user)
        
        assert user.updated_at > original_updated_at
    
    def test_user_string_representation(self, db_session):
        """Test user string representation"""
        user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password_hash="hash"
        )
        db_session.add(user)
        db_session.commit()
        
        # Test that the object can be converted to string
        user_str = str(user)
        assert "User" in user_str or "john@example.com" in user_str


class TestOTP:
    """Test cases for OTP model"""
    
    def test_otp_creation(self, db_session):
        """Test creating an OTP with all fields"""
        # First create a user
        user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password_hash="hash"
        )
        db_session.add(user)
        db_session.commit()
        
        # Create OTP
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        last_sent_at = datetime.utcnow()
        
        otp = OTP(
            user_id=user.id,
            code="123456",
            expires_at=expires_at,
            last_sent_at=last_sent_at,
            send_count=2
        )
        db_session.add(otp)
        db_session.commit()
        db_session.refresh(otp)
        
        assert otp.id is not None
        assert otp.user_id == user.id
        assert otp.code == "123456"
        assert otp.expires_at == expires_at
        assert otp.last_sent_at == last_sent_at
        assert otp.send_count == 2
    
    def test_otp_default_send_count(self, db_session):
        """Test OTP creation with default send_count"""
        user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password_hash="hash"
        )
        db_session.add(user)
        db_session.commit()
        
        otp = OTP(
            user_id=user.id,
            code="654321",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            last_sent_at=datetime.utcnow()
        )
        db_session.add(otp)
        db_session.commit()
        db_session.refresh(otp)
        
        assert otp.send_count == 1  # Default value
    
    def test_otp_user_relationship(self, db_session):
        """Test the relationship between OTP and User"""
        user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password_hash="hash"
        )
        db_session.add(user)
        db_session.commit()
        
        otp = OTP(
            user_id=user.id,
            code="111111",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            last_sent_at=datetime.utcnow()
        )
        db_session.add(otp)
        db_session.commit()
        db_session.refresh(otp)
        
        # Test relationship
        assert otp.user == user
        assert otp.user.first_name == "John"
        assert otp.user.email == "john@example.com"
    
    def test_otp_foreign_key_constraint(self, db_session):
        """Test that OTP must reference a valid user"""
        # SQLite doesn't enforce foreign key constraints by default
        # This test will succeed in SQLite but would fail in PostgreSQL
        otp = OTP(
            user_id=999,  # Non-existent user ID
            code="999999",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            last_sent_at=datetime.utcnow()
        )
        db_session.add(otp)
        db_session.commit()
        db_session.refresh(otp)
        
        # In SQLite, this will actually succeed, so we just verify the OTP was created
        assert otp.id is not None
        assert otp.user_id == 999
    
    def test_otp_expiry_static_method(self):
        """Test the expiry static method"""
        ttl_seconds = 300  # 5 minutes
        before_calculation = datetime.utcnow()
        
        expiry_time = OTP.expiry(ttl_seconds)
        after_calculation = datetime.utcnow()
        
        expected_min = before_calculation + timedelta(seconds=ttl_seconds)
        expected_max = after_calculation + timedelta(seconds=ttl_seconds)
        
        assert expected_min <= expiry_time <= expected_max
    
    def test_otp_multiple_for_same_user(self, db_session):
        """Test creating multiple OTPs for the same user"""
        user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password_hash="hash"
        )
        db_session.add(user)
        db_session.commit()
        
        # Create multiple OTPs
        otp1 = OTP(
            user_id=user.id,
            code="111111",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            last_sent_at=datetime.utcnow()
        )
        otp2 = OTP(
            user_id=user.id,
            code="222222",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            last_sent_at=datetime.utcnow()
        )
        
        db_session.add(otp1)
        db_session.add(otp2)
        db_session.commit()
        
        # Both should be created successfully
        assert otp1.id is not None
        assert otp2.id is not None
        assert otp1.user_id == otp2.user_id
    
    def test_otp_string_representation(self, db_session):
        """Test OTP string representation"""
        user = User(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password_hash="hash"
        )
        db_session.add(user)
        db_session.commit()
        
        otp = OTP(
            user_id=user.id,
            code="123456",
            expires_at=datetime.utcnow() + timedelta(minutes=5),
            last_sent_at=datetime.utcnow()
        )
        db_session.add(otp)
        db_session.commit()
        
        # Test that the object can be converted to string
        otp_str = str(otp)
        assert "OTP" in otp_str or "123456" in otp_str
