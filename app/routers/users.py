import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.cache import profile_cache
from app.database import get_db
from app.dependencies import get_current_user
from app.errors import ApiError
from app.models import User
from app.permissions import ensure_can_edit_user, ensure_can_view_user, is_admin
from app.schemas import UserCreate, UserListResponse, UserResponse, UserStatusUpdate, UserUpdate
from app.security import hash_password
from app.validators import is_valid_national_code, normalize_digits

router = APIRouter(prefix="/api/v1/users", tags=["users"])
logger = logging.getLogger("labbank")

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


@router.get("", response_model=UserListResponse)
def search_users(
    national_code: str | None = Query(None, description="exact national code to look for"),
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, description="next_cursor of the previous page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """US3: list/search users. Cursor pagination (GEN-09): results are ordered by id."""
    query = select(User).order_by(User.id).limit(limit + 1)  # one extra row tells us if there is a next page

    if national_code is not None:
        code = normalize_digits(national_code)
        if not is_valid_national_code(code):
            raise ApiError(
                400,
                "VALIDATION_ERROR",
                "Invalid or incomplete input",
                extra={"errors": [{"field": "national_code", "message": "کد ملی نامعتبر است"}]},
            )
        query = query.where(User.national_code == code)
    if cursor:
        query = query.where(User.id > cursor)

    if not is_admin(current_user):  # a normal user can only "see" his own record
        query = query.where(User.id == current_user.id)

    rows = db.scalars(query).all()
    next_cursor = rows[limit - 1].id if len(rows) > limit else None
    items = [UserResponse.model_validate(user) for user in rows[:limit]]
    return UserListResponse(items=items, next_cursor=next_cursor)


USER_NOT_FOUND = "کاربری با این شناسه یافت نشد"


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """US3: profile of one user (own profile, or any profile for an ADMIN). No sensitive fields are returned."""
    key = str(user_id)
    ensure_can_view_user(current_user, key)  # checked on every request, also when the answer is cached

    cached = profile_cache.get(key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        return cached

    user = db.get(User, key)
    if user is None:  # "not found" is never cached
        raise ApiError(404, "NOT_FOUND", USER_NOT_FOUND)

    profile = UserResponse.model_validate(user).model_dump(mode="json")
    profile_cache.set(key, profile)
    response.headers["X-Cache"] = "MISS"
    return profile


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """US4: update the phone number, address and postal code (own profile, or any profile for an ADMIN)."""
    key = str(user_id)
    ensure_can_edit_user(current_user, key)  # before the lookup: no hint whether the id exists

    user = db.get(User, key)
    if user is None:
        raise ApiError(404, "NOT_FOUND", USER_NOT_FOUND)

    user.phone_number = body.phone_number
    user.address = body.address
    user.postal_code = body.postal_code
    db.commit()
    db.refresh(user)
    profile_cache.delete(key)  # the cached profile (task 3.5) is old now
    return user


@router.patch("/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: UUID,
    body: UserStatusUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),  # login is required; who may call it: task 5.3
    db: Session = Depends(get_db),
):
    """US5: change the status of a user (ACTIVE, INACTIVE or BLOCKED). The accounts of the user are not touched."""
    key = str(user_id)
    if key == current_user.id:  # rule: nobody changes his own status (a manager must not lock himself out)
        raise ApiError(409, "CONFLICT", "نمی‌توانید وضعیت خودتان را تغییر دهید")

    user = db.get(User, key)
    if user is None:
        raise ApiError(404, "NOT_FOUND", USER_NOT_FOUND)

    if user.status == body.status:  # nothing to change: answer 200 and do nothing else
        return user

    old_status = user.status
    user.status = body.status
    db.commit()
    db.refresh(user)
    profile_cache.delete(key)  # the cached profile (task 3.5) is old now

    logger.info(  # who changed what and why (a real audit table is a possible later task)
        json.dumps(
            {
                "level": "INFO",
                "service": "S1-ACC",
                "event": "user_status_changed",
                "user_id": key,
                "old_status": old_status,
                "new_status": user.status,
                "changed_by": current_user.id,
                "reason": body.reason,
                "correlation_id": request.state.correlation_id,
            }
        )
    )
    return user