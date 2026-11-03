import uuid
from sqlalchemy import String, Text, Boolean, ForeignKey, UniqueConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

def uid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Game(Base):
    __tablename__ = "games"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(160))
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    admin_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="registration")

class Member(Base):
    __tablename__ = "members"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("game_id", "user_id"),)

class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id"), unique=True)
    display_name: Mapped[str] = mapped_column(String(100))
    wishes: Mapped[str] = mapped_column(Text)

class Restriction(Base):
    __tablename__ = "restrictions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), index=True)
    santa_member_id: Mapped[str] = mapped_column(ForeignKey("members.id"))
    recipient_member_id: Mapped[str] = mapped_column(ForeignKey("members.id"))
    __table_args__ = (
        UniqueConstraint("game_id", "santa_member_id", "recipient_member_id"),
    )

class Drawing(Base):
    __tablename__ = "drawings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")

class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    drawing_id: Mapped[str] = mapped_column(ForeignKey("drawings.id"), index=True)
    santa_member_id: Mapped[str] = mapped_column(ForeignKey("members.id"))
    recipient_member_id: Mapped[str] = mapped_column(ForeignKey("members.id"))
    __table_args__ = (
        UniqueConstraint("drawing_id", "santa_member_id"),
        UniqueConstraint("drawing_id", "recipient_member_id"),
    )

class Chat(Base):
    __tablename__ = "chats"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    assignment_id: Mapped[str] = mapped_column(ForeignKey("assignments.id"), unique=True)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id"), index=True)
    sender_member_id: Mapped[str] = mapped_column(ForeignKey("members.id"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
