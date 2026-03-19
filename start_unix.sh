#!/bin/bash
# ==============================================================================
# Description: Cross-platform deployment script for the DNS Sink0. Handles 
#              dependencies (Docker), port conflicts, and container startup.
# Version: 1.2.0
# Author: Alhasan Al-Hmondi
# ==============================================================================


echo "Initializing DNS Sink0 Deployment..."

# Check which OS we are running on to apply the correct logic
OS="$(uname -s)"
echo "[INFO] Detected Operating System: $OS"

if [ "$OS" = "Linux" ]; then
    # 1. Root privilege check
    # We need root access to free up port 53 and install packages
    if [ "$EUID" -ne 0 ]; then
      echo "[ERROR] On Linux, this script requires administrative privileges."
      echo "Action required: Please run as root (e.g., 'sudo ./start_unix.sh')."
      exit 1
    fi

    # 2. Auto-install Docker if it's missing
    # This ensures a smooth "one-click" experience for new servers
    if ! command -v docker &> /dev/null; then
        echo "[INFO] Docker is NOT installed. Installing Docker now..."
        apt-get update -y && apt-get install -y curl
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh
        echo "[SUCCESS] Docker installed successfully."
    else
        echo "[INFO] Docker is already installed."
    fi

    # 3. Handle systemd-resolved conflict
    # Modern Linux distros bind port 53 to systemd-resolved by default. We need to disable that stub listener.
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
    if ! command -v docker &> /dev/null; then
        echo "[ERROR] Docker is not installed. Please install Docker Desktop for Mac."
        exit 1
    fi
else
    echo "[WARNING] Unknown Unix OS. Proceeding with Docker deployment..."
fi

echo "------------------------------------------------------------------"
echo "[INFO] Building and provisioning the Docker container..."

# 4. Deploy the application using modern Docker Compose
docker compose up -d --build

if [ $? -eq 0 ]; then
    # Try to extract the local IP address dynamically so the user knows what to configure in their router
    if [ "$OS" = "Linux" ]; then
        LOCAL_IP=$(hostname -I | awk '{print $1}')
    elif [ "$OS" = "Darwin" ]; then
        LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1)
    else
        LOCAL_IP="<your-machine-ip>"
    fi

    echo "=================================================================="
    echo " [SUCCESS] DNS Sink0 is now active and operational! "
    echo "=================================================================="
    echo "Next Step: Configure your router's Primary DNS to point to this IP:"
    echo " "
    echo "     -->  $LOCAL_IP  <--"
    echo " "
    echo "=================================================================="
else
    echo "[ERROR] Docker deployment failed. Please review the logs above."
    exit 1
fi