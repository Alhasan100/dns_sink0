import socket
import logging
from dnslib import DNSRecord, RR, QTYPE, A

# Configure standard logging for professional output monitoring
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- CONFIGURATION ---
HOST = '0.0.0.0'
PORT = 53
UPSTREAM_DNS = '8.8.8.8'
UPSTREAM_PORT = 53
TIMEOUT = 2.0  # Timeout in seconds for upstream DNS queries

# Hardcoded blocklist for initial implementation.
BLOCKLIST = {
    "ads.example.com",
    "track.google.com",
    "fusk-annonser.se"
}

def start_dns_server():
    """
    Initializes the UDP socket and starts the DNS sinkhole event loop.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((HOST, PORT))
        logging.info(f"DNS Sinkhole initialized. Listening on {HOST}:{PORT}...")
    except PermissionError:
        logging.error(f"Permission denied. Cannot bind to port {PORT}. Are you running as root/admin?")
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
                logging.info(f"[BLOCKED] {domain} requested by {addr[0]}")
                reply = request.reply()
                reply.add_answer(RR(domain, QTYPE.A, rdata=A("0.0.0.0"), ttl=60))
                sock.sendto(reply.pack(), addr)
            else:
                # --- UPSTREAM RESOLUTION ---
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream_sock:
                    upstream_sock.settimeout(TIMEOUT)
                    upstream_sock.sendto(data, (UPSTREAM_DNS, UPSTREAM_PORT))
                    upstream_data, _ = upstream_sock.recvfrom(4096)
                    sock.sendto(upstream_data, addr)

        except socket.timeout:
            logging.warning(f"Upstream DNS request timed out for domain: {domain}")
        except Exception as e:
            logging.error(f"Malformed packet or processing error from {addr[0]}: {e}")

if __name__ == '__main__':
    start_dns_server()