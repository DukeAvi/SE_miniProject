#!/usr/bin/env bash
set -euo pipefail

suffix="${GITHUB_RUN_ID:-local}-$$"
network="bbms-backup-drill-${suffix}"
source="bbms-backup-source-${suffix}"
spare="bbms-backup-spare-${suffix}"
minio="bbms-backup-minio-${suffix}"
image="bbms-backup-drill:${suffix}"
password="ci-drill-password"
access_key="bbmsdrill"
secret_key="bbms-drill-secret"
key="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="

cleanup() {
  docker rm -f "$source" "$spare" "$minio" >/dev/null 2>&1 || true
  docker network rm "$network" >/dev/null 2>&1 || true
  docker image rm "$image" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create "$network" >/dev/null
docker run -d --name "$source" --network "$network" -e POSTGRES_DB=bbms -e POSTGRES_USER=bbms -e POSTGRES_PASSWORD="$password" postgres:16-alpine >/dev/null
docker run -d --name "$spare" --network "$network" -e POSTGRES_DB=bbms -e POSTGRES_USER=bbms -e POSTGRES_PASSWORD="$password" postgres:16-alpine >/dev/null
docker run -d --name "$minio" --network "$network" -e MINIO_ROOT_USER="$access_key" -e MINIO_ROOT_PASSWORD="$secret_key" minio/minio:RELEASE.2025-02-07T23-21-09Z server /data >/dev/null
docker build -f deployment/backup/Dockerfile -t "$image" . >/dev/null

ready=false
for attempt in $(seq 1 60); do
  if docker exec "$source" pg_isready -U bbms -d bbms >/dev/null 2>&1 \
    && docker exec "$spare" pg_isready -U bbms -d bbms >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 2
done
test "$ready" = true

docker run --rm --network "$network" --entrypoint python3 \
  -e BACKUP_S3_BUCKET=bbms-backups -e BACKUP_S3_ENDPOINT_URL="http://$minio:9000" -e BACKUP_ALLOW_HTTP_STORAGE=true \
  -e AWS_ACCESS_KEY_ID="$access_key" -e AWS_SECRET_ACCESS_KEY="$secret_key" -e AWS_DEFAULT_REGION=us-east-1 \
  "$image" scripts/init_backup_drill_storage.py

docker exec -e PGPASSWORD="$password" "$source" psql -v ON_ERROR_STOP=1 -U bbms -d bbms \
  -c 'CREATE TABLE recovery_probe (id integer PRIMARY KEY, marker text NOT NULL); INSERT INTO recovery_probe VALUES (1, '\''restored-record'\'');' >/dev/null
backup_output="$(docker run --rm --network "$network" --entrypoint python3 \
  -e POSTGRES_HOST="$source" -e POSTGRES_PORT=5432 -e POSTGRES_DB=bbms -e POSTGRES_USER=bbms -e POSTGRES_PASSWORD="$password" \
  -e BACKUP_S3_BUCKET=bbms-backups -e BACKUP_S3_ENDPOINT_URL="http://$minio:9000" -e BACKUP_ALLOW_HTTP_STORAGE=true \
  -e BACKUP_ENCRYPTION_KEY="$key" -e AWS_ACCESS_KEY_ID="$access_key" -e AWS_SECRET_ACCESS_KEY="$secret_key" -e AWS_DEFAULT_REGION=us-east-1 \
  "$image" scripts/db_backup.py backup)"
printf '%s\n' "$backup_output"
object_key="${backup_output##* }"
case "$object_key" in bbms-backups/*.dump.enc) ;; *) echo "backup drill did not return a backup key" >&2; exit 1 ;; esac

drill_started="$(date +%s)"
docker run --rm --network "$network" --entrypoint python3 \
  -e POSTGRES_HOST="$source" -e POSTGRES_DB=bbms -e POSTGRES_USER=bbms -e POSTGRES_PASSWORD="$password" \
  -e BACKUP_S3_BUCKET=bbms-backups -e BACKUP_S3_ENDPOINT_URL="http://$minio:9000" -e BACKUP_ALLOW_HTTP_STORAGE=true \
  -e BACKUP_ENCRYPTION_KEY="$key" -e AWS_ACCESS_KEY_ID="$access_key" -e AWS_SECRET_ACCESS_KEY="$secret_key" \
  -e BACKUP_RESTORE_SPARE_CONFIRMED=true -e BACKUP_RESTORE_TARGET_HOST="$spare" -e BACKUP_RESTORE_TARGET_DB=bbms \
  -e BACKUP_RESTORE_TARGET_USER=bbms -e BACKUP_RESTORE_TARGET_PASSWORD="$password" \
  "$image" scripts/db_backup.py restore "$object_key"

restored="$(docker exec -e PGPASSWORD="$password" "$spare" psql -v ON_ERROR_STOP=1 -U bbms -d bbms -Atc 'SELECT marker FROM recovery_probe WHERE id = 1')"
test "$restored" = "restored-record"
drill_seconds=$(( $(date +%s) - drill_started ))
test "$drill_seconds" -le 14400
echo "TC-DR-01 CI drill passed: synthetic data restored with verified integrity in ${drill_seconds}s (limit 14400s)."
