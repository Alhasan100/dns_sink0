"""
Description: A lightweight, fast DNS Sinkhole (Adblocker) with dynamic blocklist downloading, in-memory caching, and background auto-updating.
Version: 1.4.0
Author: Alhasan Al-Hmondi
"""

import os
import socket
import logging
import urllib.request
import time
import threading
from dnslib import DNSRecord, RR, QTYPE, A

# Configure standard logging so we can monitor traffic in the Docker console
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- CONFIGURATION (Dynamically loaded from .env) ---
HOST = '0.0.0.0'
PORT = 53
UPSTREAM_DNS = os.getenv('UPSTREAM_DNS', '8.8.8.8')
UPSTREAM_PORT = int(os.getenv('UPSTREAM_PORT', 53))
CACHE_TTL = int(os.getenv('CACHE_TTL', 300))
# How often to auto-update the blocklist in seconds (Default: 86400 seconds = 24 hours)
BLOCKLIST_UPDATE_INTERVAL = int(os.getenv('BLOCKLIST_UPDATE_INTERVAL', 86400))

# We use StevenBlack's highly respected open-source hosts file for our blocklist
BLOCKLIST_URL = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"

# In-memory storage for blazing fast lookups
BLOCKLIST = set()
DNS_CACHE = {} 

def download_blocklist():
    """
    Fetches the latest ad/malware domains from the internet and loads them into memory.
    """
    logging.info(f"Downloading blocklist from {BLOCKLIST_URL}...")
    domains = set()
    try:
        # Masquerade as a standard web browser to avoid getting blocked by the host
        req = urllib.request.Request(BLOCKLIST_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            for line in response:
                decoded_line = line.decode('utf-8').strip()
                
                # Skip empty lines and comments
                if not decoded_line or decoded_line.startswith('#'):
                    continue
                
                # Split the line to extract the domain (e.g., "0.0.0.0 ads.google.com")
                parts = decoded_line.split()
                if len(parts) >= 2 and parts[0] in ('0.0.0.0', '127.0.0.1'):
                    domain = parts[1].lower()
                    if domain != 'localhost':
                        domains.add(domain)
                        
        logging.info(f"[SUCCESS] Loaded {len(domains)} domains into the blocklist!")
        return domains
    except Exception as e:
        logging.error(f"[ERROR] Failed to download blocklist: {e}")
        return set()

def auto_update_blocklist():
    """
    Runs continuously in a background thread. It sleeps for the configured interval,
    wakes up to download a fresh blocklist, and seamlessly swaps it into memory 
    without interrupting the main DNS server thread.
    """
    global BLOCKLIST
    while True:
        time.sleep(BLOCKLIST_UPDATE_INTERVAL)
        logging.info("[AUTO-UPDATE] Waking up to fetch a fresh blocklist...")
        new_blocklist = download_blocklist()
        
        # Only replace the active list if the download was actually successful
        if new_blocklist:
            BLOCKLIST = new_blocklist
            logging.info("[AUTO-UPDATE] Background update complete. Shield is fully refreshed!")

def start_dns_server():
    """
    Initializes the UDP socket and starts the main event loop for handling DNS queries.
    """
    global BLOCKLIST, DNS_CACHE
    
    # Pre-load the blocklist before opening the port
    BLOCKLIST = download_blocklist()

    # --- NEW: Start the background auto-updater thread ---
    # Setting daemon=True means this thread will safely die when the main program closes
    update_thread = threading.Thread(target=auto_update_blocklist, daemon=True)
    update_thread.start()
    logging.info(f"Background auto-updater started (Interval: {BLOCKLIST_UPDATE_INTERVAL} seconds).")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))
        logging.info(f"DNS Sinkhole initialized. Listening on {HOST}:{PORT}...")
    except PermissionError:
        logging.error(f"Permission denied. Cannot bind to port {PORT}. Ensure you are running as root/admin.")
        return
    except Exception as e:
        logging.error(f"Failed to bind socket: {e}")
        return

    while True:
        try:
            data, addr = sock.recvfrom(512)
        except Exception:
            continue

        try:
            request = DNSRecord.parse(data)
            domain = str(request.q.qname).rstrip('.').lower()
            qtype = request.q.qtype

            # --- 1. BLOCKING LOGIC ---
            if domain in BLOCKLIST:
                logging.info(f"[BLOCKED]  {domain}")
                reply = request.reply()
                reply.add_answer(RR(domain, QTYPE.A, rdata=A("0.0.0.0"), ttl=60))
                sock.sendto(reply.pack(), addr)
                continue

            # --- 2. CACHE LOGIC ---
            cache_key = (domain, qtype)
            current_time = time.time()
            
            if cache_key in DNS_CACHE:
                expire_time, cached_data = DNS_CACHE[cache_key]
                
                if current_time < expire_time:
                    logging.info(f"[CACHED]   {domain}")
                    response = bytearray(cached_data)
                    response[0:2] = data[0:2] 
                    sock.sendto(response, addr)
                    continue
                else:
                    del DNS_CACHE[cache_key]

            # --- 3. UPSTREAM RESOLUTION ---
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream_sock:
                upstream_sock.settimeout(2.0)
                upstream_sock.sendto(data, (UPSTREAM_DNS, UPSTREAM_PORT))
                upstream_data, _ = upstream_sock.recvfrom(4096)
                
                DNS_CACHE[cache_key] = (current_time + CACHE_TTL, upstream_data)
                logging.info(f"[UPSTREAM] {domain}")
                
                sock.sendto(upstream_data, addr)

        except socket.timeout:
            logging.warning(f"Upstream DNS request timed out for domain: {domain}")
        except Exception:
            pass

if __name__ == '__main__':
    start_dns_server()