from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class ProfileUpdate(BaseModel):
    bio: Optional[str] = Field(None, max_length=1000)
    address: Optional[str] = Field(None, max_length=500)
    age: Optional[int] = Field(None, ge=0, le=150)
    
    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError('Age must be between 0 and 150')
        return v


class ProfileResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    bio: Optional[str] = None
    address: Optional[str] = None
    age: Optional[int] = None
    profile_picture: Optional[str] = None
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ProfilePictureUpload(BaseModel):
    success: bool
    url: Optional[str] = None
    message: str


class ProfilePictureDelete(BaseModel):
    success: bool
    message: str
