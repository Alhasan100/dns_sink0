@echo off
SETLOCAL EnableDelayedExpansion

:: ==============================================================================
:: Windows Deployment Script with Auto-Install
:: ==============================================================================

echo Initializing DNS Sinkhole Deployment for Windows...
echo.

:: 1. Check for Administrative privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script requires administrative privileges.
    echo Action required: Right-click 'start_windows.bat' and select 'Run as administrator'.
    pause
    exit /b 1
)

:: 2. AUTO-INSTALL DOCKER (NEW!)
docker --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Docker is NOT installed. Downloading Docker Desktop...
    echo This might take a few minutes depending on your internet connection.
    :: Använder inbyggda curl för att hämta installationsfilen
    curl -L -o DockerInstaller.exe "https://desktop.docker.com/win/main/amd64/Docker%%20Desktop%%20Installer.exe"
    
    echo [INFO] Running Docker installation quietly...
    start /wait "" DockerInstaller.exe install --quiet
    del DockerInstaller.exe
    
    echo.
    echo ==================================================================
    echo [ATTENTION] Docker Desktop has been installed!
    echo ==================================================================
    echo Windows requires Docker Desktop to initialize properly.
    echo 1. Open 'Docker Desktop' from your Windows Start menu.
    echo 2. Accept the terms and let it start up.
    echo 3. IF Windows asks you to restart your computer, do so.
    echo.
    echo After Docker is running, run this script (start_windows.bat) again!
    echo ==================================================================
    pause
    exit /b 0
) else (
    echo [INFO] Docker is already installed.
)

:: 3. Check if Port 53 is already in use by Windows
echo [INFO] Checking if port 53 is available...
netstat -ano | findstr :53 >nul
if %errorLevel% equ 0 (
    echo [WARNING] Port 53 appears to be in use by another Windows service.
    echo [WARNING] Docker might fail to start if the port is completely blocked.
) else (
    echo [INFO] Port 53 appears to be free.
)

echo.
echo [INFO] Building and provisioning the Docker container...
echo ------------------------------------------------------------------

:: 4. Deploy using Docker Compose
docker compose up -d --build

if %errorLevel% equ 0 (
    echo.
    echo ==================================================================
    echo  [SUCCESS] DNS Sinkhole is now active and operational! 
    echo ==================================================================
    echo Next Step: Configure your router's Primary DNS to point to this machine's IP address.
) else (
    echo.
    echo [ERROR] Docker deployment failed. Is Docker Desktop running?
)

pause