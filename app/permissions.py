from app.errors import ApiError
from app.models import User

ADMIN = "ADMIN"


def is_admin(user: User) -> bool:
    return user.role == ADMIN


def ensure_can_view_user(current_user: User, target_user_id: str) -> None:
    """Rule of US3: everybody can see his own profile; only an ADMIN can see other profiles."""
    if current_user.id != target_user_id and not is_admin(current_user):
        raise ApiError(403, "FORBIDDEN", "شما اجازه‌ی مشاهده‌ی این پروفایل را ندارید")