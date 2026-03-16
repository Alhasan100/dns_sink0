# Use a lightweight Python image for minimal footprint
FROM python:3.11-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy dependency requirements and install them
COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY src/ /app/

# Expose standard DNS ports
EXPOSE 53/udp
EXPOSE 53/tcp

# Define the entrypoint command to run the server unbuffered
CMD ["python", "-u", "dns_server.py"]