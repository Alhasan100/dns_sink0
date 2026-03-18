"""
Description: A lightweight, fast DNS Sinkhole (Adblocker) with dynamic blocklist downloading, in-memory caching, and background auto-updating.
Version: 1.5.0
Author: Alhasan Al-Hmondi
"""

import os
import glob
import socket
import logging
import urllib.request
import time
import threading
from dnslib import DNSRecord, RR, QTYPE, A

# Configure standard logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configuration from .env
HOST = '0.0.0.0'
PORT = 53
UPSTREAM_DNS = os.getenv('UPSTREAM_DNS', '8.8.8.8')
UPSTREAM_PORT = int(os.getenv('UPSTREAM_PORT', 53))
CACHE_TTL = int(os.getenv('CACHE_TTL', 300))
BLOCKLIST_UPDATE_INTERVAL = int(os.getenv('BLOCKLIST_UPDATE_INTERVAL', 86400))

# Directories for custom lists
CONFIG_DIR = os.getenv('CONFIG_DIR', './config')
REMOTE_URLS_FILE = os.path.join(CONFIG_DIR, 'remote_blocklists.txt')
LOCAL_LISTS_DIR = os.path.join(CONFIG_DIR, 'local_blocklists')

BLOCKLIST = set()
DNS_CACHE = {}

def ensure_config_dirs():
    """
    Ensure that the configuration directories and files exist.
    Creates default files if they are missing.
    """
    os.makedirs(LOCAL_LISTS_DIR, exist_ok=True)
    
    if not os.path.exists(REMOTE_URLS_FILE):
        with open(REMOTE_URLS_FILE, 'w') as f:
            f.write("# Add one URL per line to download remote blocklists.\n")
            f.write("https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts\n")


def parse_domain_line(line):
    """
    Extracts a valid domain from various formats, including standard hosts,
    Adblock Plus syntax (||domain.com^), and messy arrays ('||domain.com^',).
    """
    # Remove comments
    clean_line = line.split('#')[0].strip()

    # Strip unwanted characters: single quotes, double quotes, and trailing commas
    clean_line = clean_line.replace("'", "").replace('"', "").rstrip(',')

    # Strip Adblock Plus specific syntax (|| at the start, ^ at the end)
    clean_line = clean_line.replace("||", "").replace("^", "")

    # Clean up any remaining whitespace
    clean_line = clean_line.strip()

    if not clean_line:
        return None

    # Handle standard hosts format (e.g., "0.0.0.0 ads.com") or raw domains
    parts = clean_line.split()
    if len(parts) >= 2 and parts[0] in ('0.0.0.0', '127.0.0.1'):
        domain = parts[1].lower()
    else:
        domain = parts[0].lower()

    if domain != 'localhost':
        return domain

    return None

def build_blocklist():
    """
    Builds the master blocklist by downloading all remote URLs and reading 
    all local text files.
    """
    ensure_config_dirs()
    master_domains = set()
    
    # 1. Process Remote URLs
    if os.path.exists(REMOTE_URLS_FILE):
        with open(REMOTE_URLS_FILE, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
        for url in urls:
            logging.info(f"Downloading remote list: {url}")
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    for line in response:
                        decoded_line = line.decode('utf-8')
                        domain = parse_domain_line(decoded_line)
                        if domain:
                            master_domains.add(domain)
            except Exception as e:
                logging.error(f"Failed to download {url}: {e}")

    # 2. Process Local Custom Files
    local_files = glob.glob(os.path.join(LOCAL_LISTS_DIR, '*.txt'))
    for file_path in local_files:
        logging.info(f"Loading local list: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    domain = parse_domain_line(line)
                    if domain:
                        master_domains.add(domain)
        except Exception as e:
            logging.error(f"Failed to read local file {file_path}: {e}")

    logging.info(f"[SUCCESS] Shield active! Loaded {len(master_domains)} total domains into the master blocklist.")
    return master_domains

def auto_update_blocklist():
    """
    Background thread that continuously refreshes the blocklists.
    """
    global BLOCKLIST
    while True:
        time.sleep(BLOCKLIST_UPDATE_INTERVAL)
        logging.info("[AUTO-UPDATE] Fetching fresh remote and local blocklists...")
        new_list = build_blocklist()
        if new_list:
            BLOCKLIST = new_list

def start_dns_server():
    """
    Initializes the UDP socket and handles incoming DNS queries.
    """
    global BLOCKLIST, DNS_CACHE
    
    BLOCKLIST = build_blocklist()

    # Start the background auto-updater thread
    update_thread = threading.Thread(target=auto_update_blocklist, daemon=True)
    update_thread.start()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))
        logging.info(f"DNS Sinkhole initialized on {HOST}:{PORT}...")
    except PermissionError:
        logging.error("Permission denied. Cannot bind to port 53. Run as root/admin.")
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

            # Check Blocklist
            if domain in BLOCKLIST:
                logging.info(f"[BLOCKED]  {domain}")
                reply = request.reply()
                reply.add_answer(RR(domain, QTYPE.A, rdata=A("0.0.0.0"), ttl=60))
                sock.sendto(reply.pack(), addr)
                continue

            # Check Cache
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

            # Upstream Resolution
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream_sock:
                upstream_sock.settimeout(2.0)
                upstream_sock.sendto(data, (UPSTREAM_DNS, UPSTREAM_PORT))
                upstream_data, _ = upstream_sock.recvfrom(4096)
                
                DNS_CACHE[cache_key] = (current_time + CACHE_TTL, upstream_data)
                logging.info(f"[UPSTREAM] {domain}")
                
                sock.sendto(upstream_data, addr)

        except Exception:
            pass

if __name__ == '__main__':
    #start_dns_server()
    
    a =build_blocklist()
    print(a)