# ==============================================================================
# Description: Dockerfile for the lightweight DNS Sinkhole container.
# Version: 1.0.0
# Author: Alhasan Al-Hmondi
# ==============================================================================

# Use a lightweight Python Alpine image for a minimal system footprint
FROM python:3.11-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy dependency requirements and install them without caching to save space
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code into the container
COPY src/ /app/

# Expose standard DNS ports (UDP is primary for DNS, TCP for fallback)
EXPOSE 53/udp
EXPOSE 53/tcp

# Define the entrypoint command to run the server in unbuffered mode (-u)
# This ensures that logs appear immediately in the Docker console
CMD ["python", "-u", "dns_server.py"]