from app.dependencies import require_roles
from app.errors import ApiError
from app.models import User

ADMIN = "ADMIN"
MANAGER = "MANAGER"  # branch manager
OFFICER = "OFFICER"  # compliance officer

# Who may change the status of a user (task 5.3): the ONE place where this rule lives.
STATUS_CHANGE_ROLES = (ADMIN, MANAGER, OFFICER)


def is_admin(user: User) -> bool:
    return user.role == ADMIN


def ensure_can_view_user(current_user: User, target_user_id: str) -> None:
    """Rule of US3: everybody can see his own profile; only an ADMIN can see other profiles."""
    if current_user.id != target_user_id and not is_admin(current_user):
        raise ApiError(403, "FORBIDDEN", "شما اجازه‌ی مشاهده‌ی این پروفایل را ندارید")


def ensure_can_edit_user(current_user: User, target_user_id: str) -> None:
    """Rule of US4: everybody can edit his own profile; only an ADMIN can edit other profiles."""
    if current_user.id != target_user_id and not is_admin(current_user):
        raise ApiError(403, "FORBIDDEN", "شما اجازه‌ی ویرایش این پروفایل را ندارید")


require_status_manager = require_roles(*STATUS_CHANGE_ROLES)