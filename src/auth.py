import hashlib
import hmac
import json
import secrets
from pathlib import Path

PBKDF2_ITERATIONS = 600_000


def create_password_record(username: str, password: str) -> dict[str, str | int]:
    salt = secrets.token_bytes(32)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return {
        "username": username,
        "salt": salt.hex(),
        "password_hash": password_hash.hex(),
        "iterations": PBKDF2_ITERATIONS,
    }


class CredentialStore:
    def __init__(self, path: Path):
        self.path = path

    def verify(self, username: str, password: str) -> bool:
        for teacher in self._load():
            if teacher["username"] != username:
                continue

            candidate_hash = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(teacher["salt"]),
                teacher["iterations"],
            )
            return hmac.compare_digest(
                candidate_hash.hex(),
                teacher["password_hash"],
            )

        return False

    def _load(self) -> list[dict[str, str | int]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            teachers = data["teachers"]
        except FileNotFoundError as exc:
            raise RuntimeError(
                f"Teacher credentials file not found: {self.path}"
            ) from exc
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise RuntimeError(
                f"Teacher credentials file is invalid: {self.path}"
            ) from exc

        if not isinstance(teachers, list):
            raise RuntimeError(
                f"Teacher credentials file is invalid: {self.path}"
            )

        required_fields = {"username", "salt", "password_hash", "iterations"}
        for teacher in teachers:
            if not isinstance(teacher, dict) or not required_fields.issubset(teacher):
                raise RuntimeError(
                    f"Teacher credentials file is invalid: {self.path}"
                )

        return teachers
