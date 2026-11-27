from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils import new_id


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    national_code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    birth_date: Mapped[date]
    status: Mapped[str] = mapped_column(String(10), default="ACTIVE")
    phone_number: Mapped[str] = mapped_column(String(11))
    address: Mapped[str] = mapped_column(String(255))
    postal_code: Mapped[str] = mapped_column(String(10))
    password_hash: Mapped[str | None] = mapped_column(String(255), default=None)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(default=None)  # UTC
    role: Mapped[str] = mapped_column(String(10), default="USER")  # USER or ADMIN
    token_version: Mapped[int] = mapped_column(Integer, default=0)  # grows when the user is blocked: revokes tokens


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))  # the owner
    sheba_number: Mapped[str] = mapped_column(String(26), unique=True)
    status: Mapped[str] = mapped_column(String(10), default="ACTIVE")  # ACTIVE, INACTIVE or BLOCKED
    account_type: Mapped[str] = mapped_column(String(10), default="CURRENT")  # CURRENT, SAVINGS or DEPOSIT
