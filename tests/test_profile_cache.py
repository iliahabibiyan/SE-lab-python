from app.cache import TTLCache, profile_cache
from app.utils import new_id
from tests.helpers import (
    NATIONAL_CODE,
    auth_header,
    make_admin,
    register_other_user,
    register_user,
    token_for,
    update_user,
)


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


# ---------- the cache itself ----------
def test_value_expires_after_ttl():
    clock = FakeClock()
    cache = TTLCache(ttl_seconds=10, clock=clock)
    cache.set("a", {"x": 1})
    assert cache.get("a") == {"x": 1}
    clock.now += 9.9
    assert cache.get("a") == {"x": 1}
    clock.now += 0.2
    assert cache.get("a") is None


def test_delete_and_clear():
    cache = TTLCache(ttl_seconds=10)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.delete("a")
    assert cache.get("a") is None
    assert cache.get("b") == 2
    cache.clear()
    assert cache.get("b") is None


def test_ttl_zero_disables_the_cache():
    cache = TTLCache(ttl_seconds=0)
    cache.set("a", 1)
    assert cache.get("a") is None


def test_oldest_entry_is_dropped_when_full():
    cache = TTLCache(ttl_seconds=10, max_entries=2)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3


# ---------- the cache in GET /api/v1/users/{id} ----------
def test_second_read_comes_from_the_cache(client):
    user = register_user(client)
    headers = auth_header(token_for(client))
    first = client.get(f"/api/v1/users/{user['id']}", headers=headers)
    second = client.get(f"/api/v1/users/{user['id']}", headers=headers)
    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert first.json() == second.json()


def test_access_control_is_checked_even_when_the_profile_is_cached(client):
    user = register_user(client)
    register_other_user(client)
    own_headers = auth_header(token_for(client))
    assert client.get(f"/api/v1/users/{user['id']}", headers=own_headers).headers["X-Cache"] == "MISS"

    other_headers = auth_header(token_for(client, national_code="0499370899"))
    forbidden = client.get(f"/api/v1/users/{user['id']}", headers=other_headers)
    assert forbidden.status_code == 403  # the cached profile is not handed to somebody else

    make_admin("0499370899")
    allowed = client.get(f"/api/v1/users/{user['id']}", headers=other_headers)
    assert allowed.status_code == 200
    assert allowed.headers["X-Cache"] == "HIT"


def test_cached_profile_is_served_until_it_is_invalidated(client):
    user = register_user(client)
    headers = auth_header(token_for(client))
    url = f"/api/v1/users/{user['id']}"
    assert client.get(url, headers=headers).json()["name"] == "علی رضایی"

    update_user(NATIONAL_CODE, name="نام جدید")  # changed behind the cache's back
    stale = client.get(url, headers=headers)
    assert stale.headers["X-Cache"] == "HIT"
    assert stale.json()["name"] == "علی رضایی"

    profile_cache.delete(user["id"])  # what US4/US5 must do after changing a user
    fresh = client.get(url, headers=headers)
    assert fresh.headers["X-Cache"] == "MISS"
    assert fresh.json()["name"] == "نام جدید"


def test_not_found_is_not_cached(client):
    register_user(client)
    make_admin(NATIONAL_CODE)
    headers = auth_header(token_for(client))
    url = f"/api/v1/users/{new_id()}"
    for _ in range(2):
        response = client.get(url, headers=headers)
        assert response.status_code == 404
        assert "X-Cache" not in response.headers