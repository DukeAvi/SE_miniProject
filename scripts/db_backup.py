"""Encrypted PostgreSQL backup, freshness monitoring, and restore utility."""

from __future__ import annotations

import argparse
import base64
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.parse import urlparse
import uuid

import boto3
from botocore.config import Config
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


MAGIC = b"BBMSBK01"
CHUNK_SIZE = 1024 * 1024
BACKUP_PREFIX = "bbms-backups/"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, _request, _response, _code, _message, _headers, _url):
        return None


def encryption_key(value: str | None = None) -> bytes:
    """Decode a URL-safe base64 256-bit key without ever logging it."""
    value = value if value is not None else os.environ.get("BACKUP_ENCRYPTION_KEY", "")
    try:
        key = base64.b64decode(value.encode("ascii"), altchars=b"-_", validate=True)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("BACKUP_ENCRYPTION_KEY must be URL-safe base64 for 32 bytes") from exc
    if len(key) != 32:
        raise ValueError("BACKUP_ENCRYPTION_KEY must decode to exactly 32 bytes")
    return key


def encrypt_file(source: Path, destination: Path, key: bytes) -> str:
    nonce = os.urandom(12)
    encryptor = Cipher(algorithms.AES(key), modes.GCM(nonce)).encryptor()
    digest = sha256()
    with source.open("rb") as input_file, destination.open("wb") as output_file:
        header = MAGIC + nonce
        output_file.write(header)
        digest.update(header)
        while chunk := input_file.read(CHUNK_SIZE):
            encrypted = encryptor.update(chunk)
            output_file.write(encrypted)
            digest.update(encrypted)
        tail = encryptor.finalize()
        output_file.write(tail)
        digest.update(tail)
        output_file.write(encryptor.tag)
        digest.update(encryptor.tag)
    return digest.hexdigest()


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def decrypt_file(source: Path, destination: Path, key: bytes) -> None:
    size = source.stat().st_size
    if size < len(MAGIC) + 12 + 16:
        raise ValueError("backup archive is truncated")
    with source.open("rb") as input_file:
        header = input_file.read(len(MAGIC) + 12)
        if header[: len(MAGIC)] != MAGIC:
            raise ValueError("backup archive format is not recognized")
        nonce = header[len(MAGIC) :]
        input_file.seek(size - 16)
        tag = input_file.read(16)
        input_file.seek(len(MAGIC) + 12)
        remaining = size - len(MAGIC) - 12 - 16
        decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
        with destination.open("wb") as output_file:
            while remaining:
                chunk = input_file.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    raise ValueError("backup archive is truncated")
                remaining -= len(chunk)
                output_file.write(decryptor.update(chunk))
            output_file.write(decryptor.finalize())


def storage_client():
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        if os.environ.get(name) == "":
            os.environ.pop(name)
    endpoint = os.environ.get("BACKUP_S3_ENDPOINT_URL") or None
    if endpoint and not endpoint.lower().startswith("https://"):
        if not (endpoint.lower().startswith("http://") and os.environ.get("BACKUP_ALLOW_HTTP_STORAGE") == "true"):
            raise ValueError("backup object storage must use HTTPS")
    if endpoint:
        hostname = (urlparse(endpoint).hostname or "").lower()
        if hostname in {"localhost", "127.0.0.1", "::1"} or hostname == os.environ.get("POSTGRES_HOST", "").lower():
            raise ValueError("backup storage must be separate from the database host")
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
        config=Config(
            connect_timeout=10,
            read_timeout=60,
            retries={"max_attempts": 3, "mode": "standard"},
            s3={"addressing_style": "path"},
        ),
    )


def database_env() -> dict[str, str]:
    names = {
        "PGHOST": "POSTGRES_HOST",
        "PGPORT": "POSTGRES_PORT",
        "PGDATABASE": "POSTGRES_DB",
        "PGUSER": "POSTGRES_USER",
        "PGPASSWORD": "POSTGRES_PASSWORD",
    }
    result = pg_tool_environment()
    result.update({target: os.environ[source] for target, source in names.items() if os.environ.get(source)})
    if not all(result.get(name) for name in ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")):
        raise ValueError("PostgreSQL connection settings are incomplete")
    return result


def pg_tool_environment() -> dict[str, str]:
    allowed = {"PATH", "HOME", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR", "PGSERVICE", "PGSERVICEFILE"}
    result = {name: value for name, value in os.environ.items() if name in allowed or name.startswith("PGSSL")}
    result.setdefault("PATH", os.defpath)
    result.setdefault("PGCONNECT_TIMEOUT", "15")
    return result


def run_command(args: list[str], *, env: dict[str, str] | None = None) -> None:
    result = subprocess.run(
        args,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode:
        # Database tools may include connection details in stderr. Emit only an operation label.
        raise RuntimeError(f"{Path(args[0]).name} failed with exit status {result.returncode}")


def bucket() -> str:
    value = os.environ.get("BACKUP_S3_BUCKET", "").strip()
    if not value:
        raise ValueError("BACKUP_S3_BUCKET must be configured")
    return value


def validate_configuration(*, mode: str) -> None:
    bucket()
    encryption_key()
    storage_client()
    alert_url = os.environ.get("BACKUP_ALERT_WEBHOOK_URL", "")
    if not alert_url.lower().startswith("https://"):
        raise ValueError("BACKUP_ALERT_WEBHOOK_URL must be an HTTPS URL")
    if mode == "worker":
        database_env()
    retention_days = int(os.environ.get("BACKUP_RETENTION_DAYS", "7"))
    if retention_days <= 0:
        raise ValueError("BACKUP_RETENTION_DAYS must be positive")


def _prefix() -> str:
    return os.environ.get("BACKUP_S3_PREFIX", BACKUP_PREFIX).strip("/") + "/"


def delete_object_and_versions(client, object_key: str) -> None:
    versioning = client.get_bucket_versioning(Bucket=bucket()).get("Status")
    if versioning not in {"Enabled", "Suspended"}:
        client.delete_object(Bucket=bucket(), Key=object_key)
        return
    paginator = client.get_paginator("list_object_versions")
    versions = []
    for page in paginator.paginate(Bucket=bucket(), Prefix=object_key):
        versions.extend(
            {"Key": item["Key"], "VersionId": item["VersionId"]}
            for group in ("Versions", "DeleteMarkers")
            for item in page.get(group, [])
            if item["Key"] == object_key
        )
    for offset in range(0, len(versions), 1000):
        client.delete_objects(
            Bucket=bucket(),
            Delete={"Objects": versions[offset : offset + 1000], "Quiet": True},
        )


def backup(now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    key = encryption_key()
    db_env = database_env()
    client = storage_client()
    object_key = f"{_prefix()}{now:%Y/%m/%d}/{uuid.uuid4().hex}.dump.enc"
    with tempfile.TemporaryDirectory(prefix="bbms-backup-") as directory:
        raw = Path(directory) / "database.dump"
        encrypted = Path(directory) / "database.dump.enc"
        verified = Path(directory) / "verified.dump"
        run_command(
            ["pg_dump", "--format=custom", "--no-owner", "--no-acl", "--file", str(raw)],
            env=db_env,
        )
        digest = encrypt_file(raw, encrypted, key)
        client.upload_file(
            str(encrypted),
            bucket(),
            object_key,
            ExtraArgs={"Metadata": {"sha256": digest, "format": "BBMSBK01"}},
        )
        client.download_file(bucket(), object_key, str(encrypted) + ".download")
        downloaded = Path(str(encrypted) + ".download")
        if file_sha256(downloaded) != digest:
            raise RuntimeError("uploaded backup integrity verification failed")
        decrypt_file(downloaded, verified, key)
        run_command(["pg_restore", "--list", str(verified)])
        client.put_object(
            Bucket=bucket(),
            Key=object_key + ".json",
            ContentType="application/json",
            Body=json.dumps({"created_at": now.isoformat(), "sha256": digest}).encode(),
        )
    apply_retention(now=now, client=client)
    return object_key


def apply_retention(*, now: datetime | None = None, client=None) -> int:
    now = now or datetime.now(UTC)
    client = client or storage_client()
    retention_days = int(os.environ.get("BACKUP_RETENTION_DAYS", "7"))
    if retention_days <= 0:
        raise ValueError("BACKUP_RETENTION_DAYS must be positive")
    cutoff = now - timedelta(days=retention_days)
    removed = 0
    paginator = client.get_paginator("list_objects_v2")
    items = [
        item
        for page in paginator.paginate(Bucket=bucket(), Prefix=_prefix())
        for item in page.get("Contents", [])
    ]
    keys = {item["Key"] for item in items}
    for item in items:
        object_key = item["Key"]
        modified = item["LastModified"]
        if modified.tzinfo is None:
            modified = modified.replace(tzinfo=UTC)
        if modified >= cutoff:
            continue
        if object_key.endswith(".dump.enc"):
            delete_object_and_versions(client, object_key)
            delete_object_and_versions(client, object_key + ".json")
            removed += 1
        elif object_key.endswith(".dump.enc.json") and object_key[: -len(".json")] not in keys:
            delete_object_and_versions(client, object_key)
    return removed


def send_alert(message: str, *, opener=None) -> None:
    destination = os.environ.get("BACKUP_ALERT_WEBHOOK_URL", "")
    if not destination.lower().startswith("https://"):
        raise ValueError("BACKUP_ALERT_WEBHOOK_URL must be an HTTPS URL")
    body = json.dumps({"alert": "BackupFreshness", "status": "firing", "message": message}).encode()
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("BACKUP_ALERT_WEBHOOK_BEARER_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(destination, data=body, headers=headers, method="POST")
    try:
        opener = opener or build_opener(_NoRedirect())
        with opener.open(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError("backup alert delivery failed")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError("backup alert delivery failed") from exc


def latest_backup(*, client=None):
    client = client or storage_client()
    objects = []
    keys = set()
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket(), Prefix=_prefix()):
        page_items = page.get("Contents", [])
        keys.update(item["Key"] for item in page_items)
        objects.extend(item for item in page_items if item["Key"].endswith(".dump.enc.json"))
    # The sidecar is written only after successful verification; require its archive to remain present.
    objects = [
        dict(item, Key=item["Key"][: -len(".json")])
        for item in objects
        if item["Key"][: -len(".json")] in keys
    ]
    return max(objects, key=lambda item: item["LastModified"], default=None)


def check_freshness(*, now: datetime | None = None, client=None, send=send_alert) -> bool:
    now = now or datetime.now(UTC)
    latest = latest_backup(client=client)
    stale = latest is None
    if latest:
        modified = latest["LastModified"]
        if modified.tzinfo is None:
            modified = modified.replace(tzinfo=UTC)
        stale = now - modified > timedelta(hours=25)
    if stale:
        send("No verified database backup has completed within the last 25 hours.")
        return False
    return True


def restore(object_key: str) -> None:
    if os.environ.get("BACKUP_RESTORE_SPARE_CONFIRMED") != "true":
        raise ValueError("set BACKUP_RESTORE_SPARE_CONFIRMED=true only for a spare restore target")
    target_host = os.environ.get("BACKUP_RESTORE_TARGET_HOST", "")
    target_db = os.environ.get("BACKUP_RESTORE_TARGET_DB", "")
    if not target_host or not target_db:
        raise ValueError("spare restore host and database must be configured")
    if target_host.rstrip(".").lower() == os.environ.get("POSTGRES_HOST", "").rstrip(".").lower():
        raise ValueError("restore target must differ from the source database host")
    if not object_key.startswith(_prefix()) or not object_key.endswith(".dump.enc"):
        raise ValueError("restore object must be an encrypted BBMS backup in the configured prefix")
    target_env = pg_tool_environment()
    target_env.update({
        "PGHOST": target_host,
        "PGPORT": os.environ.get("BACKUP_RESTORE_TARGET_PORT", "5432"),
        "PGDATABASE": target_db,
        "PGUSER": os.environ.get("BACKUP_RESTORE_TARGET_USER", ""),
        "PGPASSWORD": os.environ.get("BACKUP_RESTORE_TARGET_PASSWORD", ""),
    })
    if not target_env["PGUSER"] or not target_env["PGPASSWORD"]:
        raise ValueError("spare restore credentials must be configured")
    client = storage_client()
    with tempfile.TemporaryDirectory(prefix="bbms-restore-") as directory:
        encrypted = Path(directory) / "database.dump.enc"
        raw = Path(directory) / "database.dump"
        client.download_file(bucket(), object_key, str(encrypted))
        expected = client.head_object(Bucket=bucket(), Key=object_key).get("Metadata", {}).get("sha256")
        if not expected or file_sha256(encrypted) != expected:
            raise ValueError("backup integrity verification failed")
        decrypt_file(encrypted, raw, encryption_key())
        run_command(["pg_restore", "--list", str(raw)])
        preflight = subprocess.run(
            [
                "psql",
                "--tuples-only",
                "--no-align",
                "--command",
                "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname !~ '^pg_' AND n.nspname <> 'information_schema' "
                "AND c.relkind IN ('r', 'v', 'm', 'S', 'f', 'p')",
                "--dbname",
                target_db,
            ],
            env=target_env,
            capture_output=True,
            text=True,
            check=False,
        )
        if preflight.returncode:
            raise RuntimeError("could not verify that the spare restore database is empty")
        if preflight.stdout.strip() != "0":
            raise ValueError("spare restore database must be empty")
        run_command(
            [
                "pg_restore",
                "--exit-on-error",
                "--single-transaction",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                "--dbname",
                target_db,
                str(raw),
            ],
            env=target_env,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("backup")
    commands.add_parser("check-freshness")
    restore_parser = commands.add_parser("restore")
    restore_parser.add_argument("object_key")
    args = parser.parse_args(argv)
    try:
        if args.command == "backup":
            print(f"verified backup created: {backup()}")
        elif args.command == "check-freshness":
            if not check_freshness():
                return 1
            print("latest verified backup is within the 25-hour recovery point objective")
        else:
            restore(args.object_key)
            print("backup restored and archive integrity verified")
    except Exception:
        print("backup operation failed due to a configuration, storage, database, or integrity error", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
