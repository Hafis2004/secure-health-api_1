# End-to-End Curl Test Commands

This document provides complete copy-paste-ready curl commands to demonstrate the full workflow of the Secure Health API.

## Prerequisites

1. Keycloak is running on `http://localhost:8080`
2. Health API is running on `https://localhost:8443`
3. Keycloak realm "health" is set up with:
   - Client: `health-api` with secret `$CLIENT_SECRET`
   - Users: `lab_viewer` / `viewer123` and `lab_editor` / `editor123`
   - Roles: `viewer` and `editor`
4. `curl` is available with `-k` flag for self-signed certificates
5. `jq` is installed for JSON parsing (optional but recommended)

## Setup: Store Variables

```bash
# Set these based on your Keycloak setup
export KEYCLOAK_URL="http://localhost:8080"
export API_URL="https://localhost:8443"
export CLIENT_ID="health-api"
export CLIENT_SECRET="<your-client-secret-here>"
```

## Step 1: Get Access Token for lab_editor

```bash
# Get editor token
EDITOR_TOKEN=$(curl -s -X POST \
  $KEYCLOAK_URL/realms/health/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "username=lab_editor" \
  -d "password=editor123" \
  -d "grant_type=password" \
  | jq -r '.access_token')

echo "Editor Token: $EDITOR_TOKEN"
export EDITOR_TOKEN=$EDITOR_TOKEN
```

**Expected Output**: A long JWT token string

## Step 2: POST a New Patient Record (as editor)

Create a new patient record with editor privileges:

```bash
curl -X POST \
  $API_URL/records \
  -k \
  -H "Authorization: Bearer $EDITOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient123",
    "name": "John Doe",
    "dob": "1990-01-01",
    "consent": true
  }'
```

**Expected Output**:
```json
{"id": "patient123"}
```

**HTTP Status**: `201 Created`

## Step 3: GET the Patient Record (as editor)

Retrieve the record we just created:

```bash
curl -X GET \
  $API_URL/records/patient123 \
  -k \
  -H "Authorization: Bearer $EDITOR_TOKEN"
```

**Expected Output**:
```json
{
  "patient_id": "patient123",
  "name": "John Doe",
  "dob": "1990-01-01",
  "consent": true
}
```

**HTTP Status**: `200 OK`

## Step 4: Get Access Token for lab_viewer

```bash
# Get viewer token
VIEWER_TOKEN=$(curl -s -X POST \
  $KEYCLOAK_URL/realms/health/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "username=lab_viewer" \
  -d "password=viewer123" \
  -d "grant_type=password" \
  | jq -r '.access_token')

echo "Viewer Token: $VIEWER_TOKEN"
export VIEWER_TOKEN=$VIEWER_TOKEN
```

**Expected Output**: A long JWT token string

## Step 5: GET the Patient Record (as viewer)

Viewer should be able to read records:

```bash
curl -X GET \
  $API_URL/records/patient123 \
  -k \
  -H "Authorization: Bearer $VIEWER_TOKEN"
```

**Expected Output**: The same patient record as Step 3

**HTTP Status**: `200 OK`

## Step 6: Try POST a Record (as viewer) - Should Fail

Viewer should NOT be able to create records:

```bash
curl -i -X POST \
  $API_URL/records \
  -k \
  -H "Authorization: Bearer $VIEWER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient456",
    "name": "Jane Smith",
    "dob": "1992-05-15",
    "consent": true
  }'
```

**Expected Output**:
```json
{"error": "forbidden"}
```

**HTTP Status**: `403 Forbidden`

## Step 7: GET All Patient Records (as editor)

List all patient records:

```bash
curl -X GET \
  $API_URL/records \
  -k \
  -H "Authorization: Bearer $EDITOR_TOKEN"
```

**Expected Output**:
```json
{
  "records": [
    {
      "patient_id": "patient123",
      "name": "John Doe",
      "dob": "1990-01-01",
      "consent": true
    }
  ],
  "count": 1
}
```

**HTTP Status**: `200 OK`

## Step 8: Create Multiple Test Records

For better testing, create a few more records:

```bash
# Create doctor record
curl -X POST \
  $API_URL/records \
  -k \
  -H "Authorization: Bearer $EDITOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient001",
    "name": "Alice Johnson",
    "dob": "1985-03-20",
    "consent": true
  }'

# Create another record
curl -X POST \
  $API_URL/records \
  -k \
  -H "Authorization: Bearer $EDITOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "patient002",
    "name": "Bob Wilson",
    "dob": "1995-07-10",
    "consent": true
  }'
```

## Step 9: Verify Encrypted Storage

Check that data is actually encrypted in the file system:

```bash
# View the raw binary encrypted file (should be unreadable)
xxd data/patient123.bin | head -20
```

**Expected Output**: Hex dump of binary data (looks like gibberish)

You can also try:

```bash
# Try to read the file as text (will show garbled characters)
cat data/patient123.bin
strings data/patient123.bin
```

**Expected Output**: Gibberish/binary data (NOT the original JSON)

## Step 10: Verify Audit Logging

Check the audit log file:

```bash
# View recent audit entries
cat audit.log | tail -5

# Or pretty-print the JSON
cat audit.log | jq '.'
```

**Expected Output**: Lines like:
```json
{"ts": 1711097400, "user": "lab_editor", "action": "CREATE", "patient_id": "patient123", "ip": "127.0.0.1"}
{"ts": 1711097410, "user": "lab_editor", "action": "READ", "patient_id": "patient123", "ip": "127.0.0.1"}
```

## Step 11: Test Missing Authorization

Request without token should fail:

```bash
curl -X GET \
  $API_URL/records/patient123 \
  -k
```

**Expected Output**:
```json
{"error": "missing token"}
```

**HTTP Status**: `401 Unauthorized`

## Step 12: Get Prometheus Metrics

Check application metrics:

```bash
curl $API_URL/metrics \
  -k
```

**Expected Output**: Prometheus metrics (text format)

```
# HELP api_requests_total Total API requests
# TYPE api_requests_total counter
api_requests_total{endpoint="/records",method="GET",status="200"} 5.0
# ... more metrics ...
```

## Complete Test Script

Save this as `test_api_complete.sh` and run it:

```bash
#!/bin/bash

KEYCLOAK_URL="http://localhost:8080"
API_URL="https://localhost:8443"
CLIENT_ID="health-api"
CLIENT_SECRET="<your-client-secret>"

echo "[*] Getting editor token..."
EDITOR_TOKEN=$(curl -s -X POST \
  $KEYCLOAK_URL/realms/health/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "username=lab_editor" \
  -d "password=editor123" \
  -d "grant_type=password" \
  | jq -r '.access_token')

echo "[+] Creating patient record..."
curl -s -X POST \
  $API_URL/records \
  -k \
  -H "Authorization: Bearer $EDITOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "test_patient_'$(date +%s)'",
    "name": "Test Patient",
    "dob": "1990-01-01",
    "consent": true
  }' | jq '.'

echo "[+] Getting viewer token..."
VIEWER_TOKEN=$(curl -s -X POST \
  $KEYCLOAK_URL/realms/health/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "username=lab_viewer" \
  -d "password=viewer123" \
  -d "grant_type=password" \
  | jq -r '.access_token')

echo "[+] Getting all records as viewer..."
curl -s -X GET \
  $API_URL/records \
  -k \
  -H "Authorization: Bearer $VIEWER_TOKEN" | jq '.'

echo "[+] Test complete!"
```

Run it:

```bash
chmod +x test_api_complete.sh
./test_api_complete.sh
```

## Troubleshooting

### "Connection refused"
- Ensure the API is running: `python app/server.py` or `docker compose up`
- Check port 8443 is accessible: `netstat -an | grep 8443`

### "SSL: CERTIFICATE_VERIFY_FAILED"
- This is expected for self-signed certs. The curl `-k` flag bypasses verification (demo only!)

### "Invalid token"
- Verify the token hasn't expired (tokens expire after ~1 hour by default)
- Get a fresh token

### "Forbidden" when viewer tries to create
- This is expected! Viewers only have read access. Try with an editor token.

### Token claims are empty
- Ensure roles are properly assigned in Keycloak
- Regenerate tokens after role assignments
