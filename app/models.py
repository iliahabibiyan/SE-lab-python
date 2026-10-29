from datetime import date

from sqlalchemy import String
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