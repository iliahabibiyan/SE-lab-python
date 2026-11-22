from app.dependencies import require_roles
from app.errors import ApiError
from app.models import User

ADMIN = "ADMIN"
MANAGER = "MANAGER"  # branch manager
OFFICER = "OFFICER"  # compliance officer

# Who may change the status of a user (task 5.3): the ONE place where this rule lives.
STATUS_CHANGE_ROLES = (ADMIN, MANAGER, OFFICER)

# Bank staff (task 6.3): they may act for customers, e.g. open an account for a customer.
STAFF_ROLES = (ADMIN, MANAGER, OFFICER)


def is_admin(user: User) -> bool:
    return user.role == ADMIN


def ensure_can_view_user(current_user: User, target_user_id: str) -> None:
    """Rule of US3: everybody can see his own profile; only an ADMIN can see other profiles."""
    if current_user.id != target_user_id and not is_admin(current_user):
        raise ApiError(403, "FORBIDDEN", "You are not allowed to view this profile")


def ensure_can_edit_user(current_user: User, target_user_id: str) -> None:
    """Rule of US4: everybody can edit his own profile; only an ADMIN can edit other profiles."""
    if current_user.id != target_user_id and not is_admin(current_user):
        raise ApiError(403, "FORBIDDEN", "You are not allowed to edit this profile")


require_status_manager = require_roles(*STATUS_CHANGE_ROLES)


def ensure_can_open_account(current_user: User, owner_user_id: str) -> None:
    """Rule of US6: a customer opens accounts only for himself; a staff member (ADMIN, MANAGER, OFFICER) for anybody."""
    if current_user.id != owner_user_id and current_user.role not in STAFF_ROLES:
        raise ApiError(403, "FORBIDDEN", "You are not allowed to open an account for this user")