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
| `GET`  | `/`  | Serve the single-page UI |
| `POST` | `/api/evaluate` | Evaluate text (body: `{"text": "…", "fluency": false}`) |
| `GET`  | `/api/job/<id>` | Poll a background fluency job |
| `POST` | `/api/highlight` | Re-generate highlight segments for a given text |
| `GET`  | `/healthz` | Returns `ok` |

## Environment variables

| Variable | Description |
|----------|-------------|
| `SSEF_ALLOW_CPU_FLUENCY=1` | Enable the fluency checkbox even without a GPU (slow) |
