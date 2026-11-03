from pydantic import BaseModel, EmailStr, Field

class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)

class GameCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)

class JoinGame(BaseModel):
    invite_code: str = Field(min_length=6, max_length=32)

class ProfileInput(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    wishes: str = Field(min_length=1, max_length=3000)

class RestrictionInput(BaseModel):
    santa_member_id: str
    recipient_member_id: str

class MessageInput(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
