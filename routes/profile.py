from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import Optional

from core.db import get_db
from models.user import User
from schemas.profile import ProfileResponse, ProfileUpdate, ProfilePictureUpload, ProfilePictureDelete
from routes.auth import get_current_user
from services.cloudinary import cloudinary_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/", response_model=ProfileResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile"""
    return current_user


@router.put("/", response_model=ProfileResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile"""
    # Update only the fields that are provided
    update_data = profile_data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.patch("/", response_model=ProfileResponse)
async def patch_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Partially update current user's profile"""
    # Update only the fields that are provided
    update_data = profile_data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post("/upload-picture", response_model=ProfilePictureUpload)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a profile picture"""
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image"
        )
    
    # Validate file size (max 5MB)
    max_size = 5 * 1024 * 1024  # 5MB
    file_data = await file.read()
    
    if len(file_data) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be less than 5MB"
        )
    
    # Upload to Cloudinary
    success, url, error = cloudinary_service.upload_profile_picture(
        file_data=file_data,
        filename=file.filename,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {error}"
        )
    
    # Update user's profile picture URL
    current_user.profile_picture = url
    db.commit()
    db.refresh(current_user)
    
    return ProfilePictureUpload(
        success=True,
        url=url,
        message="Profile picture uploaded successfully"
    )


@router.delete("/delete-picture", response_model=ProfilePictureDelete)
async def delete_profile_picture(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete the current profile picture"""
    
    if not current_user.profile_picture:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete"
        )
    
    # Delete from Cloudinary
    success, error = cloudinary_service.delete_profile_picture(current_user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image: {error}"
        )
    
    # Update user's profile picture URL
    current_user.profile_picture = None
    db.commit()
    db.refresh(current_user)
    
    return ProfilePictureDelete(
        success=True,
        message="Profile picture deleted successfully"
    )
