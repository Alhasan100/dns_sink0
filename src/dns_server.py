"""
Description: A lightweight, fast DNS Sinkhole (Adblocker) with dynamic blocklist downloading and in-memory caching.
Version: 1.3.0
Author: Alhasan Al-Hmondi
"""

import os
import socket
import logging
import urllib.request
import time
from dnslib import DNSRecord, RR, QTYPE, A

# Configure standard logging so we can monitor traffic in the Docker console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- CONFIGURATION (Now dynamically loaded from .env) ---
HOST = '0.0.0.0'
PORT = 53
# os.getenv grabs the value from Docker. If missing, it defaults to the second argument.
UPSTREAM_DNS = os.getenv('UPSTREAM_DNS', '8.8.8.8')
UPSTREAM_PORT = int(os.getenv('UPSTREAM_PORT', 53))
CACHE_TTL = int(os.getenv('CACHE_TTL', 300))

# We use StevenBlack's highly respected open-source hosts file for our blocklist
BLOCKLIST_URL = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"

# In-memory storage for blazing fast lookups
BLOCKLIST = set()
DNS_CACHE = {}


def download_blocklist():
    """
    Fetches the latest ad/malware domains from the internet and loads them into memory.
    We filter out the noise and only keep the actual domain names to save RAM.
    """
    logging.info(f"Downloading blocklist from {BLOCKLIST_URL}...")
    domains = set()
    try:
        # Masquerade as a standard web browser to avoid getting blocked by the host
        req = urllib.request.Request(BLOCKLIST_URL, headers={
                                     'User-Agent': 'Mozilla/5.0'})
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

        logging.info(
            f"[SUCCESS] Loaded {len(domains)} domains into the blocklist!")
        return domains
    except Exception as e:
        logging.error(f"[ERROR] Failed to download blocklist: {e}")
        # Return an empty set so the server can still start even if the download fails
        return set()


def start_dns_server():
    """
    Initializes the UDP socket and starts the main event loop for handling DNS queries.
    """
    global BLOCKLIST, DNS_CACHE

    # Pre-load the blocklist before opening the port
    BLOCKLIST = download_blocklist()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))
        logging.info(
            f"DNS Sinkhole initialized. Listening on {HOST}:{PORT}...")
    except PermissionError:
        logging.error(
            f"Permission denied. Cannot bind to port {PORT}. Ensure you are running as root/admin.")
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
            # If the domain is in our list, intercept it and route it to nowhere (0.0.0.0)
            if domain in BLOCKLIST:
                logging.info(f"[BLOCKED]  {domain}")
                reply = request.reply()
                reply.add_answer(
                    RR(domain, QTYPE.A, rdata=A("0.0.0.0"), ttl=60))
                sock.sendto(reply.pack(), addr)
                continue

            # --- 2. CACHE LOGIC ---
            # Check if we already resolved this domain recently to speed up response times
            cache_key = (domain, qtype)
            current_time = time.time()

            if cache_key in DNS_CACHE:
                expire_time, cached_data = DNS_CACHE[cache_key]

                if current_time < expire_time:
                    logging.info(f"[CACHED]   {domain}")

                    # PRO TIP: Instead of rebuilding the DNS packet, we just take the cached raw data
                    # and swap out the first 2 bytes (Transaction ID) to match the client's current request.
                    # This is much faster and ensures the client accepts the response.
                    response = bytearray(cached_data)
                    response[0:2] = data[0:2]

                    sock.sendto(response, addr)
                    continue
                else:
                    # The cache has expired, remove it so we can fetch a fresh IP
                    del DNS_CACHE[cache_key]

            # --- 3. UPSTREAM RESOLUTION ---
            # If it's a safe domain and not in cache, forward the request to Google DNS
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream_sock:
                upstream_sock.settimeout(2.0)
                upstream_sock.sendto(data, (UPSTREAM_DNS, UPSTREAM_PORT))
                upstream_data, _ = upstream_sock.recvfrom(4096)

                # Save the raw response in our cache for future lookups
                DNS_CACHE[cache_key] = (
                    current_time + CACHE_TTL, upstream_data)
                logging.info(f"[UPSTREAM] {domain}")

                sock.sendto(upstream_data, addr)

        except socket.timeout:
            logging.warning(
                f"Upstream DNS request timed out for domain: {domain}")
        except Exception:
            # Silently drop malformed packets to prevent server crashes
            pass


if __name__ == '__main__':
    start_dns_server()
