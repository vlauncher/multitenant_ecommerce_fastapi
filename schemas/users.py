from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    is_verified: bool

    class Config:
        from_attributes = True
