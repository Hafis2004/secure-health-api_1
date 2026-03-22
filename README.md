# Secure Health API - Complete Implementation Guide

A Python/Flask microservices application for secure healthcare data management with OIDC authentication, encryption at rest, audit logging, and comprehensive monitoring.

## ✅ Completed Tasks

- [x] **TASK 1**: Fixed `server.py` to run HTTPS on port 8443 with self-signed certificates
  - Added GET `/records` endpoint to list all encrypted patient records
  - Both GET endpoints require `['viewer', 'editor']` roles
  - POST `/records` requires `['editor']` role

- [x] **TASK 2**: Corrected Dockerfile
  - Installs requirements.txt with pytest support
  - Exposes port 8443 for HTTPS
  - Mounts certs and keys via Docker volumes/secrets
  - Runs Flask app with proper entrypoint

- [x] **TASK 3**: Fixed `compliance.py` audit_log function
  - Now writes to `audit.log` file with full entries
  - Includes timestamp, user, action, patient_id, and remote IP
  - Handles errors gracefully with try/except

- [x] **TASK 4**: Added comprehensive unit tests to `test_api.py`
  - `test_minimize()`: Tests data minimization
  - `test_get_record_viewer()`: GET with viewer role (200 expected)
  - `test_post_record_editor()`: POST with editor role (201 expected)
  - `test_post_record_viewer_forbidden()`: POST with viewer role (403 expected)
  - `test_get_all_records_editor()`: List all records
  - `test_missing_token()`: Tests 401 unauthorized

- [x] **TASK 5**: Updated `Jenkinsfile` with complete CI/CD pipeline
  - Test stage: Runs pytest with JUnit XML output
  - Security stage: Runs pip-audit for dependency checking
  - Deploy stage: docker compose up -d (all services)

- [x] **TASK 6**: Provided Keycloak setup instructions
  - See `KEYCLOAK_SETUP.md` for step-by-step curl commands
  - Creates realm "health", client "health-api"
  - Creates roles: "viewer", "editor"
  - Creates users: "lab_viewer", "lab_editor" with assignments

- [x] **TASK 7**: Provided complete curl test commands
  - See `CURL_TEST_COMMANDS.md` for end-to-end testing
  - Tests all endpoints with both viewer and editor roles
  - Demonstrates encryption and audit logging
  - Includes complete test scripts

- [x] **TASK 8**: Provided TLS verification commands
  - See `TLS_VERIFICATION.md` for multiple verification methods
  - openssl s_client, curl verbose, Python, nmap commands
  - Complete diagnostic script included

- [x] **TASK 9**: Completed `keyrotate.py` script
  - Properly decrypts all records with old key
  - Re-encrypts with new Fernet key
  - Creates backups of old key
  - Includes error handling and logging

- [x] **TASK 10**: Fixed Docker Compose secrets configuration
  - See `DOCKER_SECRETS_CONFIG.md` for detailed documentation
  - Secrets properly mounted at `/run/secrets/data_key`
  - App correctly reads from environment variable
  - Data and audit.log volumes mount for persistence

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- OpenSSL (for certificate verification)
- curl (for testing)
- jq (optional, for JSON parsing in scripts)

### 1. Generate Encryption Key

```bash
# Generate Fernet key for AES encryption
mkdir -p keys
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > keys/data.key
chmod 600 keys/data.key
```

### 2. Verify TLS Certificates

```bash
# Certificates should already exist at:
# - certs/server.crt
# - certs/server.key

# If not present, generate them:
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -nodes \
    -out certs/server.crt \
    -keyout certs/server.key \
    -days 365 \
    -subj "/CN=localhost"
chmod 600 certs/server.key
```

### 3. Start All Services

```bash
# Start all containers (Keycloak, API, Jenkins, Prometheus, Grafana, Loki)
docker compose up -d

# Watch logs
docker compose logs -f app

# Wait for Keycloak (ready when port 8080 responds)
curl -s http://localhost:8080/realms/master/protocol/openid-connect/.well-known/openid-configuration | jq .
```

### 4. Set Up Keycloak

Follow [KEYCLOAK_SETUP.md](KEYCLOAK_SETUP.md) to:
- Create realm "health"
- Create client "health-api"
- Create roles "viewer" and "editor"
- Create users "lab_viewer" and "lab_editor"

Quick setup (with curl):

```bash
# Get admin token
ADMIN_TOKEN=$(curl -s -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=admin" \
  -d "grant_type=password" | jq -r '.access_token')

# Create realm
curl -s -X POST http://localhost:8080/admin/realms \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"realm":"health","enabled":true}'

# ... continue with other steps from KEYCLOAK_SETUP.md
```

### 5. Test the API

Follow [CURL_TEST_COMMANDS.md](CURL_TEST_COMMANDS.md) for full examples, or quick test:

```bash
# Get editor token
EDITOR_TOKEN=$(curl -s -X POST http://localhost:8080/realms/health/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=health-api" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "username=lab_editor" \
  -d "password=editor123" \
  -d "grant_type=password" | jq -r '.access_token')

# Create patient record
curl -k -X POST https://localhost:8443/records \
  -H "Authorization: Bearer $EDITOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"patient1","name":"John Doe","dob":"1990-01-01","consent":true}'

# Get record
curl -k -X GET https://localhost:8443/records/patient1 \
  -H "Authorization: Bearer $EDITOR_TOKEN"
```

## 📚 Documentation

- **[KEYCLOAK_SETUP.md](KEYCLOAK_SETUP.md)** - Step-by-step Keycloak configuration
- **[CURL_TEST_COMMANDS.md](CURL_TEST_COMMANDS.md)** - Complete API testing guide
- **[TLS_VERIFICATION.md](TLS_VERIFICATION.md)** - TLS/HTTPS verification
- **[DOCKER_SECRETS_CONFIG.md](DOCKER_SECRETS_CONFIG.md)** - Docker secrets setup

## 🏗️ Architecture

```
┌─────────────────┐
│   Keycloak      │ (OIDC/IAM)
│   :8080         │
└────────┬────────┘
         │ OAuth2/OIDC
         v
┌─────────────────────────────────────┐
│   Secure Health API                 │
│   Flask App :8443 (HTTPS)           │
│ ┌───────────────────────────────┐   │
│ │ /records (GET/POST)           │   │
│ │ /metrics (Prometheus)         │   │
│ │                               │   │
│ │ + JWT verify from Keycloak    │   │
│ │ + Role-based access control   │   │
│ │ + AES encryption at rest      │   │
│ │ + Audit logging               │   │
│ └───────────────────────────────┘   │
└────────┬──────────────┬──────────────┘
         │              │
         v              v
    ┌────────┐    ┌──────────────┐
    │Encrypted   │  audit.log    │
    │Patient     │  (JSON)       │
    │Records     │               │
    │(.bin files)│               │
    └────────┘    └──────────────┘

Monitoring Stack (Optional):
├── Prometheus :9090    (Metrics collection)
├── Grafana :3000       (Visualization)
├── Loki :3100          (Log aggregation)
└── Promtail            (Log shipping)

Jenkins :8081          (CI/CD)
```

## 🔐 Security Features

1. **Authentication**: OAuth2/OIDC via Keycloak
   - JWT token verification
   - Realm and client-level roles
   - User principal stored in `flask.g`

2. **Authorization**: Role-based access control (RBAC)
   - `viewer` role: Read-only access
   - `editor` role: Read/write access
   - Enforced via decorators

3. **Encryption at Rest**: Fernet (AES-128-CBC)
   - Patient records encrypted before storage
   - Keys managed via Docker secrets
   - Key rotation support

4. **Audit Logging**: JSON-based audit trail
   - Timestamp, user, action, patient_id, IP
   - Written to `audit.log`
   - Supports compliance requirements

5. **TLS/HTTPS**: Self-signed certificates on port 8443
   - Server certificate: `certs/server.crt`
   - Server key: `certs/server.key`
   - Can be upgraded to CA-signed certs

6. **Data Minimization**: `data_minimize()` function
   - Strips sensitive fields (SSN, etc.)
   - Returns only: id, name, dob, consent

## 📊 Monitoring

### Prometheus Metrics

Access at `https://localhost:8443/metrics`:

```
# API request counts
api_requests_total{endpoint="/records",method="GET",status="200"}

# Request latency
api_request_latency_seconds_bucket{endpoint="/records"}
```

### Grafana Dashboards

Access at `http://localhost:3000` (Admin/admin)

### Audit Logs

```bash
# View audit trail
cat audit.log | jq '.'

# Recent entries
tail -20 audit.log

# Count actions
cat audit.log | jq '.action' | sort | uniq -c
```

## 🧪 Testing

### Run Unit Tests Locally

```bash
cd app

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Run Tests in Docker

```bash
# Test stage in Jenkinsfile
docker run --rm health-api:local python -m pytest tests/ -v --junitxml=pytest.xml
```

### Test JWT Tokens

```bash
# Decode JWT token (for debugging)
curl -s http://localhost:8080/realms/health/protocol/openid-connect/token \
  -d "client_id=health-api" \
  -d "client_secret=$SECRET" \
  -d "username=lab_viewer" \
  -d "password=viewer123" \
  -d "grant_type=password" \
  | jq '.access_token' \
  | sed 's/"//g' \
  | jq -R 'split(".") | .[1] | @base64d | fromjson'
```

## 🔄 Key Rotation

Rotate encryption keys without data loss:

```bash
python keyrotate.py
```

This script:
1. Reads old encryption key
2. Generates new Fernet key
3. Re-encrypts all patient records
4. Backs up old key
5. Updates `keys/data.key`

## 📦 API Endpoints

| Method | Endpoint | Role Required | Returns | Purpose |
|--------|----------|---------------|---------|---------|
| GET | `/records` | viewer, editor | List all records | Get all patient records |
| GET | `/records/<pid>` | viewer, editor | Single record | Get specific patient |
| POST | `/records` | editor | {id: pid} | Create patient record |
| GET | `/metrics` | None | Prometheus metrics | Monitor API |

## 🔧 Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OIDC_ISSUER` | http://localhost:8080/realms/health | Keycloak realm URL |
| `OIDC_AUDIENCE` | health-api | Intended audience for JWT |
| `APP_DATA_KEY` | keys/data.key | Path to Fernet encryption key |
| `RETENTION_DAYS` | 30 | Audit log retention period |

### Flask Configuration

In `app/server.py`:
- Host: `0.0.0.0` (all interfaces)
- Port: `8443` (HTTPS)
- SSL context: Uses certs/server.crt and certs/server.key
- Debug mode: Disabled in production

## 🐛 Troubleshooting

### API won't start

```bash
# Check if port 8443 is in use
netstat -an | grep 8443
# or on Windows:
netstat -ano | findstr :8443

# Check logs
docker compose logs app
```

### SSL certificate error

```bash
# Always use -k flag with curl (self-signed cert)
curl -k https://localhost:8443/...

# Or verify certificate
openssl s_client -connect localhost:8443
```

### Keycloak not responding

```bash
# Wait for Keycloak to start (can take 30-60 seconds)
docker compose logs keycloak

# Check if running
curl http://localhost:8080/admin/
```

### JWT decode errors

```bash
# Verify token format
curl ... | jq '.access_token'

# Decode to check claims
echo $TOKEN | jq -R 'split(".") | .[1] | @base64d | fromjson'
```

### Data not persisting

```bash
# Ensure volumes are mounted
docker inspect health-api_app_1 | grep -A 5 '  "Mounts"'

# Verify mount on container
docker compose exec app ls -la /app/data/
docker compose exec app ls -la /run/secrets/
```

## 📝 Implementation Details

### Storage (AES Encryption)

File: `app/storage.py`

- Uses Fernet (AES-128-CBC) from cryptography library
- Each patient record encrypted as separate `.bin` file
- Stored in `data/` directory
- Key loaded from `APP_DATA_KEY` environment variable

### Authentication

File: `app/auth.py`

- Fetches JWKS from Keycloak
- Verifies JWT signature (disabled in demo)
- Extracts claims into `flask.g.user`
- Check roles in `realm_access.roles` and `resource_access.<AUD>.roles`

### Compliance

File: `app/compliance.py`

- `data_minimize()`: Strips sensitive fields
- `enforce_consent()`: Requires consent flag
- `audit_log()`: Writes to audit.log
- `retention_cleanup()`: Stub for future cleanup

### Metrics

File: `app/server.py`

- Prometheus Counter: API requests by endpoint/method/status
- Prometheus Histogram: Request latency by endpoint
- Endpoint: GET `/metrics`
