#!/bin/bash

# ==============================================================================
# Cross-Platform Deployment Script (Linux & macOS)
# ==============================================================================

echo "Initializing DNS Sinkhole Deployment..."

# Check OS type
OS="$(uname -s)"
echo "[INFO] Detected Operating System: $OS"

if [ "$OS" = "Linux" ]; then
    # 1. Check for root privileges
    if [ "$EUID" -ne 0 ]; then
      echo "[ERROR] On Linux, this script requires administrative privileges."
      echo "Action required: Please run as root (e.g., 'sudo ./start_unix.sh')."
      exit 1
    fi

    # 2. AUTO-INSTALL DOCKER (NEW!)
    if ! command -v docker &> /dev/null; then
        echo "[INFO] Docker is NOT installed. Installing Docker now..."
        # Install curl if it's missing (needed to download Docker)
        apt-get update -y && apt-get install -y curl
        # Download and run Docker's official installation script
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh
        echo "[SUCCESS] Docker installed successfully."
    else
        echo "[INFO] Docker is already installed."
    fi

    # 3. Handle systemd-resolved conflict (Port 53)
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

# 4. Deploy the application
# Using "docker compose" (modern v2 standard)
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