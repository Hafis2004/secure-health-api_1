# TLS Verification Commands

This guide shows how to verify that TLS/HTTPS is working correctly on the Secure Health API running on port 8443.

## Prerequisites

- OpenSSL installed (comes with most Linux/Mac systems; on Windows, use Git Bash or WSL)
- curl installed
- API running on `https://localhost:8443`
- Self-signed certificate at `certs/server.crt` and `certs/server.key`

## Method 1: OpenSSL s_client

### Basic TLS Handshake Check

The `openssl s_client` command performs a full TLS handshake and shows certificate details:

```bash
openssl s_client -connect localhost:8443
```

**What to look for:**

```
CONNECTED(00000003)
depth=0 CN = localhost
verify error:num=18:self signed certificate
verify return:1
depth=0 CN = localhost
verify return:1
---
Certificate chain
 0 s:CN = localhost
   i:CN = localhost
subject=CN = localhost
issuer=CN = localhost
---
SSL-Session:
    Protocol  : TLSv1.2 (or TLSv1.3)
    Cipher    : ECDHE-RSA-AES256-GCM-SHA384 (or similar)
    Start Time: <timestamp>
    Timeout   : 300 (sec)
    Verify return code: 18 (self signed certificate)
```

**Indicators of Success:**
- `CONNECTED(00000003)` - Connection established
- `depth=0 CN = localhost` - Certificate found
- `Protocol  : TLSv1.2` or higher - TLS protocol negotiated
- `Cipher : ...` - Encryption cipher negotiated
- No fatal errors preventing connection

### Interactive S_client Session

To interact with the API via openssl:

```bash
openssl s_client -connect localhost:8443 -quiet
```

Then type HTTP requests directly:

```
GET /records/patient123 HTTP/1.1
Host: localhost:8443
Authorization: Bearer <your-token>

```

(Press Enter twice to send the request)

### Extract and View Certificate Details

```bash
openssl s_client -connect localhost:8443 -showcerts < /dev/null 2>/dev/null | openssl x509 -text -noout
```

**What to look for:**

```
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: ...
        Signature Algorithm: sha256WithRSAEncryption
        Issuer: CN = localhost
        Subject: CN = localhost
        Validity
            Not Before: ... (check current date is after this)
            Not After : ... (check current date is before this)
        Public Key Algorithm: rsaEncryption
        Public-Key: (2048 bit)
X509v3 extensions:
    X509v3 Key Usage: 
        Digital Signature, Key Encipherment
    X509v3 Extended Key Usage: 
        TLS Web Server Authentication
    X509v3 Subject Alternative Name: 
        DNS:localhost, DNS:127.0.0.1
```

## Method 2: OpenSSL Version and Capabilities Check

```bash
# Check OpenSSL version
openssl version -a

# List available ciphers
openssl ciphers -v 'HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA'
```

## Method 3: Using Curl with Verbose Output

### Full TLS Handshake Trace

```bash
curl -v -k https://localhost:8443/records/patient123 \
  -H "Authorization: Bearer <your-token>"
```

**Output includes:**

```
*   Trying 127.0.0.1:8443...
* Connected to localhost (127.0.0.1) port 8443 (#0)
* ALPN, offering h2
* ALPN, offering http/1.1
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
* TLSv1.3 (IN), TLS handshake, Server hello (2):
* TLSv1.3 (IN), TLS handshake, Encrypted Extensions (8):
* TLSv1.3 (IN), TLS handshake, Certificate (11):
* TLSv1.3 (IN), TLS handshake, Certificate verify (15):
* TLSv1.3 (IN), TLS handshake, Finished (20):
* TLSv1.3 (OUT), TLS handshake, Finished (20):
* SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384
* ALPN, server accepted to use h2
> GET /records/patient123 HTTP/1.1
> Host: localhost:8443
> User-Agent: curl/7.x.x
> Authorization: Bearer eyJ...
>
< HTTP/2 200
< content-type: application/json
< 
* Connection #0 to host localhost kept alive
```

**What to look for:**

- `Connected to localhost (127.0.0.1) port 8443 (#0)` - Connection successful
- `TLSv1.2` or `TLSv1.3` - TLS version established
- `SSL connection using TLSv1.3 ...` - TLS negotiation successful
- `> GET /records/patient123 HTTP/1.1` - HTTPS request sent
- `< HTTP/2 200` or `< HTTP/1.1 200` - Server response

### Check Certificate Fingerprint

```bash
curl -k https://localhost:8443/records -I 2>&1 | grep "SSL certificate"

# Or extract and show fingerprint:
echo | openssl s_client -connect localhost:8443 2>/dev/null | openssl x509 -noout -fingerprint -sha256
```

**Output:**

```
sha256 Fingerprint=AA:BB:CC:DD:...:XX:YY:ZZ
```

## Method 4: Using Python

Verify TLS programmatically:

```python
import ssl
import socket

def check_tls():
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    with socket.create_connection(("localhost", 8443), timeout=5) as sock:
        with context.wrap_socket(sock, server_hostname="localhost") as ssock:
            print(f"TLS Version: {ssock.version}")
            print(f"Cipher Suite: {ssock.cipher()}")
            cert = ssock.getpeercert()
            print(f"Certificate Subject: {cert.get('subject')}")
            print(f"Certificate Issued: {cert.get('notBefore')}")
            print(f"Certificate Expires: {cert.get('notAfter')}")

check_tls()
```

## Method 5: Using Nmap NSE

If nmap is installed:

```bash
nmap --script ssl-enum-ciphers -p 8443 localhost
```

**Output:**

```
| ssl-enum-ciphers: 
|   TLSv1.2: 
|     ciphers: 
|       TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384 (ecdh_x25519) - A
|       ...
|   TLSv1.3: 
|     ciphers: 
|       TLS_AES_256_GCM_SHA384 (ecdh_x25519) - A
```

## Full Diagnostic Script

Save this as `test_tls.sh`:

```bash
#!/bin/bash

echo "=== TLS/HTTPS Verification for Secure Health API ==="
echo ""

API_HOST="localhost"
API_PORT="8443"
API_URL="https://$API_HOST:$API_PORT"

# Test 1: Basic connectivity
echo "[1] Testing basic TCP connection..."
if nc -zv $API_HOST $API_PORT 2>/dev/null; then
    echo "    ✓ Port $API_PORT is open"
else
    echo "    ✗ Cannot connect to port $API_PORT"
    exit 1
fi

# Test 2: TLS handshake
echo ""
echo "[2] Performing TLS handshake..."
if timeout 5 openssl s_client -connect $API_HOST:$API_PORT < /dev/null 2>/dev/null | \
   openssl x509 -noout -text > /dev/null 2>&1; then
    echo "    ✓ TLS handshake successful"
else
    echo "    ✗ TLS handshake failed"
    exit 1
fi

# Test 3: Certificate validation
echo ""
echo "[3] Validating certificate..."
CERT_CN=$(echo | openssl s_client -connect $API_HOST:$API_PORT 2>/dev/null | \
          openssl x509 -noout -subject | grep -oP '(?<=CN=)[^/,]+')
echo "    Certificate CN: $CERT_CN"

CERT_ISSUER=$(echo | openssl s_client -connect $API_HOST:$API_PORT 2>/dev/null | \
              openssl x_509 -noout -issuer | grep -oP '(?<=CN=)[^/,]+')
echo "    Certificate Issuer: $CERT_ISSUER"

# Test 4: TLS Version
echo ""
echo "[4] Checking TLS version..."
TLS_VERSION=$(echo | openssl s_client -connect $API_HOST:$API_PORT 2>/dev/null | \
              grep "Protocol" | awk '{print $NF}')
echo "    TLS Version: $TLS_VERSION"

# Test 5: Cipher Suite
echo ""
echo "[5] Checking cipher suite..."
CIPHER=$(echo | openssl s_client -connect $API_HOST:$API_PORT 2>/dev/null | \
         grep "Cipher" | awk '{$1=$2=""; print $0}')
echo "    Cipher: $CIPHER"

# Test 6: HTTP/HTTPS response
echo ""
echo "[6] Testing HTTPS API response..."
RESPONSE=$(curl -s -k -I $API_URL/metrics 2>&1)
if echo "$RESPONSE" | grep -q "HTTP"; then
    HTTP_STATUS=$(echo "$RESPONSE" | head -1)
    echo "    ✓ API responded: $HTTP_STATUS"
else
    echo "    ✗ No HTTP response from API"
    exit 1
fi

echo ""
echo "=== All TLS checks passed! ==="
```

Run it:

```bash
chmod +x test_tls.sh
./test_tls.sh
```

## Expected Results

When TLS is working correctly:

1. ✓ Port 8443 is open and responding
2. ✓ TLS handshake completes without errors
3. ✓ Certificate is from "localhost" (CN = localhost)
4. ✓ TLS version is 1.2 or higher
5. ✓ Cipher suite is strong (AES-256-GCM or TLS 1.3)
6. ✓ HTTPS requests return valid HTTP responses (200, 401, 403, etc.)
7. ✓ Certificate is self-signed (expected for demo)

## Security Considerations

- **Self-signed certificates** are used for demo/development. In production:
  - Use certificates signed by a trusted CA
  - Implement strict certificate pinning
  - Disable `-k` flag in curl

- **TLS Version**: Should be 1.2 or higher (1.3 preferred)

- **Cipher Suites**: Should use strong ciphers (AES-256-GCM)

- **HSTS**: Consider adding Strict-Transport-Security headers

- **Certificate Rotation**: Set up automated certificate renewal (e.g., Let's Encrypt)

## Troubleshooting

### "Connection refused"
```bash
# Ensure API is running
docker compose logs app
# or
python app/server.py
```

### "SSL_ERROR_BAD_CERT_DOMAIN"
```bash
# Expected for localhost on self-signed cert
# Always use curl -k flag
```

### "SSL: SSLV3_ALERT_UNEXPECTED_MESSAGE"
```bash
# Try different TLS version:
openssl s_client -connect localhost:8443 -tls1_3
openssl s_client -connect localhost:8443 -tls1_2
```

### Certificate verification errors
```bash
# Check certificate validity dates
echo | openssl s_client -connect localhost:8443 2>/dev/null | \
openssl x509 -noout -dates
```

### "Cipher issue"
```bash
# Check available ciphers on your system
openssl ciphers -v
```
