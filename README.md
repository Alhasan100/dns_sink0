
# 🛡️ DNS Sink0
**Version:** 1.5.0 | **Author:** Alhasan Al-Hmondi
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

A lightweight, blazing-fast DNS Sinkhole (network-wide adblocker) built with Python and Docker. **DNS Sink0** protects your entire home network by intercepting DNS requests to known ad, tracking, and malware domains, routing them into a "sinkhole" (0.0.0.0) before they can even load.

## ✨ Features
* **Modular Blocklists (New in v1.5.0!):** Easily add your own remote URLs or drop local `.txt` files into the `config/` directory. No container rebuilds required!
* **Smart Parsing Engine:** Automatically cleans messy list formats. Supports standard hosts, raw domains, and Adblock Plus (`||domain.com^`) syntax.
* **Background Auto-Update:** Silently refreshes all blocklists in the background at custom intervals without dropping a single DNS request.
* **Blazing Fast Cache:** Built-in memory caching (`CACHE_TTL`) ensures repeated DNS queries are answered in milliseconds.
* **Cross-Platform & Dockerized:** Auto-installing deployment scripts for Windows (`start_windows.bat`), Linux, and macOS (`start_unix.sh`).

---

## 📂 Configuration & Custom Blocklists

DNS Sink0 uses a mapped `config/` volume, allowing you to manage your blocklists effortlessly. When you run the container, it creates the following structure:

```text
dns_sink0/
├── config/                              
│   ├── local_blocklists/                
│   │   └── my_custom_ads.txt            <-- Drop custom .txt domain lists here
│   └── remote_blocklists.txt            <-- Paste URLs for auto-downloading here
```

* **`remote_blocklists.txt`**: Add raw text/hosts URLs here (one per line). The background updater will download and merge them automatically.
* **`local_blocklists/`**: Create `.txt` files here to block specific domains manually. The smart parser automatically handles messy syntax, meaning you can paste domains directly from other adblockers without formatting them first.

---

## 🚀 Quick Start (Deployment)

You don't need to be a Python expert to run this. The included deployment scripts handle everything—including installing Docker if you don't have it!

### For Linux & macOS
1. Open your terminal and navigate to the project folder.
2. Make the deployment script executable:
   ```bash
   chmod +x start_unix.sh
   ```
3. Run the deployment script as root/admin:
   ```bash
   sudo ./start_unix.sh
   ```

### For Windows
1. Open File Explorer and navigate to the project folder.
2. Right-click `start_windows.bat` and select **"Run as administrator"**.
3. If Docker Desktop is not installed, the script will automatically download and set it up for you.

---

## ⚙️ Environment Variables

Customize how the server behaves by editing the `.env` file:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `UPSTREAM_DNS` | `8.8.8.8` | The DNS server to forward safe traffic to (e.g., `1.1.1.1` for Cloudflare). |
| `UPSTREAM_PORT`| `53` | The port used by the upstream DNS server. |
| `CACHE_TTL` | `300` | How long (in seconds) safe domains are kept in the lightning-fast memory cache. |
| `BLOCKLIST_UPDATE_INTERVAL` | `86400` | Auto-update interval for the blocklists (in seconds). 86400 = 24 hours. |

---

## 🧪 Testing Your Sinkhole

Before changing your router settings, verify the sinkhole is actively blocking ads. Run this command from your terminal (replace `<YOUR_IP>` with the IP address of your server):

```bash
# Test a known ad domain (Should return 0.0.0.0)
nslookup doubleclick.net <YOUR_IP>

# Test a normal domain (Should return a real IP address)
nslookup github.com <YOUR_IP>
```

---

## 🌐 Network-Wide Setup

1. Log in to your home router's admin panel (usually `192.168.1.1` or `192.168.0.1`).
2. Find the **DHCP / LAN / DNS** settings.
3. Change the **Primary DNS Server** to the IP address of the machine running DNS Sink0.
4. Save and reboot your router. Every device connected to your Wi-Fi is now protected!


