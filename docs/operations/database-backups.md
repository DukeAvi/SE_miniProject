# Database backup and recovery operations

This runbook implements BBMS-NF-006 / DS-NF-006 and TC-DR-01. The configured demonstration retention is seven days, approved in OI-8. Backup and restore records must be synthetic or otherwise approved for the environment; never attach production data or credentials to a pull request.

## Deployment configuration

The optional Compose `backup` profile runs two separate, non-root PostgreSQL 16 clients: `backup-worker` creates and verifies a daily full custom-format dump, while `backup-watchdog` checks backup freshness independently every five minutes. Docker's `unless-stopped` restart policy restarts either process after a failure. The database host is not used to store backup files.

Before enabling the profile, configure these values through the deployment's secret/configuration manager:

- `BACKUP_S3_BUCKET`: dedicated object-storage bucket in a separate failure domain from the database host.
- `BACKUP_S3_ENDPOINT_URL`: omit for AWS S3; otherwise use the provider's HTTPS endpoint. The endpoint cannot be the database host or localhost.
- `BACKUP_ENCRYPTION_KEY`: URL-safe base64 encoding of exactly 32 random bytes. Generate it with `python -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"`, then place it directly into the secret manager. Keep a separately protected recovery copy; losing this key makes backups unrecoverable. Rotate it only with an explicit key-version/migration plan.
- `BACKUP_ALERT_WEBHOOK_URL`: HTTPS receiver that routes backup-freshness alerts to the operations team. The webhook receives only the alert name, status, and a static sanitized message.
- `BACKUP_ALERT_WEBHOOK_BEARER_TOKEN`: optional receiver token, supplied through the secret manager.
- AWS SDK credentials or workload identity with only `s3:ListBucket`, `s3:GetBucketVersioning`, `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, and `s3:ListBucketVersions` permissions for the dedicated bucket/prefix. For versioned buckets, also grant `s3:DeleteObjectVersion` so the seven-day policy removes noncurrent archive and marker versions. Do not grant access to application source data or unrelated buckets.
- `BACKUP_RETENTION_DAYS`: defaults to the OI-8 value of `7`.

Enable and inspect the workers:

```text
docker compose --profile backup up -d --build backup-worker backup-watchdog
docker compose --profile backup ps backup-worker backup-watchdog
docker compose --profile backup logs --since 24h backup-worker backup-watchdog
```

Use bucket policy to deny non-TLS requests and enable the provider's encryption-at-rest controls in addition to the client-side AES-256-GCM encryption. The uploaded `.dump.enc` object is encrypted before it leaves the backup container. A sanitized `.json` success marker is written only after the object is downloaded again, its SHA-256 digest matches, decryption/authentication succeeds, and `pg_restore --list` validates the archive. Freshness checks use only these success markers. Retention deletes archives and their markers after seven days.

The worker attempts its full `pg_dump` at 02:00 UTC daily. If it fails, it retries every 15 minutes until that day's backup succeeds. The independent watchdog checks every five minutes and sends the configured HTTPS alert if there is no verified backup newer than 25 hours, including when the bucket has no successful backup. Delivery failures are logged as sanitized static errors and retried by later checks.

## Manual backup and status checks

```text
docker compose --profile backup run --rm --entrypoint python3 backup-worker scripts/db_backup.py backup
docker compose --profile backup run --rm --entrypoint python3 backup-worker scripts/db_backup.py check-freshness
```

The command prints only the storage object key or a sanitized result. It never prints the encryption key, database password, or webhook token. Do not use shell tracing (`set -x`) for operational commands.

## Restore drill and recovery

1. Provision an isolated spare PostgreSQL 16 environment with an empty target database and network access to the configured object store. Do not point it at the production source host.
2. Select a verified `.dump.enc` object from the dedicated bucket. Confirm the matching `.json` marker exists.
3. Set `BACKUP_RESTORE_SPARE_CONFIRMED=true`, `BACKUP_RESTORE_TARGET_HOST`, `BACKUP_RESTORE_TARGET_PORT`, `BACKUP_RESTORE_TARGET_DB`, `BACKUP_RESTORE_TARGET_USER`, and `BACKUP_RESTORE_TARGET_PASSWORD` through the secret manager. The command refuses the source database host and refuses to run without explicit spare-target confirmation.
4. Run the restore using the same protected encryption key:

```text
docker compose --profile backup run --rm --entrypoint python3 backup-worker scripts/db_backup.py restore bbms-backups/YYYY/MM/DD/<backup-id>.dump.enc
```

The restore verifies the uploaded-object SHA-256 metadata, authenticates and decrypts the AES-GCM archive, validates its PostgreSQL archive catalog, confirms that the target contains no user tables/views/sequences, and runs `pg_restore --exit-on-error --single-transaction --clean --if-exists --no-owner --no-privileges` against the configured spare database. The command never drops the database itself and will refuse a target containing user relations. Follow with application-specific record-count, foreign-key, and representative workflow checks. Store the sanitized elapsed time, object timestamp/key, row-count comparison, and verification result in the private operational evidence location. Use an isolated spare database, not a shared development or production database.

The automated GitHub Actions recovery drill creates synthetic rows on one PostgreSQL 16 container, stores an encrypted full dump in a temporary MinIO container on a separate network service, and restores into a second PostgreSQL 16 container. It verifies the restored values. This exercises the backup/restore code and storage protocol; it does not verify production IAM, offsite provider durability, alert routing, or the four-hour production recovery-time objective. Operators must perform and time TC-DR-01 in the deployment environment and retain sanitized evidence before claiming those production checks.

## Failure handling

- A failed dump, upload, download, digest check, decryption, archive inspection, marker write, or retention operation exits the backup command with a non-zero result; no success marker is written before all integrity checks pass.
- The scheduler records only a static failure message and retries the daily backup in 15 minutes.
- The watchdog alerts when no verified backup is within the 25-hour recovery point objective; it retries alert delivery every five minutes.
- If object storage or alert delivery is unavailable, resolve the provider/network/receiver issue and run the manual status and backup commands. Do not copy encryption keys or database credentials into logs or tickets.
- A host outage also takes down local watchdog containers. Production must configure the host/container platform to alert on stopped backup services and use a monitoring/alert destination outside the database host's failure domain.
