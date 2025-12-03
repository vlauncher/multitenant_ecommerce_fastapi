import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from io import BytesIO

from main import app
from core.db import get_db
from models.user import User
from security.jwt import create_access_token
from security.password import hash_password

client = TestClient(app)


@pytest.fixture
def test_user(db: Session):
    """Create a test user"""
    user = User(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        password_hash=hash_password("testpassword"),
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User):
    """Get auth headers for test user"""
    access_token = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {access_token}"}


class TestProfileEndpoints:
    
    def test_get_profile(self, test_user: User, auth_headers: dict):
        """Test getting user profile"""
        response = client.get("/profile/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["first_name"] == test_user.first_name
        assert data["last_name"] == test_user.last_name
        assert data["bio"] is None
        assert data["address"] is None
        assert data["age"] is None
        assert data["profile_picture"] is None
    
    def test_update_profile(self, test_user: User, auth_headers: dict, db: Session):
        """Test updating user profile"""
        update_data = {
            "bio": "This is my bio",
            "address": "123 Test Street",
            "age": 25
        }
        
        response = client.put("/profile/", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["bio"] == update_data["bio"]
        assert data["address"] == update_data["address"]
        assert data["age"] == update_data["age"]
        
        # Verify in database
        db.refresh(test_user)
        assert test_user.bio == update_data["bio"]
        assert test_user.address == update_data["address"]
        assert test_user.age == update_data["age"]
    
    def test_patch_profile(self, test_user: User, auth_headers: dict, db: Session):
        """Test partially updating user profile"""
        update_data = {
            "bio": "Updated bio"
        }
        
        response = client.patch("/profile/", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["bio"] == update_data["bio"]
        assert data["address"] is None  # Should remain unchanged
        assert data["age"] is None  # Should remain unchanged
    
    def test_upload_profile_picture_invalid_file_type(self, auth_headers: dict):
        """Test uploading non-image file"""
        # Create a text file instead of image
        file_data = b"This is not an image"
        files = {"file": ("test.txt", BytesIO(file_data), "text/plain")}
        
        response = client.post("/profile/upload-picture", files=files, headers=auth_headers)
        
        assert response.status_code == 400
        assert "File must be an image" in response.json()["detail"]
    
    def test_upload_profile_picture_large_file(self, auth_headers: dict):
        """Test uploading file that's too large"""
        # Create a large image file (6MB)
        file_data = b"x" * (6 * 1024 * 1024)  # 6MB
        files = {"file": ("large.jpg", BytesIO(file_data), "image/jpeg")}
        
        response = client.post("/profile/upload-picture", files=files, headers=auth_headers)
        
        assert response.status_code == 400
        assert "File size must be less than 5MB" in response.json()["detail"]
    
    def test_delete_profile_picture_no_picture(self, auth_headers: dict, test_user: User):
        """Test deleting profile picture when none exists"""
        response = client.delete("/profile/delete-picture", headers=auth_headers)
        
        assert response.status_code == 400
        assert "No profile picture to delete" in response.json()["detail"]
    
    def test_unauthorized_access(self):
        """Test accessing profile endpoints without authentication"""
        endpoints = [
            ("GET", "/profile/"),
            ("PUT", "/profile/", {}),
            ("PATCH", "/profile/", {}),
            ("POST", "/profile/upload-picture"),
            ("DELETE", "/profile/delete-picture"),
        ]
        
        for method, endpoint, *data in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "PUT":
                response = client.put(endpoint, json=data[0] if data else {})
            elif method == "PATCH":
                response = client.patch(endpoint, json=data[0] if data else {})
            elif method == "POST":
                response = client.post(endpoint, files={"file": ("test.jpg", BytesIO(b"test"), "image/jpeg")})
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 401
    
    def test_age_validation(self, test_user: User, auth_headers: dict):
        """Test age field validation"""
        # Test negative age
        response = client.put("/profile/", json={"age": -5}, headers=auth_headers)
        assert response.status_code == 422
        
        # Test age too high
        response = client.put("/profile/", json={"age": 200}, headers=auth_headers)
        assert response.status_code == 422
        
        # Test valid age
        response = client.put("/profile/", json={"age": 30}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["age"] == 30
