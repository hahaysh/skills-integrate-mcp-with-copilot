import copy
import json

import pytest
from fastapi.testclient import TestClient

from src import app as app_module
from src.auth import CredentialStore, create_password_record


@pytest.fixture()
def client(tmp_path, monkeypatch):
    credentials_path = tmp_path / "teachers.json"
    credentials_path.write_text(
        json.dumps(
            {
                "teachers": [
                    create_password_record("teacher", "correct-horse-battery")
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        app_module,
        "credential_store",
        CredentialStore(credentials_path),
    )

    original_activities = copy.deepcopy(app_module.activities)
    app_module.sessions.clear()
    with TestClient(app_module.app) as test_client:
        yield test_client
    app_module.activities.clear()
    app_module.activities.update(original_activities)
    app_module.sessions.clear()


def test_activities_remain_public(client):
    response = client.get("/activities")

    assert response.status_code == 200
    assert "Chess Club" in response.json()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/activities/Chess%20Club/signup?email=new@mergington.edu"),
        (
            "delete",
            "/activities/Chess%20Club/unregister?email=michael@mergington.edu",
        ),
    ],
)
def test_activity_changes_require_teacher_login(client, method, path):
    response = getattr(client, method)(path)

    assert response.status_code == 401
    assert response.json() == {"detail": "Teacher login required"}


def test_invalid_credentials_are_rejected(client):
    response = client.post(
        "/auth/login",
        json={"username": "teacher", "password": "incorrect-password"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}


def test_teacher_can_signup_and_unregister_student(client):
    login_response = client.post(
        "/auth/login",
        json={"username": "teacher", "password": "correct-horse-battery"},
    )

    assert login_response.status_code == 200
    assert login_response.json() == {"username": "teacher"}
    assert login_response.cookies.get(app_module.SESSION_COOKIE)

    session_response = client.get("/auth/session")
    assert session_response.json() == {
        "authenticated": True,
        "username": "teacher",
    }

    signup_response = client.post(
        "/activities/Chess%20Club/signup?email=new@mergington.edu"
    )
    assert signup_response.status_code == 200
    assert "new@mergington.edu" in app_module.activities["Chess Club"]["participants"]

    unregister_response = client.delete(
        "/activities/Chess%20Club/unregister?email=new@mergington.edu"
    )
    assert unregister_response.status_code == 200
    assert "new@mergington.edu" not in app_module.activities["Chess Club"]["participants"]


def test_logout_revokes_session(client):
    client.post(
        "/auth/login",
        json={"username": "teacher", "password": "correct-horse-battery"},
    )

    response = client.post("/auth/logout")

    assert response.status_code == 200
    assert client.get("/auth/session").json() == {
        "authenticated": False,
        "username": None,
    }
    protected_response = client.post(
        "/activities/Chess%20Club/signup?email=new@mergington.edu"
    )
    assert protected_response.status_code == 401
