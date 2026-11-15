from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import db, main
from backend.config import settings
from backend.email_service import reset_code_digest
from starlette.responses import Response


class PasswordResetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database_path = settings.database_path
        object.__setattr__(
            settings, "database_path", Path(self.temp_dir.name) / "test.db"
        )
        db.initialize_database()
        self.user = db.create_user("judge@example.com", "old-password", "评委")
        main.auth_attempts.clear()

    def tearDown(self) -> None:
        object.__setattr__(settings, "database_path", self.original_database_path)
        self.temp_dir.cleanup()

    def test_reset_code_is_one_time_and_revokes_sessions(self) -> None:
        session = db.create_session(self.user["id"])
        code = "123456"
        digest = reset_code_digest(self.user["email"], code)
        issued = db.issue_password_reset_code(self.user["id"], digest)
        self.assertTrue(issued["ok"])

        wrong = db.reset_password_with_code(
            self.user["email"],
            reset_code_digest(self.user["email"], "000000"),
            "new-password",
        )
        self.assertFalse(wrong["ok"])
        self.assertEqual(wrong["error"], "invalid_code")

        reset = db.reset_password_with_code(
            self.user["email"], digest, "new-password"
        )
        self.assertTrue(reset["ok"])
        self.assertIsNone(db.get_user_by_session(session))
        self.assertIsNone(db.authenticate(self.user["email"], "old-password"))
        self.assertIsNotNone(db.authenticate(self.user["email"], "new-password"))

        reused = db.reset_password_with_code(
            self.user["email"], digest, "another-password"
        )
        self.assertFalse(reused["ok"])

    def test_registration_reset_and_report_email_api_flow(self) -> None:
        captured: dict[str, str] = {}

        def capture_reset_code(
            user: dict[str, str], code: str, expires_minutes: int
        ) -> None:
            captured["email"] = user["email"]
            captured["code"] = code

        with (
            patch("backend.main.email_configured", return_value=True),
            patch("backend.main.send_registration_email") as registration_email,
            patch(
                "backend.main.send_password_reset_email",
                side_effect=capture_reset_code,
            ),
            patch("backend.main.send_health_report_email") as report_email,
        ):
            response = main.register(
                main.RegisterRequest(
                    name="体验用户",
                    email="visitor@example.com",
                    password="initial-password",
                ),
                Response(),
            )
            self.assertEqual(response["registration_email"]["status"], "sent")
            registration_email.assert_called_once()

            request = main.request_password_reset(
                main.PasswordResetRequest(email="visitor@example.com")
            )
            self.assertTrue(request["ok"])
            self.assertEqual(captured["email"], "visitor@example.com")
            self.assertRegex(captured["code"], r"^\d{6}$")

            reset = main.confirm_password_reset(
                main.PasswordResetConfirmRequest(
                    email="visitor@example.com",
                    code=captured["code"],
                    new_password="reset-password",
                )
            )
            self.assertTrue(reset["ok"])
            self.assertIsNotNone(
                db.authenticate("visitor@example.com", "reset-password")
            )

            login = main.login(
                main.LoginRequest(
                    email="visitor@example.com",
                    password="reset-password",
                ),
                Response(),
            )
            self.assertEqual(login["user"]["email"], "visitor@example.com")
            visitor = db.get_user_by_email("visitor@example.com")
            assert visitor is not None
            report = main.email_health_report(
                main.EmailReportRequest(report_type="visit_summary"),
                user=visitor,
            )
            self.assertEqual(report["report_type"], "visit_summary")
            report_email.assert_called_once()


if __name__ == "__main__":
    unittest.main()
