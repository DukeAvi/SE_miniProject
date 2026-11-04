#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
temp_root="$(mktemp -d)"
project="bbms-tls-ci-${GITHUB_RUN_ID:-local}"
postgres_tls_dir="$temp_root/postgres-tls"
public_tls_dir="$temp_root/public-tls"
mkdir -p "$postgres_tls_dir" "$public_tls_dir"

cleanup() {
  docker compose -p "$project" -f "$repo_root/compose.yaml" -f "$repo_root/compose.secure.yaml" down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$temp_root"
}
trap cleanup EXIT

openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 2 \
  -keyout "$temp_root/ca.key" -out "$temp_root/ca.crt" \
  -subj "/CN=BBMS CI TLS Test CA" >/dev/null 2>&1
openssl req -newkey rsa:2048 -nodes -keyout "$temp_root/server.key" \
  -out "$temp_root/server.csr" -subj "/CN=localhost" >/dev/null 2>&1
cat > "$temp_root/server.ext" <<'EOF'
subjectAltName=DNS:localhost,DNS:db
extendedKeyUsage=serverAuth
keyUsage=digitalSignature,keyEncipherment
EOF
openssl x509 -req -in "$temp_root/server.csr" -CA "$temp_root/ca.crt" \
  -CAkey "$temp_root/ca.key" -CAcreateserial -days 2 -sha256 \
  -extfile "$temp_root/server.ext" -out "$temp_root/server.crt" >/dev/null 2>&1

cp "$temp_root/ca.crt" "$postgres_tls_dir/ca.crt"
cp "$temp_root/server.crt" "$postgres_tls_dir/server.crt"
cp "$temp_root/server.key" "$postgres_tls_dir/server.key"
chmod 600 "$postgres_tls_dir/server.key"
postgres_uid="$(docker run --rm postgres:16-alpine id -u postgres)"
postgres_gid="$(docker run --rm postgres:16-alpine id -g postgres)"
sudo chown "$postgres_uid:$postgres_gid" "$postgres_tls_dir/server.key"
cp "$temp_root/ca.crt" "$public_tls_dir/ca.crt"
cp "$temp_root/server.crt" "$public_tls_dir/fullchain.pem"
cp "$temp_root/server.key" "$public_tls_dir/privkey.pem"

export POSTGRES_TLS_DIR="$postgres_tls_dir"
export BBMS_TLS_DIR="$public_tls_dir"
export BBMS_PUBLIC_HOSTNAME=localhost
export POSTGRES_PASSWORD=ci-only-tls-password
export DJANGO_SECRET_KEY=ci-only-tls-test-key
export DJANGO_ALLOWED_HOSTS=localhost
export DJANGO_DEBUG=false

docker compose -p "$project" -f "$repo_root/compose.yaml" -f "$repo_root/compose.secure.yaml" config --quiet
echo "Compose TLS deployment configuration validated"
docker compose -p "$project" -f "$repo_root/compose.yaml" -f "$repo_root/compose.secure.yaml" build edge
if docker compose -p "$project" -f "$repo_root/compose.yaml" -f "$repo_root/compose.secure.yaml" \
  run --rm --no-deps -e 'BBMS_PUBLIC_HOSTNAME=localhost;id' edge >/dev/null 2>&1; then
  echo "Nginx accepted an invalid public hostname" >&2
  exit 1
fi
echo "Nginx hostname validation rejects malformed input"
docker compose -p "$project" -f "$repo_root/compose.yaml" -f "$repo_root/compose.secure.yaml" up --build -d db redis web edge

for attempt in $(seq 1 60); do
  if curl --silent --show-error --fail --resolve localhost:443:127.0.0.1 \
    --cacert "$public_tls_dir/ca.crt" https://localhost/healthz >/dev/null 2>&1; then
    break
  fi
  if [ "$attempt" -eq 60 ]; then
    echo "TLS deployment health probe did not become ready" >&2
    exit 1
  fi
  sleep 2
done
echo "TLS edge and application health endpoint are ready"

curl --silent --show-error --fail --resolve localhost:443:127.0.0.1 \
  --cacert "$public_tls_dir/ca.crt" --tlsv1.2 --tls-max 1.2 \
  -D "$temp_root/https.headers" https://localhost/healthz -o "$temp_root/health.json"
grep -Eq '"status"[[:space:]]*:[[:space:]]*"ok"' "$temp_root/health.json"
grep -qi '^Strict-Transport-Security: max-age=31536000; includeSubDomains' "$temp_root/https.headers"
grep -qi '^X-Content-Type-Options: nosniff' "$temp_root/https.headers"
grep -qi '^X-Frame-Options: DENY' "$temp_root/https.headers"
grep -qi '^Referrer-Policy: strict-origin-when-cross-origin' "$temp_root/https.headers"
grep -qi '^Content-Security-Policy:' "$temp_root/https.headers"
echo "TLS 1.2 and application security headers verified"

curl --silent --show-error --fail --resolve localhost:443:127.0.0.1 \
  --cacert "$public_tls_dir/ca.crt" --tlsv1.3 --tls-max 1.3 \
  https://localhost/healthz >/dev/null
echo "TLS 1.3 verified"

curl --silent --show-error --output /dev/null --dump-header "$temp_root/http.headers" \
  -H 'Host: localhost' http://127.0.0.1/healthz
grep -qi '^HTTP/1.1 308' "$temp_root/http.headers"
grep -qi '^Location: https://localhost/healthz' "$temp_root/http.headers"
echo "HTTP redirects to the configured HTTPS hostname"

if openssl s_client -connect 127.0.0.1:443 -servername localhost -tls1 \
  -cipher 'DEFAULT:@SECLEVEL=0' -brief -verify_return_error \
  -CAfile "$public_tls_dir/ca.crt" </dev/null >/dev/null 2>&1; then
  echo "TLS 1.0 unexpectedly negotiated" >&2
  exit 1
fi
echo "TLS 1.0 and TLS 1.1 rejected"
if openssl s_client -connect 127.0.0.1:443 -servername localhost -tls1_1 \
  -cipher 'DEFAULT:@SECLEVEL=0' -brief -verify_return_error \
  -CAfile "$public_tls_dir/ca.crt" </dev/null >/dev/null 2>&1; then
  echo "TLS 1.1 unexpectedly negotiated" >&2
  exit 1
fi
echo "TLS 1.0 and TLS 1.1 rejected"

docker compose -p "$project" -f "$repo_root/compose.yaml" -f "$repo_root/compose.secure.yaml" \
  exec -T web python manage.py shell -c '
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT ssl, version FROM pg_stat_ssl WHERE pid = pg_backend_pid()")
    encrypted, version = cursor.fetchone()
assert encrypted and version in {"TLSv1.2", "TLSv1.3"}, (encrypted, version)
print(f"PostgreSQL transport verified: {version}, encrypted=True")
'
echo "PostgreSQL hostname and CA verification succeeded"
query='from django.db import connection; connection.ensure_connection()'
if docker compose -p "$project" -f "$repo_root/compose.yaml" -f "$repo_root/compose.secure.yaml" \
  exec -T -e POSTGRES_HOST=untrusted-database-name web python manage.py shell -c "$query" \
  >/dev/null 2>&1; then
  echo "PostgreSQL accepted a certificate hostname mismatch" >&2
  exit 1
fi
if docker compose -p "$project" -f "$repo_root/compose.yaml" -f "$repo_root/compose.secure.yaml" \
  exec -T -e POSTGRES_SSLMODE=disable web python manage.py shell -c "$query" \
  >/dev/null 2>&1; then
  echo "PostgreSQL accepted a plaintext connection" >&2
  exit 1
fi

echo "TLS deployment integration passed: HTTPS 200, HTTP redirect, security headers, TLS 1.2/1.3 accepted, TLS 1.0/1.1 rejected, PostgreSQL verified TLS."
