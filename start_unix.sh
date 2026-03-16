#!/bin/bash

# ==============================================================================
# Cross-Platform Deployment Script (Linux & macOS)
# ==============================================================================

echo "Initializing DNS Sinkhole Deployment..."

# Check OS type
OS="$(uname -s)"
echo "[INFO] Detected Operating System: $OS"

if [ "$OS" = "Linux" ]; then
    if [ "$EUID" -ne 0 ]; then
      echo "[ERROR] On Linux, this script requires administrative privileges."
      echo "Action required: Please run as root (e.g., 'sudo ./start_unix.sh')."
      exit 1
    fi

    if systemctl is-active --quiet systemd-resolved 2>/dev/null; then
        echo "[INFO] 'systemd-resolved' is active. Reconfiguring to release port 53..."
        cp /etc/systemd/resolved.conf /etc/systemd/resolved.conf.bak
        sed -i 's/#DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf
        sed -i 's/DNSStubListener=yes/DNSStubListener=no/' /etc/systemd/resolved.conf
        rm -f /etc/resolv.conf
        ln -s /run/systemd/resolve/resolv.conf /etc/resolv.conf
        systemctl restart systemd-resolved
        echo "[SUCCESS] Port 53 has been successfully released."
    fi

elif [ "$OS" = "Darwin" ]; then
    echo "[INFO] macOS detected. Skipping Linux-specific port checks."
else
    echo "[WARNING] Unknown Unix OS. Proceeding with Docker deployment..."
fi

echo "------------------------------------------------------------------"
echo "[INFO] Building and provisioning the Docker container..."

docker compose up -d --build

if [ $? -eq 0 ]; then
    echo "=================================================================="
    echo " [SUCCESS] DNS Sinkhole is now active and operational! "
    echo "=================================================================="
    echo "Next Step: Configure your router's Primary DNS to point to this machine's IP address."
else
    echo "[ERROR] Docker deployment failed. Please review the logs above."
    exit 1
fi