"""Forward sanitized Alertmanager notifications and retain delivery evidence."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


EVIDENCE = Path(os.environ.get("BBMS_ALERT_EVIDENCE_PATH", "/app/var/alerts/alerts.jsonl"))
MAX_PAYLOAD_BYTES = 1_048_576


class RejectRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def validate_https_url(destination, setting_name="BBMS_ALERT_WEBHOOK_URL"):
    parsed = urlsplit(destination or "")
    has_control_chars = any(ord(character) < 32 or ord(character) == 127 for character in destination or "")
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or has_control_chars
        or (destination or "").strip() != (destination or "")
    ):
        raise ValueError(f"{setting_name} must be an HTTPS URL without embedded credentials.")
    return destination


def sanitize_payload(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("alerts"), list):
        raise ValueError("Invalid Alertmanager payload.")

    alerts = []
    for alert in payload["alerts"]:
        if not isinstance(alert, dict):
            raise ValueError("Invalid Alertmanager alert.")
        labels = alert.get("labels") or {}
        annotations = alert.get("annotations") or {}
        if not isinstance(labels, dict) or not isinstance(annotations, dict):
            raise ValueError("Invalid Alertmanager alert metadata.")
        alerts.append({
            "status": str(alert.get("status", "unknown"))[:32],
            "alertname": str(labels.get("alertname", "unknown"))[:128],
            "severity": str(labels.get("severity", "unknown"))[:32],
            "summary": str(annotations.get("summary", ""))[:512],
            "startsAt": str(alert.get("startsAt", ""))[:64],
            "endsAt": str(alert.get("endsAt", ""))[:64],
        })
    return {"alerts": alerts}


def forward_alerts(payload, destination, bearer_token="", *, opener=None):
    validate_https_url(destination)
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"Content-Type": "application/json", "User-Agent": "BBMS-Alert-Forwarder/1.0"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    request = Request(destination, data=body, headers=headers, method="POST")
    client = opener or build_opener(RejectRedirectHandler()).open
    with client(request, timeout=10) as response:
        if not 200 <= response.status < 300:
            raise URLError("Alert destination rejected the notification.")


def store_evidence(payload, path=EVIDENCE):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        for alert in payload["alerts"]:
            stream.write(json.dumps(alert, sort_keys=True) + "\n")


def make_handler(destination, bearer_token, evidence_path=EVIDENCE):
    class AlertHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/healthz":
                self.send_error(404)
                return
            self.send_response(200)
            self.end_headers()

        def do_POST(self):
            if self.path != "/alerts":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_PAYLOAD_BYTES:
                    self.send_error(413)
                    return
                payload = sanitize_payload(json.loads(self.rfile.read(length)))
            except (ValueError, TypeError, json.JSONDecodeError):
                self.send_error(400)
                return

            try:
                forward_alerts(payload, destination, bearer_token)
                store_evidence(payload, evidence_path)
            except (OSError, URLError, ValueError):
                # Avoid echoing webhook URLs, credentials, or provider responses.
                print("BBMS alert delivery failed", file=sys.stderr)
                self.send_error(502, "Alert delivery failed.")
                return
            self.send_response(204)
            self.end_headers()

        def log_message(self, format, *args):
            return

    return AlertHandler


def main():
    destination = validate_https_url(os.environ.get("BBMS_ALERT_WEBHOOK_URL"))
    bearer_token = os.environ.get("BBMS_ALERT_WEBHOOK_BEARER_TOKEN", "")
    ThreadingHTTPServer(("0.0.0.0", 9095), make_handler(destination, bearer_token)).serve_forever()


if __name__ == "__main__":
    main()
