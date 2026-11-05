from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.errors import ApiError
from app.models import User
from app.schemas import UserCreate, UserResponse
from app.security import hash_password

router = APIRouter(prefix="/api/v1/users", tags=["users"])

DUPLICATE_NATIONAL_CODE = "کد ملی تکراری است"


@router.post("", response_model=UserResponse, status_code=201)
def register_user(body: UserCreate, db: Session = Depends(get_db)):
    """US1: register a new user. Status is ACTIVE by default."""
    exists = db.scalar(select(User.id).where(User.national_code == body.national_code))
    if exists:
        raise ApiError(409, "CONFLICT", DUPLICATE_NATIONAL_CODE)

    user = User(**body.model_dump(exclude={"password"}), password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two requests with the same national code at the same time
        db.rollback()
        raise ApiError(409, "CONFLICT", DUPLICATE_NATIONAL_CODE)
    db.refresh(user)
    return user


USER_NOT_FOUND = "کاربری با این شناسه یافت نشد"


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),  # login is required; who may see whom: task 3.3
    db: Session = Depends(get_db),
):
    """US3: profile of one user. UserResponse has no password hash or other sensitive field."""
    user = db.get(User, str(user_id))
    if user is None:
        raise ApiError(404, "NOT_FOUND", USER_NOT_FOUND)
    return user