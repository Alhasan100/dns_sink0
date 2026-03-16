# 🛡️ DNS Sinkhole
**Version:** 1.4.0 | **Author:** Alhasan Al-Hmondi



A lightweight, blazing-fast DNS Sinkhole (network-wide adblocker) built with Python and Docker. It protects your entire home network by intercepting DNS requests to known ad, tracking, and malware domains, routing them into a "sinkhole" (0.0.0.0) before they can even load.

## ✨ Features
* **Dynamic Blocklist:** Automatically downloads over 100,000+ domains from StevenBlack's respected hosts file.
* **Background Auto-Update:** Silently refreshes the blocklist in the background at custom intervals without dropping a single DNS request.
* **Blazing Fast Cache:** Built-in memory caching (`CACHE_TTL`) ensures repeated DNS queries are answered in milliseconds.
* **Cross-Platform:** Includes intelligent, auto-installing deployment scripts for Windows, Linux (Debian/Ubuntu), and macOS.
* **Dockerized:** Runs in a secure, isolated container to keep your host system clean.
* **Fully Configurable:** Easy setup using a standard `.env` file.

---

## 🚀 Quick Start (Deployment)

You don't need to be a Python expert to run this. The included deployment scripts handle everything—including installing Docker if you don't have it!

### For Linux & macOS
1. Open your terminal and navigate to the project folder.
2. Make the deployment script executable:
   ```bash
   chmod +x start_unix.sh

```

*(Troubleshooting: If `chmod` fails or you still get a permission error, you can force the execution by running `sudo bash start_unix.sh` directly).*
3. Run the deployment script as root/admin:

```bash
sudo ./start_unix.sh

```

4. The script will automatically handle port conflicts (like `systemd-resolved` on Linux), build the container, and output your server's IP address.

### For Windows

1. Open File Explorer and navigate to the project folder.
2. Right-click `start_windows.bat` and select **"Run as administrator"**.
3. If Docker Desktop is not installed, the script will download and install it for you (a restart might be required). Run the script again once Docker is active.

---

## ⚙️ Configuration

You can easily customize how the Sinkhole behaves without touching the Python code. Open the `.env` file to adjust the settings:

| Variable | Default Value | Description |
| --- | --- | --- |
| `UPSTREAM_DNS` | `8.8.8.8` | The DNS server to forward safe traffic to (e.g., `1.1.1.1` for Cloudflare). |
| `UPSTREAM_PORT` | `53` | The port used by the upstream DNS server. |
| `CACHE_TTL` | `300` | How long (in seconds) safe domains are kept in the lightning-fast memory cache. |
| `BLOCKLIST_UPDATE_INTERVAL` | `86400` | Auto-update interval for the blocklist (in seconds). 86400 = 24 hours. |

---

## 🧪 Testing Your Sinkhole

Before changing your router settings, verify that the sinkhole is actively blocking ads. Run this command from your terminal (replace `<YOUR_IP>` with the IP address provided by the deployment script):

```bash
# Test a known ad domain (Should return 0.0.0.0)
nslookup doubleclick.net <YOUR_IP>

# Test a normal domain (Should return a real IP address)
nslookup github.com <YOUR_IP>

```

---

## 🌐 Network-Wide Setup

Once you have verified the server is working:

1. Log in to your home router's admin panel (usually `192.168.1.1` or `192.168.0.1`).
2. Find the **DHCP / LAN / DNS** settings.
3. Change the **Primary DNS Server** to the IP address of the machine running this container.
4. Save and reboot your router. Now, every device connected to your Wi-Fi is ad-free!

```
