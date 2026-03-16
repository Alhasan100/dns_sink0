@echo off
SETLOCAL EnableDelayedExpansion

:: ==============================================================================
:: Windows Deployment Script
:: ==============================================================================

echo Initializing DNS Sinkhole Deployment for Windows...
echo.

:: Check for Administrative privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script requires administrative privileges.
    echo Action required: Right-click 'start_windows.bat' and select 'Run as administrator'.
    pause
    exit /b 1
)

:: Check if Port 53 is already in use
echo [INFO] Checking if port 53 is available...
netstat -ano | findstr :53 >nul
if %errorLevel% equ 0 (
    echo [WARNING] Port 53 appears to be in use by another Windows service.
) else (
    echo [INFO] Port 53 appears to be free.
)

echo.
echo [INFO] Building and provisioning the Docker container...
echo ------------------------------------------------------------------

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