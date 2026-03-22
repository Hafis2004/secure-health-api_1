FROM python:3.11-slim

WORKDIR /app

# Install pip dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Certs and keys are mounted via Docker volumes/secrets, not copied
# Volume mount for certs: ./certs:/app/certs
# Secret mount for key: data_key at /run/secrets/data_key

EXPOSE 8443

# Entrypoint script to handle secrets and run the app
CMD ["python", "server.py"]