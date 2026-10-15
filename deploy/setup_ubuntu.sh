#!/usr/bin/env bash
# deploy/setup_ubuntu.sh — Idempotent server setup for SSEF
# Run as a user with sudo access from the repo root.
# The NVIDIA driver must already be installed before running this script.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$REPO_DIR/.venv"
SERVICE_NAME="ssef"
NGINX_CONF="/etc/nginx/sites-available/ssef"
NGINX_ENABLED="/etc/nginx/sites-enabled/ssef"
NGINX_DEFAULT="/etc/nginx/sites-enabled/default"

echo "=== SSEF setup: repo at $REPO_DIR ==="

# ── 1. System packages ──────────────────────────────────────────────────
echo "--- Installing system packages ---"
sudo apt-get update -qq
sudo apt-get install -y python3-venv python3-pip nginx git

# ── 2. Python virtual environment ──────────────────────────────────────
echo "--- Creating/updating virtual environment ---"
if [ ! -d "$VENV" ]; then
    python3 -m venv "$VENV"
fi

"$VENV/bin/pip" install --upgrade pip --quiet

# Install the library with the fluency optional extra (GPU instance)
"$VENV/bin/pip" install -e "$REPO_DIR[fluency]" --quiet

# Install Flask and gunicorn
"$VENV/bin/pip" install -r "$REPO_DIR/app/requirements.txt" --quiet

# ── 3. Pre-download SinBERT model ───────────────────────────────────────
echo "--- Pre-downloading SinBERT model (this may take a few minutes) ---"
"$VENV/bin/python" - <<'EOF'
from sinhala_story_eval.metrics.fluency import load_model
load_model()
print("SinBERT model loaded successfully.")
EOF

# ── 4. CUDA availability check ──────────────────────────────────────────
echo "--- CUDA check ---"
"$VENV/bin/python" -c "import torch; print('torch.cuda.is_available():', torch.cuda.is_available())"

# ── 5. systemd service ──────────────────────────────────────────────────
echo "--- Installing systemd service ---"
sudo cp "$REPO_DIR/deploy/ssef.service" "/etc/systemd/system/${SERVICE_NAME}.service"
# Patch WorkingDirectory to actual path
sudo sed -i "s|WorkingDirectory=.*|WorkingDirectory=$REPO_DIR|" "/etc/systemd/system/${SERVICE_NAME}.service"
# Patch ExecStart to use the actual venv
sudo sed -i "s|ExecStart=.*/.venv/|ExecStart=$VENV/|" "/etc/systemd/system/${SERVICE_NAME}.service"

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

# ── 6. nginx ────────────────────────────────────────────────────────────
echo "--- Configuring nginx ---"
sudo cp "$REPO_DIR/deploy/nginx_ssef.conf" "$NGINX_CONF"
sudo ln -sf "$NGINX_CONF" "$NGINX_ENABLED"

# Remove the default site if it exists
if [ -L "$NGINX_DEFAULT" ]; then
    sudo rm -f "$NGINX_DEFAULT"
    echo "Removed nginx default site."
fi

sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

# ── 7. Health check ─────────────────────────────────────────────────────
echo "--- Health check ---"
sleep 3
curl -s localhost/healthz

echo ""
# ── 8. Accounts summary ────────────────────────────────────────────────
"$VENV/bin/python" - <<EOF
import os
try:
    from app.auth import get_auth_path, load_auth
    auth = load_auth(get_auth_path())
    count = len(auth.get("users", {})) if auth else 0
except Exception:
    count = 0
print(f"Accounts: {count} (manage with: cd $REPO_DIR && .venv/bin/python -m app.auth list|add|reset|remove)")
EOF

echo ""
echo "=== Setup complete ==="
