# 🛡️ DNS Sink0
**Version:** 1.5.0 | **Author:** Alhasan Al-Hmondi
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

DNS Sink0 is a professional-grade, high-performance DNS Sinkhole developed in Python and optimized for Docker. It serves as a network-wide firewall for DNS traffic, neutralizing advertisements, trackers, and malware at the resolution layer before they reach your devices.

## 🏗️ Architecture & Packet Flow
The server utilizes a non-blocking UDP listener. Each incoming query is evaluated through a prioritized pipeline to ensure deterministic behavior and maximum throughput:



1.  **Allowlist Check:** Immediate bypass for trusted domains ($O(1)$ complexity).
2.  **Regex Evaluation:** Pattern matching for complex subdomain structures (e.g., `.*\.telemetry\..*`).
3.  **Static Blocklist:** Final check against millions of known malicious domains ($O(1)$ complexity).
4.  **Cache Lookup:** Returns previously resolved safe queries without upstream latency.
5.  **Recursive Forwarding:** Queries passing all filters are sent to the `UPSTREAM_DNS`.

---

## 📂 System File Structure
DNS Sink0 uses a mapped volume for persistent configuration. The following structure is maintained within the project directory:

```text
dns_sink0/
├── src/
│   ├── dns_server.py          # Core DNS Logic & Filtering Engine
│   └── requirements.txt       # Python dependencies (dnslib, etc.)
├── config/                    # Persistent Configuration Volume
│   ├── allowlist.txt          # Priority: High (Never Block)
│   ├── regex_blocklist.txt    # Priority: Medium (Pattern Matching)
│   ├── remote_blocklists.txt  # Auto-syncing remote URL sources
│   └── local_blocklists/      # Directory for custom .txt domain lists
├── docker-compose.yml         # Container orchestration
├── .env                       # Environment variables & Tuning
├── .gitignore                 # Git exclusion rules
├── .dockerignore              # Docker build exclusion rules
├── start_unix.sh              # Linux/macOS Deployment Script
└── start_windows.bat          # Windows Deployment Script
```

---

## 🚀 Deployment & Platform Recommendation

### 🐧 Recommended Platform: Linux
For production environments, **Linux (Ubuntu, Debian, or Raspberry Pi OS) is highly recommended**. 
* **Kernel Efficiency:** Superior handling of the UDP stack on port 53.
* **Low Overhead:** Avoids the virtualization layer (WSL2/Hyper-V) required by Docker Desktop on Windows.
* **Reliability:** Built for 24/7 "headless" operation.

### 1. Environment Configuration
Define your operational parameters in the `.env` file:
```bash
UPSTREAM_DNS=8.8.8.8           # Primary upstream resolver (e.g., Google or Cloudflare)
CACHE_TTL=300                  # Cache duration in seconds
BLOCKLIST_UPDATE_INTERVAL=86400 # Auto-refresh interval (24h)
```

### 2. Execution
* **Linux/macOS (Production):**
    ```bash
    chmod +x start_unix.sh
    sudo ./start_unix.sh
    ```
* **Windows (Testing Only):**
    Run `start_windows.bat` as **Administrator**.

### 🔄 Forcing an Immediate Update
If you modify your lists and need the changes to take effect immediately without waiting for the auto-update cycle:
```bash
docker restart python_dns_sink0
```

---

## 🌐 Network-Wide Integration
To protect every device in your home or office, follow these steps:

1.  **Identify Server IP:** Find the static local IP address of the machine running DNS Sink0.
2.  **Router Configuration:** * Access your router's admin panel (usually `192.168.1.1`).
    * Navigate to **LAN / DHCP / DNS Settings**.
    * Set the **Primary DNS** to the IP of your DNS Sink0 host.
3.  **Reboot Router:** **Crucial Step.** Rebooting the router forces all connected devices to refresh their DHCP lease and start using the new DNS settings immediately.

---

## 🛠️ Operational Maintenance & Troubleshooting

### Monitoring & Health Checks
Observe real-time blocking and server health via the Docker log stream. This is the primary way to verify that queries are being processed:
```bash
docker logs -f python_dns_sink0
```

### Common Issues & Solutions

* **Port 53 Binding Failure:** * *Cause:* On many Linux distros, `systemd-resolved` occupies port 53 by default. 
    * *Fix:* Disable the stub listener in `/etc/systemd/resolved.conf` or stop the service before starting the container.
* **Permission Denied (Socket Error):** * *Cause:* Port 53 is a "privileged" port. 
    * *Fix:* Ensure you are running the deployment scripts with `sudo` (Linux) or as an Administrator (Windows).
* **Upstream Connection Timeout:** * *Cause:* Firewall rules or incorrect `UPSTREAM_DNS` IP in `.env`. 
    * *Fix:* Verify the host machine can ping the upstream DNS (e.g., `ping 8.8.8.8`).
* **IPv6 Leakage:** * *Cause:* If your router provides an IPv6 DNS address, devices might bypass DNS Sink0. 
    * *Fix:* Disable IPv6 DNS in your router or ensure DNS Sink0 is configured for IPv6 (Future update).
* **Changes Not Reflecting:** * *Cause:* Client-side OS cache or browser cache (DNS-over-HTTPS). 
    * *Fix:* Disable "Secure DNS" in Chrome/Firefox settings and flush OS DNS cache.

---

## ⚖️ Performance & Scalability
By utilizing Python `Sets` for domain storage and pre-compiled `RE` objects for pattern matching, DNS Sink0 maintains a near-constant lookup time regardless of list size. This ensures that your internet speed remains unaffected even with millions of active block rules.
