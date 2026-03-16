import socket
import logging
import urllib.request
from dnslib import DNSRecord, RR, QTYPE, A

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- CONFIGURATION ---
HOST = '0.0.0.0'
PORT = 53
UPSTREAM_DNS = '8.8.8.8'
UPSTREAM_PORT = 53
TIMEOUT = 2.0

# Världens mest populära open-source blocklista
BLOCKLIST_URL = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"

# Nu startar vi med en tom lista som vi fyller på när programmet startar
BLOCKLIST = set()


def download_blocklist():
    """
    Downloads and parses a hosts file from the internet to build the blocklist.
    """
    logging.info(f"Downloading blocklist from {BLOCKLIST_URL}...")
    domains = set()
    try:
        # Vi låtsas vara en vanlig webbläsare för att inte bli blockerade
        req = urllib.request.Request(BLOCKLIST_URL, headers={
                                     'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            for line in response:
                # Koda av texten och ta bort mellanslag
                decoded_line = line.decode('utf-8').strip()

                # Hoppa över kommentarer och tomma rader
                if not decoded_line or decoded_line.startswith('#'):
                    continue

                # En rad ser ut så här: "0.0.0.0 ads.google.com"
                # Vi delar upp raden för att bara plocka ut domännamnet
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
        # Om nedladdningen misslyckas, returnera en tom lista så servern inte kraschar
        return set()


def start_dns_server():
    """
    Initializes the UDP socket and starts the DNS sinkhole event loop.
    """
    # 1. Ladda ner listan INNAN vi startar servern
    global BLOCKLIST
    BLOCKLIST = download_blocklist()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))
        logging.info(
            f"DNS Sinkhole initialized. Listening on {HOST}:{PORT}...")
    except PermissionError:
        logging.error(
            f"Permission denied. Cannot bind to port {PORT}. Are you running as root/admin?")
        return
    except Exception as e:
        logging.error(f"Failed to bind socket: {e}")
        return

    while True:
        try:
            data, addr = sock.recvfrom(512)
        except Exception as e:
            logging.error(f"Socket receive error: {e}")
            continue

        try:
            request = DNSRecord.parse(data)
            domain = str(request.q.qname).rstrip('.').lower()

            # --- BLOCKING LOGIC ---
            if domain in BLOCKLIST:
                logging.info(f"[BLOCKED] {domain}")
                reply = request.reply()
                reply.add_answer(
                    RR(domain, QTYPE.A, rdata=A("0.0.0.0"), ttl=60))
                sock.sendto(reply.pack(), addr)
            else:
                # --- UPSTREAM RESOLUTION ---
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream_sock:
                    upstream_sock.settimeout(TIMEOUT)
                    upstream_sock.sendto(data, (UPSTREAM_DNS, UPSTREAM_PORT))
                    upstream_data, _ = upstream_sock.recvfrom(4096)
                    sock.sendto(upstream_data, addr)

        except socket.timeout:
            logging.warning(
                f"Upstream DNS request timed out for domain: {domain}")
        except Exception as e:
            pass  # Tystar fel från trasiga paket så inte loggen fylls med skräp


if __name__ == '__main__':
    start_dns_server()
    
    
    #BLOCKLIST = download_blocklist()
    #print(BLOCKLIST)