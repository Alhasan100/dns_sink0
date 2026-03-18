@echo off
SETLOCAL EnableDelayedExpansion
:: ==============================================================================
:: Description: Windows deployment script for the DNS Sink0. Automates Docker 
::              Desktop installation, environment checks, and container startup.
:: Version: 1.2.0
:: Author: Alhasan Al-Hmondi
:: ==============================================================================

echo Initializing DNS Sink0 Deployment for Windows...
echo.

:: 1. Check for Administrative privileges
:: We need admin rights to perform silent installations and check system ports
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script requires administrative privileges.
    echo Action required: Right-click 'start_windows.bat' and select 'Run as administrator'.
    pause
    exit /b 1
)

:: 2. Auto-install Docker Desktop if it's missing
docker --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Docker is NOT installed. Downloading Docker Desktop...
    echo This might take a few minutes depending on your internet connection.
    
    :: Fetch the official installer using built-in curl
    curl -L -o DockerInstaller.exe "https://desktop.docker.com/win/main/amd64/Docker%%20Desktop%%20Installer.exe"
    
    echo [INFO] Running Docker installation quietly...
    start /wait "" DockerInstaller.exe install --quiet
    del DockerInstaller.exe
    
    echo.
    echo ==================================================================
    echo [ATTENTION] Docker Desktop has been installed!
    echo ==================================================================
    echo Windows requires Docker Desktop to initialize WSL2 properly.
    echo 1. Open 'Docker Desktop' from your Windows Start menu.
    echo 2. Accept the terms and let it start up.
    echo 3. IF Windows asks you to restart your computer, please do so.
    echo.
    echo After Docker is running properly, run this script again!
    echo ==================================================================
    pause
    exit /b 0
) else (
    echo [INFO] Docker is already installed.
)

:: 3. Port 53 conflict check
:: Let the user know if another Windows service (like ICS) is hogging the DNS port
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
    :: Extract the active Local IP address using PowerShell so the user can easily configure their router
    for /f "delims=" %%i in ('powershell -Command "(Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -ne $null }).IPv4Address.IPAddress"') do set LOCAL_IP=%%i

    echo.
    echo ==================================================================
    echo  [SUCCESS] DNS Sink0 is now active and operational! 
    echo ==================================================================
    echo Next Step: Configure your router's Primary DNS to point to this IP:
    echo.
    echo      --^>  !LOCAL_IP!  ^<--
    echo.
    echo ==================================================================
) else (
    echo.
    echo [ERROR] Docker deployment failed. Is Docker Desktop running?
)

pause