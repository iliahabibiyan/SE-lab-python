from app.tokens import decode_token
from tests.helpers import (
    NATIONAL_CODE,
    OTHER_NATIONAL_CODE,
    PASSWORD,
    auth_header,
    login,
    make_admin,
    register_other_user,
    register_user,
    token_for,
)


def admin_and_victim(client):
    """An ADMIN (default user) and a normal user who is logged in; returns (admin_headers, victim, victim_tokens)."""
    register_user(client)
    victim = register_other_user(client)
    make_admin(NATIONAL_CODE)
    admin_headers = auth_header(token_for(client))
    victim_tokens = login(client, national_code=OTHER_NATIONAL_CODE).json()
    return admin_headers, victim, victim_tokens


def set_status(client, headers, user_id, status):
    return client.patch(f"/api/v1/users/{user_id}/status", json={"status": status}, headers=headers)


def test_tokens_carry_the_token_version(client):
    admin_and_victim(client)
    tokens = login(client, national_code=OTHER_NATIONAL_CODE).json()
    assert decode_token(tokens["access_token"])["ver"] == 0
    assert decode_token(tokens["refresh_token"], "refresh")["ver"] == 0


def test_blocking_revokes_access_and_refresh_tokens(client):
    admin_headers, victim, tokens = admin_and_victim(client)
    assert client.get("/api/v1/auth/me", headers=auth_header(tokens["access_token"])).status_code == 200

    assert set_status(client, admin_headers, victim["id"], "BLOCKED").status_code == 200

    me = client.get("/api/v1/auth/me", headers=auth_header(tokens["access_token"]))
    assert me.status_code == 401
    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 401


def test_deactivating_also_revokes_the_tokens(client):
    admin_headers, victim, tokens = admin_and_victim(client)
    assert set_status(client, admin_headers, victim["id"], "INACTIVE").status_code == 200
    assert client.get("/api/v1/auth/me", headers=auth_header(tokens["access_token"])).status_code == 401


def test_old_tokens_stay_dead_after_the_user_is_activated_again(client):
    admin_headers, victim, old_tokens = admin_and_victim(client)
    set_status(client, admin_headers, victim["id"], "BLOCKED")
    set_status(client, admin_headers, victim["id"], "ACTIVE")

    assert client.get("/api/v1/auth/me", headers=auth_header(old_tokens["access_token"])).status_code == 401
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": old_tokens["refresh_token"]}).status_code == 401

    new_tokens = login(client, national_code=OTHER_NATIONAL_CODE, password=PASSWORD)  # a new login works
    assert new_tokens.status_code == 200
    assert decode_token(new_tokens.json()["access_token"])["ver"] == 1  # blocked once: version 1 (activating keeps it)
    assert client.get("/api/v1/auth/me", headers=auth_header(new_tokens.json()["access_token"])).status_code == 200


def test_activating_does_not_revoke_anything(client):
    admin_headers, victim, tokens = admin_and_victim(client)
    assert set_status(client, admin_headers, victim["id"], "ACTIVE").status_code == 200  # already ACTIVE
    assert client.get("/api/v1/auth/me", headers=auth_header(tokens["access_token"])).status_code == 200


def test_tokens_of_other_users_are_not_revoked(client):
    admin_headers, victim, _ = admin_and_victim(client)
    set_status(client, admin_headers, victim["id"], "BLOCKED")
    assert client.get("/api/v1/auth/me", headers=admin_headers).status_code == 200
