# Docker Compose Secrets Configuration

This document explains how Docker secrets are used in the Secure Health API and how to configure them correctly.

## Overview

Docker secrets provide a secure way to manage sensitive data (like encryption keys) in Docker Compose and Docker Swarm. Secrets are:

1. Stored encrypted in the Docker daemon
2. Available to containers only as files in `/run/secrets/`
3. Never exposed in environment variables (more secure)
4. Support rotation and versioning

## Current Configuration

The `docker-compose.yml` already has secrets configured:

```yaml
services:
  app:
    environment:
      - OIDC_ISSUER=http://keycloak:8080/realms/health
      - OIDC_AUDIENCE=health-api
      - APP_DATA_KEY=/run/secrets/data_key  # Path to secret file
    secrets:
      - data_key  # Reference to defined secret
    ports:
      - "8443:8443"
    volumes:
      - ./certs:/app/certs
    depends_on: [ keycloak ]
    networks: [ appnet ]

secrets:
  data_key:
    file: ./keys/data.key  # Source file (must exist!)
```

## How It Works

1. **Secret Definition** (at compose root level):
   ```yaml
   secrets:
     data_key:
       file: ./keys/data.key
   ```
   This tells Docker to read the encryption key from `./keys/data.key` and register it as a secret named `data_key`.

2. **Secret Reference** (in service):
   ```yaml
   app:
     secrets:
       - data_key
   ```
   This mounts the secret into the container at `/run/secrets/data_key`.

3. **Environment Variable** (for app to know where to find it):
   ```yaml
   environment:
     - APP_DATA_KEY=/run/secrets/data_key
   ```

4. **Application Code** (reads from environment):
   ```python
   # storage.py
   KEY_FILE = os.environ.get('APP_DATA_KEY', 'keys/data.key')
   ```

## Prerequisites

Before running docker compose up, ensure the secret source file exists:

```bash
# Generate key if it doesn't exist
ls -la keys/data.key

# If not found, generate it:
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > keys/data.key

# Verify it's readable
head -c 100 keys/data.key
```

## Running with Secrets

### Option 1: Docker Compose (Recommended for Demo)

Standard setup:

```bash
# Start all services
docker compose up -d

# Verify the app container is running
docker compose logs app

# Verify the secret is mounted correctly
docker compose exec app ls -la /run/secrets/
docker compose exec app cat /run/secrets/data_key
```

### Option 2: Standalone Docker with Named Secrets

If using Docker Swarm mode:

```bash
# Initialize Docker Swarm (if not already)
docker swarm init

# Create a named secret from the key file
docker secret create data_key keys/data.key

# Verify the secret exists
docker secret ls

# Use in docker-compose (requires docker compose in swarm mode)
docker stack deploy -c docker-compose.yml health-api

# View logs
docker service logs health-api_app
```

## Alternative: Using Environment Variables (Less Secure)

If you prefer to use environment variables instead of Docker secrets:

```yaml
services:
  app:
    environment:
      - OIDC_ISSUER=http://keycloak:8080/realms/health
      - OIDC_AUDIENCE=health-api
      - APP_DATA_KEY=/app/keys/data.key  # Direct path
    volumes:
      - ./keys:/app/keys:ro  # Mount keys as read-only
      - ./certs:/app/certs
    depends_on: [ keycloak ]
    networks: [ appnet ]
```

**Note**: This is less secure because:
- Key is in memory as environment variable
- Volume mount copies are less protected
- Better for development only

## Entrypoint Script Option (Advanced)

For more control, use an entrypoint script:

Create `app/entrypoint.sh`:

```bash
#!/bin/bash
set -e

# Handle Docker secret (mounted at /run/secrets/data_key)
if [ -f /run/secrets/data_key ]; then
    echo "[*] Using Docker secret for data key"
    export APP_DATA_KEY=/run/secrets/data_key
fi

# Fall back to local key if secret not found
if [ ! -f "$APP_DATA_KEY" ]; then
    if [ -f /app/keys/data.key ]; then
        export APP_DATA_KEY=/app/keys/data.key
        echo "[*] Using local key file"
    else
        echo "[!] No encryption key found!"
        exit 1
    fi
fi

# Generate certificates if not present
if [ ! -f /app/certs/server.crt ] || [ ! -f /app/certs/server.key ]; then
    echo "[*] Generating self-signed certificates..."
    mkdir -p /app/certs
    openssl req -x509 -newkey rsa:2048 -nodes \
        -out /app/certs/server.crt \
        -keyout /app/certs/server.key \
        -days 365 \
        -subj "/CN=localhost"
fi

echo "[*] Starting Health API..."
exec python server.py
```

Update the Dockerfile to use it:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8443

# Make entrypoint executable and use it
RUN chmod +x entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
```

Update docker-compose.yml:

```yaml
app:
  build: ./app
  environment:
    - OIDC_ISSUER=http://keycloak:8080/realms/health
    - OIDC_AUDIENCE=health-api
  secrets:
    - data_key
  ports:
    - "8443:8443"
  volumes:
    - ./certs:/app/certs
  depends_on: [ keycloak ]
  networks: [ appnet ]
```

## Verifying Secrets Work Correctly

### Test 1: Check Secret in Container

```bash
# Once container is running
docker compose exec app cat /run/secrets/data_key

# Should output the Fernet key (base64 string)
```

### Test 2: Verify App Reads Key Correctly

```bash
# Check app logs
docker compose logs app | grep -i "key\|secret\|encrypt"

# Try creating a record
curl -k https://localhost:8443/records \
  -H "authorization: Bearer $(get_token)" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"test","name":"Test","dob":"2000-01-01","consent":true}'
```

### Test 3: Verify Encryption

```bash
# Check encrypted file exists and is binary
file data/test.bin
# Should output: data/test.bin: data

# Try to read it (should be garbage)
cat data/test.bin
strings data/test.bin
```

### Test 4: Key Rotation with Secret

When rotating keys with Docker secrets:

```bash
# Run key rotation script
docker compose exec app python keyrotate.py

# Docker will handle updating the secret
# No need to manually update the mounted file

# For persistent secrets, update the source file:
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > keys/data.key

# Restart the service to use new secret
docker compose restart app
```

## Security Best Practices

1. **File Permissions**: Keep `keys/data.key` readable only by owner:
   ```bash
   chmod 600 keys/data.key
   ls -la keys/data.key
   # Should show: -rw------- (permission 600)
   ```

2. **Backup the Key**: Store a backup in a secure location:
   ```bash
   cp keys/data.key keys/data.key.backup
   chmod 600 keys/data.key.backup
   ```

3. **Key Rotation**: Regularly rotate encryption keys:
   ```bash
   python keyrotate.py
   # Then commit the changes (or update Docker secret)
   ```

4. **Environment Variables**: Don't print or log the key:
   ```bash
   # DON'T do this:
   echo $APP_DATA_KEY
   
   # Instead, just check that it's set:
   [ -f /run/secrets/data_key ] && echo "Key is mounted"
   ```

5. **Access Control**: Restrict who can read the key:
   ```bash
   # Only root and app user
   chown root:appuser keys/data.key
   chmod 640 keys/data.key
   ```

6. **Encrypted Storage**: In production, use:
   - HashiCorp Vault for key management
   - Azure Key Vault or AWS Secrets Manager
   - Kubernetes Secrets with encryption at rest

## Troubleshooting

### Problem: "No such file or directory: /run/secrets/data_key"

**Solution**: The secret must be defined and referenced:

```bash
# Verify secret definition
grep -A2 "secrets:" docker-compose.yml

# Verify secret is mounted in service
grep -A2 "secrets:" docker-compose.yml | grep -A1 "app:"
```

### Problem: APP_DATA_KEY is not being read

**Solution**: Check environment variable:

```bash
docker compose exec app env | grep APP_DATA_KEY

# Should output:
# APP_DATA_KEY=/run/secrets/data_key
```

### Problem: Key file doesn't exist

**Solution**: Create it before starting compose:

```bash
mkdir -p keys
python3 << 'EOF'
from cryptography.fernet import Fernet
key = Fernet.generate_key()
with open('keys/data.key', 'wb') as f:
    f.write(key)
EOF

chmod 600 keys/data.key
ls -la keys/data.key
```

### Problem: Secret file is world-readable (insecure)

**Solution**: Restrict permissions:

```bash
chmod 600 keys/data.key
chmod 700 keys/

# Verify
ls -la keys/
# drwx------ (700)
# -rw------- (600)
```

### Problem: Old containers using old secret

**Solution**: Stop and remove containers to force re-creation:

```bash
docker compose down
docker compose up -d
```

## Complete Working Example

Here's a complete, tested configuration:

**Directory structure:**
```
secure-health-api/
├── keys/
│   └── data.key          # Generated Fernet key
├── certs/                # TLS certs
├── app/
│   ├── server.py
│   ├── storage.py        # Reads APP_DATA_KEY env var
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml    # Defines secrets
└── README.md
```

**Setup:**
```bash
# 1. Generate Fernet key
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > keys/data.key
chmod 600 keys/data.key

# 2. Start services
docker compose up -d

# 3. Verify secret is mounted
docker compose exec app ls /run/secrets/

# 4. Create test record
EDITOR_TOKEN=$(curl -s http://localhost:8080/realms/health/protocol/openid-connect/token \
  -d "client_id=health-api" -d "client_secret=$SECRET" \
  -d "username=lab_editor" -d "password=editor123" \
  -d "grant_type=password" | jq -r .access_token)

curl -k https://localhost:8443/records \
  -H "Authorization: Bearer $EDITOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"test1","name":"Test","dob":"2000-01-01","consent":true}'

# 5. Verify encryption
file data/test1.bin  # Should show: data (binary)
```

## Summary

- ✓ Docker Compose secrets are already configured in `docker-compose.yml`
- ✓ Secret is mounted at `/run/secrets/data_key`
- ✓ Application reads from `APP_DATA_KEY` environment variable
- ✓ `storage.py` correctly reads from env var
- ✓ Make sure `keys/data.key` exists before `docker compose up`
- ✓ Use `chmod 600` on key files for security
- ✓ Consider entrypoint script for more control (optional)
