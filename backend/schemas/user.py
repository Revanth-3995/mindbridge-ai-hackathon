from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class UserCreate(BaseModel):
	email: EmailStr
	password: str = Field(..., min_length=6, max_length=128)
	full_name: Optional[str] = None


class UserLogin(BaseModel):
	email: EmailStr
	password: str


class UserResponse(BaseModel):
	id: str
	email: EmailStr
	full_name: Optional[str] = None
	created_at: Optional[str] = None

	class Config:
		from_attributes = True


class Token(BaseModel):
	access_token: str
	token_type: str = "bearer"
	user: UserResponse


