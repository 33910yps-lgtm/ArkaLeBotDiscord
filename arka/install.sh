#!/usr/bin/env bash
# install.sh - Install ARKA bot as a systemd service (no dedicated user)
set -e

INSTALL_DIR="$(pwd)"
echo "Installation directory: $INSTALL_DIR"

# Determine user to run service as (preserve the original invoker if sudoed)
if [ -n "$SUDO_USER" ]; then
    SERVICE_USER="$SUDO_USER"
else
    SERVICE_USER="$USER"
fi
echo "Service will run as user: $SERVICE_USER"

# Python virtual environment
VENV_DIR="$INSTALL_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r "$INSTALL_DIR/requirements.txt"

# Lavalink setup
LAVALINK_DIR="$INSTALL_DIR/lavalink"
mkdir -p "$LAVALINK_DIR"
LAVALINK_JAR="$LAVALINK_DIR/Lavalink.jar"
if [ ! -f "$LAVALINK_JAR" ]; then
    echo "Downloading Lavalink..."
    # Use a known stable version; adjust if needed
    wget -O "$LAVALINK_JAR" "https://github.com/freyacodes/Lavalink/releases/download/3.7.1/Lavalink.jar"
fi

# Write .env file with provided values
ENV_FILE="$INSTALL_DIR/.env"
cat > "$ENV_FILE" <<EOF
DISCORD_TOKEN=MTUxNTgyNDg1Mjk5OTYwMjMyNg.GlDRgo.G5u43D0KM4WBXkAAJBI1q0Qh3ffPszz1uE8tKA
LAVALINK_HOST=127.0.0.1
LAVALINK_PORT=2333
LAVALINK_PASSWORD=youshallnotpass
VRCHAT_COOKIE=
TARGET_CHANNEL_ID=1496438095703441524
VRCHAT_ROLE_ID=1496879263767330987
APPLICATION_ID=
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080
EOF
echo "Environment file written to $ENV_FILE"

# Systemd service files
ARK_SERVICE="/etc/systemd/system/arka.service"
LAVALINK_SERVICE="/etc/systemd/system/lavalink.service"

echo "Creating systemd service for ARKA bot..."
sudo tee "$ARK_SERVICE" > /dev/null <<EOF
[Unit]
Description=ARKA Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$VENV_DIR/bin/python -m arka.main
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Creating systemd service for Lavalink..."
sudo tee "$LAVALINK_SERVICE" > /dev/null <<EOF
[Unit]
Description=Lavalink Server
After=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$LAVALINK_DIR
ExecStart=/usr/bin/java -jar $LAVALINK_JAR
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd, enable and start services
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Enabling and starting services..."
sudo systemctl enable arka.service
sudo systemctl enable lavalink.service
sudo systemctl start arka.service
sudo systemctl start lavalink.service

echo "Installation complete!"
echo "You can check status with:"
echo "  sudo systemctl status arka.service"
echo "  sudo systemctl status lavalink.service"
echo "View logs with:"
echo "  journalctl -u arka.service -f"
echo "  journalctl -u lavalink.service -f"
echo "Dashboard available at http://<your-pi-ip>:8080"