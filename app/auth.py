# -*- coding: utf-8 -*-
"""
app/auth.py — Account storage, authentication, and admin CLI for SSEF.

Format of instance/ssef_auth.json:
{
    "secret_key": "<random hex>",
    "users": {
        "<username_lowercase>": "<werkzeug hash>"
    }
}
"""

import getpass
import json
import os
import re
import secrets
import sys
import tempfile
import threading
from werkzeug.security import check_password_hash, generate_password_hash

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_lock = threading.Lock()

_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,30}$")


def get_auth_path(path: str | None = None) -> str:
    """Return the resolved auth file path."""
    if path:
        return os.path.abspath(path)
    env_path = os.environ.get("SSEF_AUTH_FILE")
    if env_path:
        return os.path.abspath(env_path)
    return os.path.join(_REPO_ROOT, "instance", "ssef_auth.json")


def validate_credentials(username: str, password: str) -> tuple[bool, str | None]:
    """Validate username and password format.

    Rules:
      - Username: 3-30 characters from [A-Za-z0-9_]
      - Password: at least 8 characters

    Returns:
      (True, None) if valid.
      (False, 'register.invalid_username') if username is invalid.
      (False, 'register.short_password') if password is too short.
    """
    if not username or not _USERNAME_PATTERN.match(username):
        return False, "register.invalid_username"
    if not password or len(password) < 8:
        return False, "register.short_password"
    return True, None


def _write_auth_file_atomic(path: str, data: dict) -> None:
    """Write data to path atomically using a temp file and os.replace."""
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", dir=folder, delete=False, encoding="utf-8") as tf:
        tmp_name = tf.name
        json.dump(data, tf, indent=2, ensure_ascii=False)
        tf.flush()
        os.fsync(tf.fileno())

    # On Linux set the file mode to 600
    if hasattr(os, "chmod") and sys.platform != "win32":
        try:
            os.chmod(tmp_name, 0o600)
        except OSError:
            pass

    os.replace(tmp_name, path)

    if hasattr(os, "chmod") and sys.platform != "win32":
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def load_auth(path: str | None = None) -> dict | None:
    """Load auth data from JSON file. Returns None if file does not exist."""
    file_path = get_auth_path(path)
    with _lock:
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None


def get_secret_key(path: str | None = None) -> str:
    """Get secret key, creating the auth file with only a secret key if missing."""
    file_path = get_auth_path(path)
    with _lock:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
            if "secret_key" in data and data["secret_key"]:
                return data["secret_key"]
        else:
            data = {"users": {}}

        key = secrets.token_hex(32)
        data["secret_key"] = key
        if "users" not in data:
            data["users"] = {}
        _write_auth_file_atomic(file_path, data)
        return key


def add_user(path: str | None, username: str, password: str) -> None:
    """Create or overwrite a user in the auth file.

    Creates the file and folder if missing, generates secret_key with
    secrets.token_hex(32) if missing, hashes with werkzeug.security.generate_password_hash.
    """
    file_path = get_auth_path(path)
    uname = username.strip().lower()
    hashed = generate_password_hash(password)

    with _lock:
        data = None
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = None

        if data is None or not isinstance(data, dict):
            data = {"secret_key": secrets.token_hex(32), "users": {}}

        if "secret_key" not in data or not data["secret_key"]:
            data["secret_key"] = secrets.token_hex(32)
        if "users" not in data or not isinstance(data["users"], dict):
            data["users"] = {}

        data["users"][uname] = hashed
        _write_auth_file_atomic(file_path, data)


def create_user(path: str | None, username: str, password: str) -> bool:
    """Like add_user but returns False (and changes nothing) if the username already exists.

    Used by sign-up.
    """
    file_path = get_auth_path(path)
    uname = username.strip().lower()

    with _lock:
        data = None
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = None

        if data is None or not isinstance(data, dict):
            data = {"secret_key": secrets.token_hex(32), "users": {}}

        if "secret_key" not in data or not data["secret_key"]:
            data["secret_key"] = secrets.token_hex(32)
        if "users" not in data or not isinstance(data["users"], dict):
            data["users"] = {}

        if uname in data["users"]:
            return False

        data["users"][uname] = generate_password_hash(password)
        _write_auth_file_atomic(file_path, data)
        return True


def remove_user(path: str | None, username: str) -> None:
    """Remove a user from the auth file."""
    file_path = get_auth_path(path)
    uname = username.strip().lower()

    with _lock:
        if not os.path.exists(file_path):
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        if isinstance(data, dict) and "users" in data and uname in data["users"]:
            del data["users"][uname]
            _write_auth_file_atomic(file_path, data)


def check_user(path: str | None, username: str, password: str) -> bool:
    """Check credentials against the auth file."""
    file_path = get_auth_path(path)
    uname = username.strip().lower()

    with _lock:
        if not os.path.exists(file_path):
            return False
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return False

        if not isinstance(data, dict) or "users" not in data:
            return False
        stored_hash = data["users"].get(uname)
        if not stored_hash:
            return False

    return check_password_hash(stored_hash, password)


# ---------------------------------------------------------------------------
# Admin CLI
# ---------------------------------------------------------------------------
def _ask_password(prompt: str = "Password: ") -> str:
    pw1 = getpass.getpass(prompt)
    pw2 = getpass.getpass("Confirm password: ")
    if pw1 != pw2:
        print("Error: The passwords do not match.")
        sys.exit(1)
    return pw1


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        print("Usage: python -m app.auth [add|reset|remove|list] [username]")
        sys.exit(1)

    cmd = argv[0].lower()
    auth_path = get_auth_path()

    if cmd == "list":
        auth = load_auth(auth_path)
        users = sorted(auth.get("users", {}).keys()) if auth else []
        print(f"Accounts: {len(users)}")
        for u in users:
            print(f"  {u}")

    elif cmd == "add":
        if len(argv) < 2:
            print("Usage: python -m app.auth add <username>")
            sys.exit(1)
        username = argv[1].strip()
        ok, err = validate_credentials(username, "placeholder_for_len")
        if not ok and err == "register.invalid_username":
            print("Error: Use 3–30 letters, numbers or _.")
            sys.exit(1)
        pw = _ask_password("Password: ")
        ok, err = validate_credentials(username, pw)
        if not ok:
            if err == "register.short_password":
                print("Error: The password must be at least 8 characters.")
            else:
                print("Error: Invalid credentials.")
            sys.exit(1)
        add_user(auth_path, username, pw)
        print(f"User '{username.lower()}' added successfully.")

    elif cmd == "reset":
        if len(argv) < 2:
            print("Usage: python -m app.auth reset <username>")
            sys.exit(1)
        username = argv[1].strip().lower()
        auth = load_auth(auth_path)
        if not auth or username not in auth.get("users", {}):
            print(f"Error: User '{username}' does not exist.")
            sys.exit(1)
        pw = _ask_password("New password: ")
        if len(pw) < 8:
            print("Error: The password must be at least 8 characters.")
            sys.exit(1)
        add_user(auth_path, username, pw)
        print(f"Password for user '{username}' reset successfully.")

    elif cmd == "remove":
        if len(argv) < 2:
            print("Usage: python -m app.auth remove <username>")
            sys.exit(1)
        username = argv[1].strip().lower()
        remove_user(auth_path, username)
        print(f"User '{username}' removed.")

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python -m app.auth [add|reset|remove|list] [username]")
        sys.exit(1)


if __name__ == "__main__":
    main()
