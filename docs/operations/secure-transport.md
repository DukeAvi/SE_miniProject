# Secure transport deployment

This is the internet-facing deployment configuration for BBMS-SR-001 / DS-SR-001 and TC-Sec-01. The base `compose.yaml` is a local, private development stack: it does not publish Gunicorn and intentionally has development-only HTTP settings. Do not expose its `web` container or replace the secure overlay with a direct port mapping.

## Required TLS material

Configure `BBMS_PUBLIC_HOSTNAME`, `BBMS_TLS_DIR`, and `POSTGRES_TLS_DIR` with the secret/configuration manager. Do not add certificate private keys to the repository.

- `BBMS_TLS_DIR/fullchain.pem` and `privkey.pem`: the public certificate chain and private key for the public hostname. The certificate must be valid for `BBMS_PUBLIC_HOSTNAME` and renewed before expiry.
- `POSTGRES_TLS_DIR/server.crt` and `server.key`: a PostgreSQL server certificate whose SAN contains `db`; protect the private key so it is readable by the PostgreSQL container user only.
- `POSTGRES_TLS_DIR/ca.crt`: the trusted CA certificate that issued the PostgreSQL certificate. The same file is mounted read-only into the web, worker, Beat, and backup-worker containers.

Use separate keys for the public edge and PostgreSQL. Use certificate rotation procedures that safely reload/restart the affected containers. PostgreSQL TLS certificates must be issued by an internal CA if the database service name is not covered by a public CA certificate.

The secure overlay sets Django HTTPS redirects, trusted-proxy handling, one-year HSTS with subdomains, secure session/CSRF cookies, and CSRF trusted origins. Nginx listens on ports 80 and 443; port 80 returns a fixed-host 308 redirect and port 443 accepts TLS 1.2 or TLS 1.3 only. Nginx rejects malformed host configuration at startup, disables server tokens, and sends HSTS, CSP (from Django), content-type, frame, referrer, and permissions headers. The Gunicorn service has no published host port.

PostgreSQL is configured with TLS enabled, TLS 1.2 as the minimum protocol, and a `pg_hba.conf` that rejects every non-TLS TCP connection. Django and Celery clients use `sslmode=verify-full`, the configured CA, and the `db` hostname, so they fail closed on plaintext, untrusted certificates, and hostname mismatch. Django settings reject `allow`, `prefer`, and `require` libpq modes because they do not verify the database identity. `disable` is retained only for the local/test database configuration; the secure overlay always overrides it with `verify-full`.

## Start and verify

After setting the required secrets and environment values:

```text
docker compose -f compose.yaml -f compose.secure.yaml config --quiet
docker compose -f compose.yaml -f compose.secure.yaml up -d --build
docker compose -f compose.yaml -f compose.secure.yaml ps
```

Open only ports 80 and 443 at the external firewall. The edge redirects HTTP and serves HTTPS. Keep the database, Redis, and Gunicorn services on the private Compose network. The CI script `scripts/test_tls_deployment.sh` creates ephemeral test certificates and verifies the real Nginx and PostgreSQL containers: redirect behavior, security headers, TLS 1.2/1.3 success, TLS 1.0/1.1 rejection, and an authenticated Django-to-PostgreSQL query using verified TLS. CI certificates and databases are disposable synthetic test data and are not production evidence.

For production, run the transport portion of TC-Sec-01 against the actual public hostname and database network after deployment. Retain a sanitized report of the negotiated public TLS protocol/cipher, HTTP redirect, response headers, certificate validity/renewal status, and PostgreSQL `pg_stat_ssl` verification. Do not include private keys, credentials, or customer data in the report.
