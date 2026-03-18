"""
Description: A lightweight, fast DNS Sinkhole (Adblocker) with modular blocklists.
Version: 2.0.0-beta (Allowlist & Regex support)
Author: Alhasan Al-Hmondi
"""

import os
import glob
import socket
import logging
import urllib.request
import time
import threading
import re
from dnslib import DNSRecord, RR, QTYPE, A

# Configure standard logging for operational visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Core networking configuration
HOST = '0.0.0.0'
PORT = 53
UPSTREAM_DNS = os.getenv('UPSTREAM_DNS', '8.8.8.8')
UPSTREAM_PORT = int(os.getenv('UPSTREAM_PORT', 53))
CACHE_TTL = int(os.getenv('CACHE_TTL', 300))
BLOCKLIST_UPDATE_INTERVAL = int(os.getenv('BLOCKLIST_UPDATE_INTERVAL', 86400))

# Path definitions for modular configuration
CONFIG_DIR = os.getenv('CONFIG_DIR', './config')
REMOTE_URLS_FILE = os.path.join(CONFIG_DIR, 'remote_blocklists.txt')
LOCAL_LISTS_DIR = os.path.join(CONFIG_DIR, 'local_blocklists')
ALLOWLIST_FILE = os.path.join(CONFIG_DIR, 'allowlist.txt')
REGEX_FILE = os.path.join(CONFIG_DIR, 'regex_blocklist.txt')

# Global state
# Sets provide O(1) lookup complexity for domain matching
BLOCKLIST = set()
ALLOWLIST = set()
COMPILED_REGEXES = []
DNS_CACHE = {}


def ensure_config_dirs():
    """
    Bootstraps the environment by validating directory structures
    and generating default configuration files if absent.
    
    Args:
        None
        
    Returns:
        None
    """
    os.makedirs(LOCAL_LISTS_DIR, exist_ok=True)

    if not os.path.exists(REMOTE_URLS_FILE):
        with open(REMOTE_URLS_FILE, 'w') as f:
            f.write("# Add one URL per line to download remote blocklists.\n")
            f.write(
                "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts\n")

    if not os.path.exists(ALLOWLIST_FILE):
        with open(ALLOWLIST_FILE, 'w') as f:
            f.write(
                "# ==============================================================================\n")
            f.write("# DNS Sink0 - Allowlist (Whitelist)\n")
            f.write(
                "# Domains listed here will NEVER be blocked, overriding all blocklists.\n")
            f.write(
                "# ==============================================================================\n")

    if not os.path.exists(REGEX_FILE):
        with open(REGEX_FILE, 'w') as f:
            f.write(
                "# ==============================================================================\n")
            f.write("# DNS Sink0 - Regex Blocklist\n")
            f.write(
                "# Add one regular expression per line to block domains matching the pattern.\n")
            f.write(
                "# Example: block all subdomains of example.com (e.g., ads.example.com)\n")
            f.write("# .*\\.example\\.com\n")
            f.write(
                "# ==============================================================================\n")


def parse_domain_line(line):
    """
    Normalizes diverse string formats (standard hosts, Adblock Plus syntax, 
    raw text arrays) into a strict, matchable domain string.
    
    Args:
        line (str): Raw string from a blocklist.
        
    Returns:
        str: Cleaned, lowercase domain string.
        None: If the line is a comment, empty, or an invalid target.
    """
    clean_line = line.split('#')[0].strip()
    clean_line = clean_line.replace("'", "").replace('"', "").rstrip(',')
    clean_line = clean_line.replace("||", "").replace("^", "")
    clean_line = clean_line.strip()

    if not clean_line:
        return None

    parts = clean_line.split()
    if len(parts) >= 2 and parts[0] in ('0.0.0.0', '127.0.0.1'):
        domain = parts[1].lower()
    else:
        domain = parts[0].lower()

    if domain != 'localhost':
        return domain

    return None


def build_allowlist():
    """
    Parses the local allowlist configuration.
    
    Args:
        None
        
    Returns:
        set: Domains authorized to bypass all filtering logic.
    """
    ensure_config_dirs()
    allow_domains = set()
    if os.path.exists(ALLOWLIST_FILE):
        try:
            with open(ALLOWLIST_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    domain = parse_domain_line(line)
                    if domain:
                        allow_domains.add(domain)
        except Exception as e:
            logging.error(f"Failed to read allowlist file: {e}")

    logging.info(f"Loaded {len(allow_domains)} domains into the allowlist.")
    return allow_domains


def build_regex_list():
    """
    Parses and pre-compiles regex patterns to minimize runtime CPU overhead.
    
    Args:
        None
        
    Returns:
        list: Compiled re.Pattern objects.
    """
    ensure_config_dirs()
    regex_list = []
    if os.path.exists(REGEX_FILE):
        try:
            with open(REGEX_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    pattern = line.split('#')[0].strip()
                    if pattern:
                        try:
                            compiled_pattern = re.compile(pattern)
                            regex_list.append(compiled_pattern)
                        except re.error as e:
                            logging.error(
                                f"Invalid regex pattern '{pattern}': {e}")
        except Exception as e:
            logging.error(f"Failed to read regex file: {e}")

    logging.info(f"Loaded {len(regex_list)} regex patterns.")
    return regex_list


def build_blocklist():
    """
    Aggregates and deduplicates domains from remote URLs and local files.
    
    Args:
        None
        
    Returns:
        set: Unified collection of blocked domain strings.
    """
    ensure_config_dirs()
    master_domains = set()

    if os.path.exists(REMOTE_URLS_FILE):
        with open(REMOTE_URLS_FILE, 'r') as f:
            urls = [line.strip() for line in f if line.strip()
                    and not line.startswith('#')]

        for url in urls:
            logging.info(f"Downloading remote list: {url}")
            try:
                req = urllib.request.Request(
                    url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    for line in response:
                        decoded_line = line.decode('utf-8')
                        domain = parse_domain_line(decoded_line)
                        if domain:
                            master_domains.add(domain)
            except Exception as e:
                logging.error(f"Failed to download {url}: {e}")

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

    logging.info(
        f"[SUCCESS] Shield active! Loaded {len(master_domains)} total domains into the master blocklist.")
    return master_domains


def auto_update_lists():
    """
    Daemon worker that periodically refreshes filtering rules without 
    interrupting the main execution loop.
    
    Args:
        None
        
    Returns:
        None
    """
    global BLOCKLIST, ALLOWLIST, COMPILED_REGEXES
    while True:
        time.sleep(BLOCKLIST_UPDATE_INTERVAL)
        logging.info("[AUTO-UPDATE] Fetching fresh lists...")

        ALLOWLIST = build_allowlist()
        COMPILED_REGEXES = build_regex_list()
        new_blocklist = build_blocklist()

        if new_blocklist:
            BLOCKLIST = new_blocklist


def start_dns_server():
    """
    Binds the UDP socket, parses incoming queries, evaluates against 
    the filtering pipeline, and routes traffic.
    
    Args:
        None
        
    Returns:
        None
    """
    global BLOCKLIST, ALLOWLIST, COMPILED_REGEXES, DNS_CACHE

    ALLOWLIST = build_allowlist()
    COMPILED_REGEXES = build_regex_list()
    BLOCKLIST = build_blocklist()

    update_thread = threading.Thread(target=auto_update_lists, daemon=True)
    update_thread.start()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))
        logging.info(f"DNS Sink0 initialized on {HOST}:{PORT}...")
    except PermissionError:
        logging.error(
            "Permission denied. Cannot bind to port 53. Run as root/admin.")
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

            # Allowlist overrides all block rules
            if domain in ALLOWLIST:
                logging.info(f"[ALLOWED]  {domain} (Bypassing filters)")

            else:
                # Evaluate against compiled regex patterns
                is_regex_blocked = False
                for pattern in COMPILED_REGEXES:
                    if pattern.search(domain):
                        is_regex_blocked = True
                        logging.info(f"[BLOCKED]  {domain} (Matched Regex)")
                        break

                # Evaluate against strict domain matches and execute sinkhole
                if is_regex_blocked or domain in BLOCKLIST:
                    if not is_regex_blocked:
                        logging.info(f"[BLOCKED]  {domain}")

                    reply = request.reply()
                    reply.add_answer(
                        RR(domain, QTYPE.A, rdata=A("0.0.0.0"), ttl=60))
                    sock.sendto(reply.pack(), addr)
                    continue

            # Resolve from local cache if TTL remains valid
            cache_key = (domain, qtype)
            current_time = time.time()
            if cache_key in DNS_CACHE:
                expire_time, cached_data = DNS_CACHE[cache_key]
                if current_time < expire_time:
                    response = bytearray(cached_data)
                    # Preserve original transaction ID
                    response[0:2] = data[0:2]
                    sock.sendto(response, addr)
                    continue
                else:
                    del DNS_CACHE[cache_key]

            # Forward unresolved queries to upstream provider
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream_sock:
                upstream_sock.settimeout(2.0)
                upstream_sock.sendto(data, (UPSTREAM_DNS, UPSTREAM_PORT))
                upstream_data, _ = upstream_sock.recvfrom(4096)

                DNS_CACHE[cache_key] = (
                    current_time + CACHE_TTL, upstream_data)
                sock.sendto(upstream_data, addr)

        # Drop malformed packets silently
        except Exception:
            pass


if __name__ == '__main__':
    start_dns_server()
