# Getting Started: Complete Setup Checklist

This guide provides a step-by-step checklist to get the Secure Health API up and running from scratch.

## Phase 1: Prerequisites ✓

- [ ] Docker and Docker Compose installed
- [ ] Python 3.10+ or 3.11 installed
- [ ] curl installed
- [ ] OpenSSL installed
- [ ] jq installed (optional, for JSON parsing)
- [ ] Git installed

Verify:
```bash
docker --version
docker-compose --version
python3 --version
curl --version
openssl version
```

## Phase 2: Repository Setup ✓

- [ ] Clone or extract the repository
  ```bash
  cd secure-health-api
  ```

- [ ] Verify directory structure
  ```bash
  ls -la
  # Should show: app/, certs/, keys/, jenkins/, monitoring/, docker-compose.yml, README.md, etc.
  ```

- [ ] Create necessary directories
  ```bash
  mkdir -p keys data certs
  chmod 700 keys certs
  ```

## Phase 3: Generate Encryption Key ✓

- [ ] Generate Fernet encryption key
  ```bash
  python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > keys/data.key
  chmod 600 keys/data.key
  ```

- [ ] Verify key file
  ```bash
  ls -la keys/data.key
  # Should show: -rw------- (permissions 600)
  
  head -c 50 keys/data.key
  # Should show base64 encoded string starting with: EncryptedFernet...
  ```

## Phase 4: Generate TLS Certificates ✓

- [ ] Check if certificates exist
  ```bash
  ls certs/server.crt certs/server.key
  ```

- [ ] If not, generate self-signed certificates
  ```bash
  openssl req -x509 -newkey rsa:2048 -nodes \
    -out certs/server.crt \
    -keyout certs/server.key \
    -days 365 \
    -subj "/CN=localhost"
  chmod 600 certs/server.key
  ```

- [ ] Verify certificates
  ```bash
  ls -la certs/
  # Should show: -rw-r--r-- server.crt and -rw------- server.key
  
  openssl x509 -in certs/server.crt -text -noout | grep -A2 "Issuer\|Subject"
  ```

## Phase 5: Docker Compose Startup ✓

- [ ] Build Docker image
  ```bash
  docker-compose build app
  ```

- [ ] Start all services
  ```bash
  docker-compose up -d
  ```

- [ ] Verify containers are running
  ```bash
  docker-compose ps
  # All services should have status: Up
  ```

- [ ] Check logs for errors
  ```bash
  docker-compose logs keycloak | tail -20
  docker-compose logs app | tail -20
  ```

- [ ] Wait for Keycloak to be ready (can take 30-60 seconds)
  ```bash
  # Keep running until you see successful response
  curl -s http://localhost:8080/realms/master/.well-known/openid-configuration | jq . > /dev/null && echo "✓ Keycloak is ready"
  ```

## Phase 6: Keycloak Configuration ✓

See [KEYCLOAK_SETUP.md](KEYCLOAK_SETUP.md) for detailed instructions.

Quick setup:

```bash
# Save this as setup_keycloak.sh and run it
#!/bin/bash
set -e

KEYCLOAK_URL="http://localhost:8080"

echo "[*] Getting admin token..."
ADMIN_TOKEN=$(curl -s -X POST $KEYCLOAK_URL/realms/master/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=admin" \
  -d "grant_type=password" | jq -r '.access_token')

echo "[+] Creating realm..."
curl -s -X POST $KEYCLOAK_URL/admin/realms \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"realm":"health","enabled":true}'

echo "[+] Creating client..."
CLIENT_ID=$(curl -s -X POST $KEYCLOAK_URL/admin/realms/health/clients \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"clientId":"health-api","enabled":true,"clientAuthenticationType":"confidential","directAccessGrantsEnabled":true}' \
  | jq -r '.id')

echo "[+] Getting client secret..."
CLIENT_SECRET=$(curl -s -X GET $KEYCLOAK_URL/admin/realms/health/clients/$CLIENT_ID/client-secret \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.value')

echo "[+] Creating roles..."
curl -s -X POST $KEYCLOAK_URL/admin/realms/health/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"viewer"}'

curl -s -X POST $KEYCLOAK_URL/admin/realms/health/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"editor"}'

echo "[+] Creating users..."
LAB_VIEWER=$(curl -s -X POST $KEYCLOAK_URL/admin/realms/health/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"lab_viewer","enabled":true}' | jq -r '.id')

curl -s -X PUT $KEYCLOAK_URL/admin/realms/health/users/$LAB_VIEWER/reset-password \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"password","value":"viewer123","temporary":false}'

LAB_EDITOR=$(curl -s -X POST $KEYCLOAK_URL/admin/realms/health/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"lab_editor","enabled":true}' | jq -r '.id')

curl -s -X PUT $KEYCLOAK_URL/admin/realms/health/users/$LAB_EDITOR/reset-password \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"password","value":"editor123","temporary":false}'

echo "[+] Assigning roles..."
VIEWER_ROLE=$(curl -s -X GET $KEYCLOAK_URL/admin/realms/health/roles/viewer \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.id')

curl -s -X POST $KEYCLOAK_URL/admin/realms/health/users/$LAB_VIEWER/role-mappings/realm \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "[{\"id\":\"$VIEWER_ROLE\",\"name\":\"viewer\",\"composite\":false,\"clientRole\":false,\"containerId\":\"health\"}]"

EDITOR_ROLE=$(curl -s -X GET $KEYCLOAK_URL/admin/realms/health/roles/editor \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r '.id')

curl -s -X POST $KEYCLOAK_URL/admin/realms/health/users/$LAB_EDITOR/role-mappings/realm \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "[{\"id\":\"$EDITOR_ROLE\",\"name\":\"editor\",\"composite\":false,\"clientRole\":false,\"containerId\":\"health\"}]"

echo "[+] Setup complete!"
echo "Client ID: health-api"
echo "Client Secret: $CLIENT_SECRET"
save this client secret for testing!
echo "Access OpenSSL admin console: http://localhost:8080 (admin/admin)"
```

- [ ] Save the Client Secret (you'll need it for testing)
  ```bash
  export CLIENT_SECRET="<YOUR_CLIENT_SECRET>"
  ```

- [ ] Verify setup by getting a token
  ```bash
  curl -s -X POST http://localhost:8080/realms/health/protocol/openid-connect/token \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=health-api" \
    -d "client_secret=$CLIENT_SECRET" \
    -d "username=lab_viewer" \
    -d "password=viewer123" \
    -d "grant_type=password" | jq '.access_token'
  ```

## Phase 7: Test API Endpoints ✓

See [CURL_TEST_COMMANDS.md](CURL_TEST_COMMANDS.md) for full testing guide.

Quick tests:

```bash
# Set up environment
export API_URL="https://localhost:8443"
export KEYCLOAK_URL="http://localhost:8080"
export CLIENT_ID="health-api"
export CLIENT_SECRET="<YOUR_CLIENT_SECRET>"

# Get editor token
export EDITOR_TOKEN=$(curl -s -X POST $KEYCLOAK_URL/realms/health/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "username=lab_editor" \
  -d "password=editor123" \
  -d "grant_type=password" | jq -r '.access_token')

echo "[+] Testing POST /records..."
curl -k -X POST $API_URL/records \
  -H "Authorization: Bearer $EDITOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"patient_id":"test_patient_1","name":"John Doe","dob":"1990-01-01","consent":true}'

echo -e "\n[+] Testing GET /records/test_patient_1..."
curl -k -X GET $API_URL/records/test_patient_1 \
  -H "Authorization: Bearer $EDITOR_TOKEN"

echo -e "\n[+] Testing GET /records (list all)..."
curl -k -X GET $API_URL/records \
  -H "Authorization: Bearer $EDITOR_TOKEN"

echo -e "\n[+] GET /metrics..."
curl -k -X GET $API_URL/metrics
```

- [ ] Verify responses are successful (200, 201 status codes)
- [ ] Check that audit.log is being written
  ```bash
  docker-compose exec app tail -5 audit.log | jq '.'
  ```

## Phase 8: Verify Encryption ✓

- [ ] Check encrypted files exist
  ```bash
  ls -la data/
  # Should show: test_patient_1.bin (encrypted binary)
  ```

- [ ] Verify files are not readable as text
  ```bash
  file data/test_patient_1.bin
  # Should show: data (binary, not JSON)
  ```

- [ ] Try to read raw content (should be gibberish)
  ```bash
  cat data/test_patient_1.bin | head -c 100
  # Should output unreadable binary data
  ```

## Phase 9: Verify TLS/HTTPS ✓

See [TLS_VERIFICATION.md](TLS_VERIFICATION.md) for detailed verification.

Quick verification:

```bash
# Test TLS connection
openssl s_client -connect localhost:8443 < /dev/null 2>/dev/null | grep -E "depth=|Verify return|Protocol|Cipher"

# Should show:
# depth=0 CN = localhost
# verify return:1
# Protocol  : TLSv1.2 (or higher)
# Cipher    : ECDHE-RSA-AES256-GCM-SHA384 (or similar)
```

## Phase 10: Run Unit Tests ✓

- [ ] Run tests locally
  ```bash
  cd app
  pip install -r requirements.txt
  pytest tests/ -v
  ```

- [ ] Or run in Docker
  ```bash
  docker-compose run --rm app python -m pytest tests/ -v
  ```

- [ ] Expected output
  ```
  test_minimize PASSED
  test_get_record_viewer PASSED
  test_post_record_editor PASSED
  test_post_record_viewer_forbidden PASSED
  test_get_all_records_editor PASSED
  test_missing_token PASSED
  ===== 6 passed in 0.123s =====
  ```

## Phase 11: Verify Audit Logging ✓

- [ ] Check audit log file
  ```bash
  # View recent entries
  tail -10 audit.log
  
  # Pretty print JSON
  cat audit.log | jq '.'
  
  # Count actions
  cat audit.log | jq '.action' | sort | uniq -c
  ```

- [ ] Expected entries
  ```json
  {"ts": 1711097400, "user": "lab_editor", "action": "CREATE", "patient_id": "test_patient_1", "ip": "127.0.0.1"}
  {"ts": 1711097405, "user": "lab_editor", "action": "READ", "patient_id": "test_patient_1", "ip": "127.0.0.1"}
  ```

## Phase 12: Verify Monitoring ✓

- [ ] Check Prometheus metrics
  ```bash
  curl -k https://localhost:8443/metrics | head -20
  
  # Should show metrics like:
  # api_requests_total{endpoint="/records",method="POST",status="201"} 1.0
  # api_requests_total{endpoint="/records",method="GET",status="200"} 3.0
  ```

- [ ] Access Grafana (optional)
  ```bash
  # Open: http://localhost:3000
  # Login: admin / admin
  # Add Prometheus data source: http://prometheus:9090
  ```

## Phase 13: Test Role-Based Access Control ✓

- [ ] Get viewer token
  ```bash
  export VIEWER_TOKEN=$(curl -s -X POST $KEYCLOAK_URL/realms/health/protocol/openid-connect/token \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=$CLIENT_ID" \
    -d "client_secret=$CLIENT_SECRET" \
    -d "username=lab_viewer" \
    -d "password=viewer123" \
    -d "grant_type=password" | jq -r '.access_token')
  ```

- [ ] Viewer can READ
  ```bash
  curl -k -X GET $API_URL/records/test_patient_1 \
    -H "Authorization: Bearer $VIEWER_TOKEN"
  # Should return: 200 OK
  ```

- [ ] Viewer cannot WRITE
  ```bash
  curl -i -k -X POST $API_URL/records \
    -H "Authorization: Bearer $VIEWER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"patient_id":"test2","name":"Test","dob":"2000-01-01","consent":true}'
  # Should return: 403 Forbidden
  ```

## Phase 14: Cleanup & Shutdown ✓

- [ ] To stop all services
  ```bash
  docker-compose down
  ```

- [ ] To remove volumes and start fresh
  ```bash
  docker-compose down -v
  rm -rf data/* audit.log
  ```

- [ ] To save logs before shutdown
  ```bash
  docker-compose logs > logs_$(date +%Y%m%d_%H%M%S).txt
  docker-compose down
  ```

## Phase 15: Restore and Resume ✓

- [ ] To start back up (data persists in ./data)
  ```bash
  docker-compose up -d
  ```

- [ ] To do key rotation
  ```bash
  docker-compose exec app python keyrotate.py
  ```

- [ ] To clean data while keeping setup
  ```bash
  rm data/*.bin
  > audit.log
  docker-compose restart app
  ```

## Post-Setup: Next Steps

- [ ] Deploy to staging environment
- [ ] Configure using [DOCKER_SECRETS_CONFIG.md](DOCKER_SECRETS_CONFIG.md) for production
- [ ] Set up CI/CD with [jenkins/Jenkinsfile](jenkins/Jenkinsfile)
- [ ] Implement additional security (TLS certificate upgrade, vault integration)
- [ ] Scale horizontally with load balancer
- [ ] Implement database instead of flat files
- [ ] Add API rate limiting
- [ ] Set up alerting and monitoring dashboards

## Troubleshooting Checklist

| Problem | Solution |
|---------|----------|
| Port 8443 already in use | `kill -9 $(lsof -t -i :8443)` or `netstat -ano \| findstr :8443` on Windows |
| Keycloak not ready | Wait 30-60 seconds and check `docker logs keycloak` |
| No Fernet key | Run: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" > keys/data.key` |
| SSL certificate error | Always use `-k` flag with curl (self-signed cert) |
| JWT decode error | Verify token hasn't expired, get a fresh one |
| Audit log not writing | Check file permissions: `ls -la audit.log` |
| Data not persisting | Check Docker volumes: `docker inspect health-api_app_1 \| grep -A 5 "Mounts"` |
| Tests failing | Run `pytest -v` to see detailed error messages |

## Success Criteria ✓

- [x] All services running (`docker-compose ps`)
- [x] Keycloak accessible at http://localhost:8080
- [x] API responds to HTTPS requests on port 8443
- [x] Can create patient records as editor
- [x] Can list records as viewer
- [x] Cannot create records as viewer (403)
- [x] Patient data is encrypted on disk
- [x] Audit log records all actions
- [x] JWT tokens are validated
- [x] TLS handshake works with openssl s_client
- [x] All unit tests pass
- [x] Prometheus metrics are collected

## Support & Documentation

- [README.md](README.md) - Main documentation
- [KEYCLOAK_SETUP.md](KEYCLOAK_SETUP.md) - Keycloak configuration details
- [CURL_TEST_COMMANDS.md](CURL_TEST_COMMANDS.md) - Complete API testing guide
- [TLS_VERIFICATION.md](TLS_VERIFICATION.md) - TLS verification methods
- [DOCKER_SECRETS_CONFIG.md](DOCKER_SECRETS_CONFIG.md) - Docker secrets management

---

**Last Updated**: March 22, 2026
**Status**: ✅ All 10 tasks completed
