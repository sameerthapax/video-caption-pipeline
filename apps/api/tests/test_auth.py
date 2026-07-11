from types import SimpleNamespace

from app.core.database import SessionLocal
from app.core.auth import ACCESS_TOKEN_COOKIE, CSRF_COOKIE, CSRF_HEADER, REFRESH_TOKEN_COOKIE
from app.models.job import VideoJob
//

def test_signup_sets_auth_cookies(client, monkeypatch):
    def fake_sign_up_with_password(*, email: str, password: str):
        return SimpleNamespace(
            access_token="access-token",
            refresh_token="refresh-token",
            user=SimpleNamespace(id="user-id", email=email),
        )

    monkeypatch.setattr("app.controllers.auth_controller.sign_up_with_password", fake_sign_up_with_password)
    client.app.dependency_overrides.clear()

    response = client.post("/api/auth/signup/", json={"email": "person@example.com", "password": "secret123"})

    assert response.status_code == 201
    assert response.json()["user"]["email"] == "person@example.com"
    assert ACCESS_TOKEN_COOKIE in response.cookies
    assert CSRF_COOKIE in response.cookies
    assert REFRESH_TOKEN_COOKIE in response.cookies


def test_login_sets_auth_cookies(client, monkeypatch):
    def fake_sign_in_with_password(*, email: str, password: str):
        return SimpleNamespace(
            access_token="access-token",
            refresh_token="refresh-token",
            user=SimpleNamespace(id="user-id", email=email),
        )

    monkeypatch.setattr("app.controllers.auth_controller.sign_in_with_password", fake_sign_in_with_password)
    client.app.dependency_overrides.clear()

    response = client.post("/api/auth/login/", json={"email": "person@example.com", "password": "secret123"})

    assert response.status_code == 200
    assert response.json()["user"]["id"] == "user-id"
    assert ACCESS_TOKEN_COOKIE in response.cookies
    assert CSRF_COOKIE in response.cookies
    assert REFRESH_TOKEN_COOKIE in response.cookies


def test_session_returns_current_user(client):
    response = client.get("/api/auth/session/")

    assert response.status_code == 200
    assert response.json()["user"]["id"] == "test-user-id"
    assert CSRF_COOKIE in response.cookies


def test_logout_clears_auth_cookies(client, monkeypatch):
    called = {"logout": False}

    def fake_sign_out_session(*, access_token: str):
        called["logout"] = access_token == "access-token"

    monkeypatch.setattr("app.controllers.auth_controller.sign_out_session", fake_sign_out_session)
    client.app.dependency_overrides.clear()
    client.cookies.set(ACCESS_TOKEN_COOKIE, "access-token")
    client.cookies.set(REFRESH_TOKEN_COOKIE, "refresh-token")
    client.cookies.set(CSRF_COOKIE, "csrf-token")

    response = client.post("/api/auth/logout/", headers={CSRF_HEADER: "csrf-token"})

    assert response.status_code == 204
    assert called["logout"] is True


def test_logout_requires_csrf_header(client):
    client.app.dependency_overrides.clear()
    client.cookies.set(ACCESS_TOKEN_COOKIE, "access-token")
    client.cookies.set(REFRESH_TOKEN_COOKIE, "refresh-token")
    client.cookies.set(CSRF_COOKIE, "csrf-token")

    response = client.post("/api/auth/logout/")

    assert response.status_code == 403


def test_profile_returns_job_summary(client):
    db = SessionLocal()
    db.add_all(
        [
            VideoJob(
                user_id="test-user-id",
                original_filename="finished.mp4",
                storage_bucket="videos",
                video_path="videos/finished.mp4",
                upload_content_type="video/mp4",
                upload_file_size=1234,
                status="completed",
                current_step="completed",
                progress=100,
            ),
            VideoJob(
                user_id="test-user-id",
                original_filename="processing.mp4",
                storage_bucket="videos",
                video_path="videos/processing.mp4",
                upload_content_type="video/mp4",
                upload_file_size=4321,
                status="processing",
                current_step="processing_segment_2",
                progress=48,
            ),
        ]
    )
    db.commit()
    db.close()

    response = client.get("/api/auth/profile/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["id"] == "test-user-id"
    assert payload["total_jobs"] == 2
    assert payload["completed_jobs"] == 1
    assert payload["active_jobs"] == 1
