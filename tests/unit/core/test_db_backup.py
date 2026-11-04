import base64
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import ipaddress
import json
from pathlib import Path
import ssl
import threading

import pytest
from cryptography import x509
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from urllib.request import HTTPSHandler, build_opener

from scripts import db_backup


class Paginator:
    def __init__(self, pages):
        self.pages = pages

    def paginate(self, **_kwargs):
        return self.pages


class BackupStore:
    def __init__(self, items):
        self.items = items

    def get_paginator(self, _name):
        return Paginator([{"Contents": self.items}])


class MemoryS3:
    def __init__(self, *, corrupt_download=False):
        self.objects = {}
        self.corrupt_download = corrupt_download
        self.markers = []

    def upload_file(self, filename, bucket, key, ExtraArgs):
        self.objects[key] = (Path(filename).read_bytes(), ExtraArgs["Metadata"])

    def download_file(self, bucket, key, filename):
        payload = self.objects[key][0]
        if self.corrupt_download:
            payload = payload[:-1] + bytes([payload[-1] ^ 0x01])
        Path(filename).write_bytes(payload)

    def put_object(self, **kwargs):
        self.markers.append(kwargs["Key"])
        self.objects[kwargs["Key"]] = (kwargs["Body"], {})

    def get_paginator(self, _name):
        return Paginator([{"Contents": []}])

    def get_bucket_versioning(self, **_kwargs):
        return {}

    def delete_object(self, **_kwargs):
        return None


def test_encryption_round_trip_and_authentication_rejects_tampering(tmp_path):
    source = tmp_path / "source.dump"
    encrypted = tmp_path / "source.dump.enc"
    restored = tmp_path / "restored.dump"
    source.write_bytes((b"representative backup data" * 90_000) + b"end")
    key = bytes(range(32))

    digest = db_backup.encrypt_file(source, encrypted, key)
    assert len(digest) == 64
    assert encrypted.read_bytes() != source.read_bytes()
    db_backup.decrypt_file(encrypted, restored, key)
    assert restored.read_bytes() == source.read_bytes()

    tampered = bytearray(encrypted.read_bytes())
    tampered[25] ^= 0x01
    encrypted.write_bytes(tampered)
    with pytest.raises(InvalidTag):
        db_backup.decrypt_file(encrypted, restored, key)


def test_encryption_key_requires_exact_256_bit_urlsafe_base64():
    key = base64.urlsafe_b64encode(bytes(range(32))).decode("ascii")
    assert db_backup.encryption_key(key) == bytes(range(32))
    with pytest.raises(ValueError, match="exactly 32 bytes"):
        db_backup.encryption_key(base64.urlsafe_b64encode(b"short").decode())


def test_database_tool_environment_contains_only_database_credentials(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "database")
    monkeypatch.setenv("POSTGRES_DB", "bbms")
    monkeypatch.setenv("POSTGRES_USER", "bbms")
    monkeypatch.setenv("POSTGRES_PASSWORD", "database-password")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "storage-secret")
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", "encryption-secret")
    env = db_backup.database_env()
    assert env["PGHOST"] == "database"
    assert env["PGPASSWORD"] == "database-password"
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert "BACKUP_ENCRYPTION_KEY" not in env


def test_backup_upload_is_downloaded_decrypted_and_catalog_checked_before_success_marker(monkeypatch):
    key = base64.urlsafe_b64encode(bytes(range(32))).decode()
    store = MemoryS3()
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", key)
    monkeypatch.setenv("BACKUP_S3_BUCKET", "backups")
    monkeypatch.setenv("BACKUP_S3_PREFIX", "bbms-backups")
    monkeypatch.setenv("BACKUP_RETENTION_DAYS", "7")
    monkeypatch.setenv("POSTGRES_HOST", "database")
    monkeypatch.setenv("POSTGRES_DB", "bbms")
    monkeypatch.setenv("POSTGRES_USER", "bbms")
    monkeypatch.setenv("POSTGRES_PASSWORD", "unit-test-password")
    monkeypatch.setattr(db_backup, "storage_client", lambda: store)
    restored_archives = []

    def fake_command(args, *, env=None):
        if args[0] == "pg_dump":
            Path(args[args.index("--file") + 1]).write_bytes(b"synthetic postgres archive")
        else:
            restored_archives.append(Path(args[-1]).read_bytes())

    monkeypatch.setattr(db_backup, "run_command", fake_command)
    now = datetime(2026, 11, 4, 2, tzinfo=UTC)
    object_key = db_backup.backup(now=now)

    encrypted, metadata = store.objects[object_key]
    assert encrypted != b"synthetic postgres archive"
    assert metadata["sha256"] == db_backup.sha256(encrypted).hexdigest()
    assert store.markers == [object_key + ".json"]
    assert restored_archives == [b"synthetic postgres archive"]
    manifest = json.loads(store.objects[object_key + ".json"][0])
    assert manifest["sha256"] == metadata["sha256"]


def test_backup_does_not_write_success_marker_when_remote_copy_is_corrupted(monkeypatch):
    key = base64.urlsafe_b64encode(bytes(range(32))).decode()
    store = MemoryS3(corrupt_download=True)
    monkeypatch.setenv("BACKUP_ENCRYPTION_KEY", key)
    monkeypatch.setenv("BACKUP_S3_BUCKET", "backups")
    monkeypatch.setenv("BACKUP_S3_PREFIX", "bbms-backups")
    monkeypatch.setenv("POSTGRES_HOST", "database")
    monkeypatch.setenv("POSTGRES_DB", "bbms")
    monkeypatch.setenv("POSTGRES_USER", "bbms")
    monkeypatch.setenv("POSTGRES_PASSWORD", "unit-test-password")
    monkeypatch.setattr(db_backup, "storage_client", lambda: store)
    monkeypatch.setattr(
        db_backup,
        "run_command",
        lambda args, **kwargs: Path(args[args.index("--file") + 1]).write_bytes(b"synthetic archive")
        if args[0] == "pg_dump"
        else None,
    )
    with pytest.raises(RuntimeError, match="integrity verification failed"):
        db_backup.backup(now=datetime(2026, 11, 4, 2, tzinfo=UTC))
    assert store.markers == []


def test_storage_endpoint_requires_https_outside_explicit_test_configuration(monkeypatch):
    monkeypatch.setenv("BACKUP_S3_ENDPOINT_URL", "http://storage.internal")
    monkeypatch.delenv("BACKUP_ALLOW_HTTP_STORAGE", raising=False)
    with pytest.raises(ValueError, match="HTTPS"):
        db_backup.storage_client()

    monkeypatch.setenv("BACKUP_ALLOW_HTTP_STORAGE", "true")
    monkeypatch.setattr(db_backup.boto3, "client", lambda *_args, **_kwargs: "test-client")
    assert db_backup.storage_client() == "test-client"


def test_freshness_alert_fires_at_25_hour_boundary_and_uses_only_verified_marker(monkeypatch):
    monkeypatch.setenv("BACKUP_S3_BUCKET", "backups")
    now = datetime(2026, 11, 4, 12, tzinfo=UTC)
    fresh = BackupStore([
        {"Key": "bbms-backups/today.dump.enc", "LastModified": now - timedelta(hours=24, minutes=59)},
        {"Key": "bbms-backups/today.dump.enc.json", "LastModified": now - timedelta(hours=24, minutes=59)},
    ])
    stale = BackupStore([
        {"Key": "bbms-backups/old.dump.enc", "LastModified": now - timedelta(hours=25, seconds=1)},
        {"Key": "bbms-backups/old.dump.enc.json", "LastModified": now - timedelta(hours=25, seconds=1)},
    ])
    unverified_only = BackupStore([
        {"Key": "bbms-backups/partial.dump.enc", "LastModified": now},
        {"Key": "bbms-backups/orphan.dump.enc.json", "LastModified": now},
    ])
    alerts = []
    assert db_backup.check_freshness(now=now, client=fresh, send=alerts.append)
    assert not db_backup.check_freshness(now=now, client=stale, send=alerts.append)
    assert not db_backup.check_freshness(now=now, client=unverified_only, send=alerts.append)
    assert alerts == [
        "No verified database backup has completed within the last 25 hours.",
        "No verified database backup has completed within the last 25 hours.",
    ]


def test_retention_removes_archive_and_its_success_marker(monkeypatch):
    cutoff = datetime(2026, 11, 1, tzinfo=UTC)
    old_key = "bbms-backups/old.dump.enc"

    class Store(BackupStore):
        def __init__(self):
            super().__init__([{"Key": old_key, "LastModified": cutoff - timedelta(seconds=1)}])
            self.deleted = []

        def delete_object(self, **kwargs):
            self.deleted.append(kwargs["Key"])

        def get_bucket_versioning(self, **_kwargs):
            return {}

    store = Store()
    monkeypatch.setenv("BACKUP_RETENTION_DAYS", "7")
    monkeypatch.setenv("BACKUP_S3_BUCKET", "backups")
    assert db_backup.apply_retention(now=cutoff + timedelta(days=7), client=store) == 1
    assert store.deleted == [old_key, old_key + ".json"]


def test_retention_deletes_all_object_versions_and_markers(monkeypatch):
    key = "bbms-backups/old.dump.enc"

    class VersionedStore:
        def __init__(self):
            self.deletions = []

        def get_bucket_versioning(self, **_kwargs):
            return {"Status": "Enabled"}

        def get_paginator(self, name):
            if name == "list_objects_v2":
                return Paginator([{"Contents": [
                    {"Key": key, "LastModified": datetime(2026, 10, 1, tzinfo=UTC)},
                    {"Key": key + ".json", "LastModified": datetime(2026, 10, 1, tzinfo=UTC)},
                ]}])

            class VersionPaginator:
                def paginate(self, **kwargs):
                    object_key = kwargs["Prefix"]
                    return [{
                        "Versions": [
                            {"Key": object_key, "VersionId": "current"},
                            {"Key": object_key, "VersionId": "older"},
                        ],
                        "DeleteMarkers": [{"Key": object_key, "VersionId": "delete-marker"}],
                    }]

            return VersionPaginator()

        def delete_objects(self, **kwargs):
            self.deletions.extend(kwargs["Delete"]["Objects"])

    store = VersionedStore()
    monkeypatch.setenv("BACKUP_RETENTION_DAYS", "7")
    monkeypatch.setenv("BACKUP_S3_BUCKET", "backups")
    db_backup.apply_retention(now=datetime(2026, 11, 1, tzinfo=UTC), client=store)
    assert store.deletions == [
        {"Key": object_key, "VersionId": version}
        for object_key in (key, key + ".json")
        for version in ("current", "older", "delete-marker")
    ]


def test_restore_refuses_source_database_without_explicit_spare_confirmation(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "production-db")
    monkeypatch.setenv("BACKUP_RESTORE_TARGET_HOST", "production-db")
    monkeypatch.setenv("BACKUP_RESTORE_TARGET_DB", "bbms")
    monkeypatch.setenv("BACKUP_RESTORE_SPARE_CONFIRMED", "true")
    with pytest.raises(ValueError, match="differ from the source"):
        db_backup.restore("bbms-backups/restore.dump.enc")


def test_alert_delivery_sends_sanitized_payload_to_https_destination(monkeypatch):
    captured = {}

    class Response:
        status = 202

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class FakeOpener:
        def open(self, request, timeout):
            return fake_open(request, timeout)

    def fake_open(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data
        captured["auth"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return Response()

    monkeypatch.setenv("BACKUP_ALERT_WEBHOOK_URL", "https://alerts.example.test/backup")
    monkeypatch.setenv("BACKUP_ALERT_WEBHOOK_BEARER_TOKEN", "test-token")
    db_backup.send_alert(
        "No verified database backup has completed within the last 25 hours.",
        opener=FakeOpener(),
    )
    payload = json.loads(captured["body"])
    assert captured["url"] == "https://alerts.example.test/backup"
    assert captured["auth"] == "Bearer test-token"
    assert captured["timeout"] == 10
    assert payload == {
        "alert": "BackupFreshness",
        "status": "firing",
        "message": "No verified database backup has completed within the last 25 hours.",
    }
    assert "test-token" not in captured["body"].decode()


def test_alert_is_delivered_over_verified_https_to_configured_receiver(tmp_path, monkeypatch):
    received = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received.append((self.path, self.headers.get("Authorization"), self.rfile.read(int(self.headers["Content-Length"]))))
            self.send_response(204)
            self.end_headers()

        def log_message(self, _format, *_args):
            return

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .sign(private_key, hashes.SHA256())
    )
    certificate_path = tmp_path / "test-receiver.pem"
    key_path = tmp_path / "test-receiver-key.pem"
    certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    server_context.load_cert_chain(certificate_path, key_path)
    server.socket = server_context.wrap_socket(server.socket, server_side=True)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        client_context = ssl.create_default_context(cafile=str(certificate_path))
        opener = build_opener(db_backup._NoRedirect(), HTTPSHandler(context=client_context))
        monkeypatch.setenv("BACKUP_ALERT_WEBHOOK_URL", f"https://127.0.0.1:{server.server_port}/backup-alerts")
        monkeypatch.setenv("BACKUP_ALERT_WEBHOOK_BEARER_TOKEN", "receiver-test-token")
        db_backup.send_alert("No verified database backup has completed within the last 25 hours.", opener=opener)
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)

    assert len(received) == 1
    path, auth, body = received[0]
    assert path == "/backup-alerts"
    assert auth == "Bearer receiver-test-token"
    payload = json.loads(body)
    assert payload["alert"] == "BackupFreshness"
    assert "receiver-test-token" not in body.decode()
