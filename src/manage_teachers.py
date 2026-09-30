import argparse
import getpass
import json
from pathlib import Path

from src.auth import create_password_record

DEFAULT_CREDENTIALS_PATH = Path(__file__).with_name("teachers.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a teacher login")
    parser.add_argument("username", help="Teacher username")
    parser.add_argument(
        "--credentials-file",
        type=Path,
        default=DEFAULT_CREDENTIALS_PATH,
        help="Path to the teacher credentials JSON file",
    )
    args = parser.parse_args()

    username = args.username.strip()
    if not username:
        parser.error("username cannot be empty")

    password = getpass.getpass("Password (at least 12 characters): ")
    if len(password) < 12:
        parser.error("password must be at least 12 characters")
    if password != getpass.getpass("Confirm password: "):
        parser.error("passwords do not match")

    credentials = _load_credentials(args.credentials_file)
    record = create_password_record(username, password)
    credentials["teachers"] = [
        teacher
        for teacher in credentials["teachers"]
        if teacher.get("username") != username
    ]
    credentials["teachers"].append(record)

    args.credentials_file.write_text(
        json.dumps(credentials, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated credentials for {username!r} in {args.credentials_file}")


def _load_credentials(path: Path) -> dict[str, list[dict[str, object]]]:
    if not path.exists():
        return {"teachers": []}

    try:
        credentials = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Credentials file contains invalid JSON: {path}") from exc

    if not isinstance(credentials, dict) or not isinstance(
        credentials.get("teachers"), list
    ):
        raise SystemExit(f"Credentials file has an invalid structure: {path}")

    return credentials


if __name__ == "__main__":
    main()
