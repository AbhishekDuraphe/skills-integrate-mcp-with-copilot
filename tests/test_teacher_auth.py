import asyncio
import hashlib
import json
import tempfile
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from urllib.parse import quote, urlencode
from unittest.mock import patch

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import app as activities_app


class TeacherAuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.credentials_path = Path(self.temp_dir.name) / "teachers.json"
        salt = b"test-salt-for-auth"
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", b"correct horse battery staple", salt, 100_000
        )
        self.credentials_path.write_text(
            json.dumps(
                {
                    "teachers": [
                        {
                            "username": "teacher1",
                            "password_hash": (
                                f"pbkdf2_sha256$100000${salt.hex()}${password_hash.hex()}"
                            ),
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        self.credentials_patch = patch.object(
            activities_app, "TEACHERS_FILE", self.credentials_path
        )
        self.credentials_patch.start()
        activities_app.teacher_sessions.clear()
        self.cookies = {}

    def tearDown(self):
        activities_app.teacher_sessions.clear()
        self.credentials_patch.stop()
        self.temp_dir.cleanup()

    def request(self, method, path, params=None, json_data=None):
        query_string = urlencode(params or {}).encode("utf-8")
        body = json.dumps(json_data).encode("utf-8") if json_data is not None else b""
        headers = [(b"host", b"testserver")]
        if body:
            headers.append((b"content-type", b"application/json"))
        if self.cookies:
            cookie_header = "; ".join(
                f"{name}={value}" for name, value in self.cookies.items()
            )
            headers.append((b"cookie", cookie_header.encode("latin-1")))

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": quote(path, safe="/%:@!$&'()*+,;=-._~").encode("ascii"),
            "query_string": query_string,
            "headers": headers,
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "root_path": "",
        }
        messages = []
        request_sent = False

        async def receive():
            nonlocal request_sent
            if request_sent:
                return {"type": "http.disconnect"}
            request_sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        asyncio.run(activities_app.app(scope, receive, send))
        response_start = next(message for message in messages if message["type"] == "http.response.start")
        response_body = b"".join(
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        )
        response_headers = dict(response_start["headers"])
        set_cookie = response_headers.get(b"set-cookie")
        if set_cookie:
            parsed_cookie = SimpleCookie()
            parsed_cookie.load(set_cookie.decode("latin-1"))
            for name, morsel in parsed_cookie.items():
                if morsel["max-age"] == "0" or not morsel.value:
                    self.cookies.pop(name, None)
                else:
                    self.cookies[name] = morsel.value
        return response_start["status"], json.loads(response_body)

    def test_activity_list_is_public(self):
        status, response = self.request("GET", "/activities")

        self.assertEqual(status, 200)
        self.assertIn("Chess Club", response)

    def test_anonymous_users_cannot_change_activity_rosters(self):
        status, _ = self.request(
            "POST", "/activities/Chess Club/signup", params={"email": "new@mergington.edu"}
        )

        self.assertEqual(status, 401)
        self.assertNotIn("new@mergington.edu", activities_app.activities["Chess Club"]["participants"])

        status, _ = self.request(
            "DELETE",
            "/activities/Chess Club/unregister",
            params={"email": "michael@mergington.edu"},
        )

        self.assertEqual(status, 401)
        self.assertIn("michael@mergington.edu", activities_app.activities["Chess Club"]["participants"])

    def test_teacher_can_login_and_change_rosters(self):
        login_status, login_response = self.request(
            "POST", "/auth/login",
            json_data={"username": "teacher1", "password": "correct horse battery staple"},
        )

        self.assertEqual(login_status, 200)
        self.assertTrue(login_response["authenticated"])
        self.assertTrue(self.cookies.get("teacher_session"))

        signup_status, _ = self.request(
            "POST", "/activities/Chess Club/signup", params={"email": "new@mergington.edu"}
        )
        self.assertEqual(signup_status, 200)

        unregister_status, _ = self.request(
            "DELETE",
            "/activities/Chess Club/unregister",
            params={"email": "new@mergington.edu"},
        )
        self.assertEqual(unregister_status, 200)

        logout_status, _ = self.request("POST", "/auth/logout")
        self.assertEqual(logout_status, 200)
        denied_status, _ = self.request(
            "POST", "/activities/Chess Club/signup", params={"email": "new@mergington.edu"}
        )
        self.assertEqual(denied_status, 401)

    def test_invalid_credentials_are_rejected(self):
        status, _ = self.request(
            "POST", "/auth/login", json_data={"username": "teacher1", "password": "wrong"}
        )

        self.assertEqual(status, 401)
        self.assertFalse(self.cookies.get("teacher_session"))


if __name__ == "__main__":
    unittest.main()
