"""认证接口测试：注册 / 登录 / 当前用户 / 错误路径。"""

from __future__ import annotations


def test_register_and_login(client):
    resp = client.post(
        "/api/auth/register",
        json={"username": "user1", "password": "secret123"},
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "user1"

    resp = client.post(
        "/api/auth/login",
        json={"username": "user1", "password": "secret123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


def test_register_duplicate(client):
    payload = {"username": "dup", "password": "secret123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409


def test_login_wrong_password(client):
    client.post(
        "/api/auth/register", json={"username": "bad", "password": "secret123"}
    )
    resp = client.post(
        "/api/auth/login", json={"username": "bad", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post(
        "/api/auth/login", json={"username": "nobody", "password": "x"}
    )
    assert resp.status_code == 401


def test_weak_password_rejected(client):
    resp = client.post(
        "/api/auth/register", json={"username": "weak", "password": "123"}
    )
    assert resp.status_code == 422


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_token(client, auth_headers):
    headers = auth_headers("meuser")
    resp = client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "meuser"
