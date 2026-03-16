# Simple DNS Sinkhole

A lightweight, cross-platform DNS sinkhole for network-wide ad blocking. Built with Python and Docker.

## Features
- **Network-wide blocking:** Block ads on all devices (phones, TVs, PCs) by changing your router's DNS.
- **Cross-Platform:** Works on Linux, macOS, and Windows.
- **One-Click Deployment:** Built-in scripts handle port conflicts and Docker deployment automatically.

## How to Install

1. Clone this repository to your machine.
2. Run the deployment script for your operating system:
   - **Linux / macOS:** Open terminal and run `sudo ./start_unix.sh`
   - **Windows:** Right-click `start_windows.bat` and select "Run as administrator".
3. Log into your router and change the "Primary DNS" to the IP address of the machine running this software.