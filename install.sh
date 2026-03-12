#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/speaker-control.service"

echo "==> Installing dependencies..."
cd "$SCRIPT_DIR"
uv sync

echo "==> Creating systemd user service..."
mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Auto Speaker Control (Tapo smart plug)
After=pipewire.service network-online.target
Requires=pipewire.service
Wants=network-online.target
Conflicts=sleep.target

[Service]
Type=simple
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/.venv/bin/python speaker_control.py
Restart=on-failure
RestartSec=10
TimeoutStopSec=30

[Install]
WantedBy=default.target
EOF

echo "==> Reloading systemd..."
systemctl --user daemon-reload

echo "==> Enabling and starting speaker-control service..."
systemctl --user enable --now speaker-control.service

echo "==> Done! Check status with: systemctl --user status speaker-control"
