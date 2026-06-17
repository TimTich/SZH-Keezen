#!/usr/bin/env bash
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
PI_USER="szh-keezen"
PI_HOST="10.100.83.251"
PI_SSH_KEY="$HOME/.ssh/id_rsa"
APP_NAME="szh-keezen"
APP_DIR="/home/szh-keezen/$APP_NAME"
PYTHON_BIN="/usr/bin/python3"
# ─────────────────────────────────────────────────────────────────────────────

SSH="ssh -i $PI_SSH_KEY -o StrictHostKeyChecking=accept-new ${PI_USER}@${PI_HOST}"
SCP="scp -i $PI_SSH_KEY"

echo "==> Deploying $APP_NAME to $PI_HOST..."

echo "==> Creating app directory..."
$SSH "mkdir -p $APP_DIR"

scp -i $PI_SSH_KEY -r ./* "${PI_USER}@${PI_HOST}:${APP_DIR}/"

echo "==> Installing dependencies..."
$SSH "pip3 install --break-system-packages -r $APP_DIR/requirements.txt"

echo "==> Creating systemd service..."
$SSH "sudo tee /etc/systemd/system/${APP_NAME}.service > /dev/null <<'EOF'
[Unit]
Description=$APP_NAME Python app
After=network.target

[Service]
Type=simple
User=$PI_USER
WorkingDirectory=$APP_DIR
ExecStart=$PYTHON_BIN $APP_DIR/main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF"

echo "==> Enabling and starting service..."
$SSH "sudo systemctl daemon-reload && \
      sudo systemctl enable $APP_NAME && \
      sudo systemctl restart $APP_NAME"

echo ""
echo "✓ Done! Service '$APP_NAME' is running on $PI_HOST"
echo ""
echo "  Useful commands:"
echo "    Status : ssh ${PI_USER}@${PI_HOST} 'sudo systemctl status $APP_NAME'"
echo "    Logs   : ssh ${PI_USER}@${PI_HOST} 'journalctl -u $APP_NAME -f'"
echo "    Restart: ssh ${PI_USER}@${PI_HOST} 'sudo systemctl restart $APP_NAME'"