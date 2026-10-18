# SSEF Web Application

A minimal Flask web application that lets you paste one Sinhala story and see the SSEF framework's scores.

## Prerequisites

The library must be installed in editable mode from the repo root:

```powershell
pip install -e "."
pip install -r app/requirements.txt
```

Fluency (SinBERT) requires a GPU and the optional extra:

```powershell
pip install -e ".[fluency]"
```

## Running locally (Windows)

From the **repo root** (not the `app/` folder):

```powershell
python app/app.py
```

Then open <http://127.0.0.1:5000> in your browser.

> **Fluency note:** The fluency checkbox will be disabled locally unless a CUDA-capable GPU is present or `SSEF_ALLOW_CPU_FLUENCY=1` is set in the environment. On a CPU the SinBERT model takes several minutes per story and is not recommended for interactive use.

## Running in development mode

```powershell
$env:FLASK_APP = "app/app.py"
flask --app app.app:create_app run --debug
```

## Running on the Linux server (production)

```bash
gunicorn --workers 1 --threads 4 --timeout 120 --bind 127.0.0.1:8000 "app.app:create_app()"
```

**One worker is required** — background fluency jobs are stored in process memory.

See `deploy/ssef.service` and `deploy/nginx_ssef.conf` for the full systemd + nginx setup.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/`  | Serve the single-page UI (redirects to `/login` if not signed in) |
| `GET`, `POST` | `/login` | Sign in to an account |
| `GET`, `POST` | `/register` | Create a new user account |
| `POST` | `/logout` | Sign out and clear session |
| `GET`  | `/privacy` | Privacy policy, English or Sinhala (public, no sign-in) |
| `POST` | `/api/evaluate` | Evaluate text (body: `{"text": "…", "fluency": false}`) |
| `GET`  | `/api/job/<id>` | Poll a background fluency job |
| `POST` | `/api/highlight` | Re-generate highlight segments for a given text |
| `GET`  | `/healthz` | Returns `ok` (public health check) |

## Environment variables

| Variable | Description |
|----------|-------------|
| `SSEF_ALLOW_CPU_FLUENCY=1` | Enable the fluency checkbox even without a GPU (slow) |
| `SSEF_LOGIN=off` | Disable authentication requirement (local development / Colab) |
| `SSEF_REGISTRATION=off` | Close new user sign-up (existing users can still sign in) |
| `SSEF_AUTH_FILE` | Path to JSON account storage (default: `instance/ssef_auth.json`) |

## Accounts

Anyone may create an account and sign in. Sign-up is open by default.

### Managing accounts from the command line

Run these commands from the repository root:

- **List accounts:**
  ```bash
  python -m app.auth list
  ```
- **Add a user:**
  ```bash
  python -m app.auth add <username>
  ```
- **Reset a user's password:**
  ```bash
  python -m app.auth reset <username>
  ```
- **Remove a user:**
  ```bash
  python -m app.auth remove <username>
  ```

Passwords are asked interactively twice via `getpass` and are never passed as command-line arguments.

### Configuration & Notes

- `SSEF_REGISTRATION=off` closes user sign-up while keeping sign-in enabled.
- `SSEF_LOGIN=off` disables login and sign-up controls completely for local development.
- The hosted application at https://generationkatha.online is served over HTTPS (nginx with a Let's Encrypt certificate). A local run on `127.0.0.1` uses plain HTTP.

### What is stored

Only usernames and password hashes in `instance/ssef_auth.json` on the server. No story text, no scores, no IP addresses are written to disk by the login feature (the in-memory limit counters are lost on restart).
