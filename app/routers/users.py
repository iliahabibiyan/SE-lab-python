from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.models import User
from app.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/api/v1/users", tags=["users"])

DUPLICATE_NATIONAL_CODE = "کد ملی تکراری است"


@router.post("", response_model=UserResponse, status_code=201)
def register_user(body: UserCreate, db: Session = Depends(get_db)):
    """US1: register a new user. Status is ACTIVE by default."""
    exists = db.scalar(select(User.id).where(User.national_code == body.national_code))
    if exists:
        raise ApiError(409, "CONFLICT", DUPLICATE_NATIONAL_CODE)

    user = User(**body.model_dump())
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two requests with the same national code at the same time
        db.rollback()
        raise ApiError(409, "CONFLICT", DUPLICATE_NATIONAL_CODE)
    db.refresh(user)
    return user
