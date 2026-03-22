# Keycloak Setup Instructions for Secure Health API

This guide provides step-by-step curl commands to set up Keycloak with the "health" realm, clients, roles, and users for the secure healthcare microservices project.

## Prerequisites

- Keycloak 24.0 running on `http://localhost:8080`
- Initial admin credentials: `admin` / `admin`
- `curl` CLI tool available

## Step 1: Get Admin Access Token

First, obtain an admin token to make API calls:

```bash
ADMIN_TOKEN=$(curl -s -X POST \
  http://localhost:8080/realms/master/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=admin" \
  -d "grant_type=password" \
  | jq -r '.access_token')

echo "Admin Token: $ADMIN_TOKEN"
```

Store this token for use in subsequent commands:

```bash
export ADMIN_TOKEN=$ADMIN_TOKEN
```

## Step 2: Create the "health" Realm

```bash
curl -X POST \
  http://localhost:8080/admin/realms \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "realm": "health",
    "enabled": true,
    "displayName": "Healthcare Realm",
    "duplicateEmailsAllowed": false,
    "resetPasswordAllowed": true,
    "editUsernameAllowed": true,
    "bruteForceProtected": true,
    "loginWithEmailAllowed": true
  }'

echo "Realm 'health' created successfully"
```

## Step 3: Create the "health-api" Client

```bash
HEALTH_API_CLIENT=$(curl -s -X POST \
  http://localhost:8080/admin/realms/health/clients \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "clientId": "health-api",
    "name": "Health API",
    "enabled": true,
    "clientAuthenticationType": "confidential",
    "directAccessGrantsEnabled": true,
    "standardFlowEnabled": true,
    "serviceAccountsEnabled": true,
    "publicClient": false,
    "redirectUris": [
      "http://localhost:8443/*",
      "http://localhost:5001/*"
    ],
    "webOrigins": [
      "*"
    ]
  }' | jq -r '.id')

echo "Client 'health-api' created with ID: $HEALTH_API_CLIENT"
export HEALTH_API_CLIENT=$HEALTH_API_CLIENT
```

## Step 4: Get Client Secret

```bash
CLIENT_SECRET=$(curl -s -X GET \
  http://localhost:8080/admin/realms/health/clients/$HEALTH_API_CLIENT/client-secret \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq -r '.value')

echo "Client Secret: $CLIENT_SECRET"
export CLIENT_SECRET=$CLIENT_SECRET
```

## Step 5: Create Realm Roles

### Create "viewer" Role

```bash
curl -X POST \
  http://localhost:8080/admin/realms/health/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "viewer",
    "description": "Read-only access to patient records"
  }'

echo "Role 'viewer' created"
```

### Create "editor" Role

```bash
curl -X POST \
  http://localhost:8080/admin/realms/health/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "editor",
    "description": "Read and write access to patient records"
  }'

echo "Role 'editor' created"
```

## Step 6: Create Users and Assign Roles

### Create "lab_viewer" User with Viewer Role

```bash
# Create user
LAB_VIEWER_USER=$(curl -s -X POST \
  http://localhost:8080/admin/realms/health/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "lab_viewer",
    "email": "viewer@hospital.local",
    "firstName": "Lab",
    "lastName": "Viewer",
    "enabled": true,
    "attributes": {
      "department": ["Laboratory"]
    }
  }' | jq -r '.id')

echo "User 'lab_viewer' created with ID: $LAB_VIEWER_USER"

# Set password for lab_viewer
curl -X PUT \
  http://localhost:8080/admin/realms/health/users/$LAB_VIEWER_USER/reset-password \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "password",
    "value": "viewer123",
    "temporary": false
  }'

echo "Password set for lab_viewer: viewer123"

# Get viewer role ID
VIEWER_ROLE_ID=$(curl -s -X GET \
  http://localhost:8080/admin/realms/health/roles/viewer \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq -r '.id')

# Assign viewer role to lab_viewer
curl -X POST \
  http://localhost:8080/admin/realms/health/users/$LAB_VIEWER_USER/role-mappings/realm \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "[{
    \"id\": \"$VIEWER_ROLE_ID\",
    \"name\": \"viewer\",
    \"composite\": false,
    \"clientRole\": false,
    \"containerId\": \"health\"
  }]"

echo "Role 'viewer' assigned to lab_viewer"
```

### Create "lab_editor" User with Editor Role

```bash
# Create user
LAB_EDITOR_USER=$(curl -s -X POST \
  http://localhost:8080/admin/realms/health/users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "lab_editor",
    "email": "editor@hospital.local",
    "firstName": "Lab",
    "lastName": "Editor",
    "enabled": true,
    "attributes": {
      "department": ["Laboratory"]
    }
  }' | jq -r '.id')

echo "User 'lab_editor' created with ID: $LAB_EDITOR_USER"

# Set password for lab_editor
curl -X PUT \
  http://localhost:8080/admin/realms/health/users/$LAB_EDITOR_USER/reset-password \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "password",
    "value": "editor123",
    "temporary": false
  }'

echo "Password set for lab_editor: editor123"

# Get editor role ID
EDITOR_ROLE_ID=$(curl -s -X GET \
  http://localhost:8080/admin/realms/health/roles/editor \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq -r '.id')

# Assign editor role to lab_editor
curl -X POST \
  http://localhost:8080/admin/realms/health/users/$LAB_EDITOR_USER/role-mappings/realm \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "[{
    \"id\": \"$EDITOR_ROLE_ID\",
    \"name\": \"editor\",
    \"composite\": false,
    \"clientRole\": false,
    \"containerId\": \"health\"
  }]"

echo "Role 'editor' assigned to lab_editor"
```

## Step 7: Get Access Tokens for Users

### Get Token for lab_viewer

```bash
VIEWER_TOKEN=$(curl -s -X POST \
  http://localhost:8080/realms/health/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=health-api" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "username=lab_viewer" \
  -d "password=viewer123" \
  -d "grant_type=password" \
  | jq -r '.access_token')

echo "Viewer Token: $VIEWER_TOKEN"
export VIEWER_TOKEN=$VIEWER_TOKEN
```

### Get Token for lab_editor

```bash
EDITOR_TOKEN=$(curl -s -X POST \
  http://localhost:8080/realms/health/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=health-api" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "username=lab_editor" \
  -d "password=editor123" \
  -d "grant_type=password" \
  | jq -r '.access_token')

echo "Editor Token: $EDITOR_TOKEN"
export EDITOR_TOKEN=$EDITOR_TOKEN
```

## Complete Automation Script

To run all steps at once, save this as `setup_keycloak.sh` and run it:

```bash
#!/bin/bash
set -e

KEYCLOAK_URL="http://localhost:8080"
ADMIN_USER="admin"
ADMIN_PASS="admin"

echo "[*] Getting admin token..."
ADMIN_TOKEN=$(curl -s -X POST \
  $KEYCLOAK_URL/realms/master/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=admin-cli" \
  -d "username=$ADMIN_USER" \
  -d "password=$ADMIN_PASS" \
  -d "grant_type=password" \
  | jq -r '.access_token')

echo "[+] Admin token obtained"

echoo "[*] Creating realm 'health'..."
curl -s -X POST \
  $KEYCLOAK_URL/admin/realms \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"realm":"health","enabled":true}'

echo "[+] Realm created"

echo "[*] Creating client 'health-api'..."
HEALTH_API_CLIENT=$(curl -s -X POST \
  $KEYCLOAK_URL/admin/realms/health/clients \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"clientId":"health-api","name":"Health API","enabled":true,"clientAuthenticationType":"confidential","directAccessGrantsEnabled":true}' \
  | jq -r '.id')

echo "[+] Client created: $HEALTH_API_CLIENT"

echo "[*] Getting client secret..."
CLIENT_SECRET=$(curl -s -X GET \
  $KEYCLOAK_URL/admin/realms/health/clients/$HEALTH_API_CLIENT/client-secret \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq -r '.value')

echo "[+] Client secret: $CLIENT_SECRET"

echo "[*] Creating roles..."
curl -s -X POST \
  $KEYCLOAK_URL/admin/realms/health/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"viewer"}'

curl -s -X POST \
  $KEYCLOAK_URL/admin/realms/health/roles \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"editor"}'

echo "[+] Roles created"

echo "[*] Setup complete!"
echo "Client ID: health-api"
echo "Client Secret: $CLIENT_SECRET"
```

## Verification

To verify the setup works, try logging in:

```bash
curl -X POST http://localhost:8080/realms/health/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=health-api" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "username=lab_viewer" \
  -d "password=viewer123" \
  -d "grant_type=password"
```

You should receive a JSON response with `access_token`, `refresh_token`, etc.
