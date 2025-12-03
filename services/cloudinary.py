import os
import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from typing import Optional, Tuple


class CloudinaryService:
    def __init__(self):
        # Configure Cloudinary with environment variables
        cloudinary.config(
            cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
            api_key=os.getenv("CLOUDINARY_API_KEY"),
            api_secret=os.getenv("CLOUDINARY_API_SECRET"),
            secure=True
        )
    
    def upload_profile_picture(self, file_data: bytes, filename: str, user_id: int) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Upload a profile picture to Cloudinary
        
        Args:
            file_data: Binary data of the image file
            filename: Original filename
            user_id: ID of the user uploading the image
            
        Returns:
            Tuple of (success: bool, url: Optional[str], error: Optional[str])
        """
        try:
            # Generate a unique filename for the user
            public_id = f"user_{user_id}_profile"
            
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(
                file_data,
                public_id=public_id,
                folder="profile_pictures",
                overwrite=True,
                resource_type="image",
                format="webp",
                width=300,
                height=300,
                crop="fill",
                gravity="face",
                quality="auto",
                fetch_format="auto"
            )
            
            return True, result.get("secure_url"), None
            
        except CloudinaryError as e:
            return False, None, str(e)
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"
    
    def delete_profile_picture(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Delete a user's profile picture from Cloudinary
        
        Args:
            user_id: ID of the user whose picture to delete
            
        Returns:
            Tuple of (success: bool, error: Optional[str])
        """
        try:
            public_id = f"profile_pictures/user_{user_id}_profile"
            
            result = cloudinary.uploader.destroy(public_id)
            
            # Cloudinary returns {"result": "ok"} or {"result": "not found"}
            if result.get("result") == "ok":
                return True, None
            elif result.get("result") == "not found":
                return True, None  # Consider it successful if it's already gone
            else:
                return False, f"Failed to delete: {result.get('result')}"
                
        except CloudinaryError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"


# Global instance
cloudinary_service = CloudinaryService()
