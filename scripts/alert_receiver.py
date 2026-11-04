"""Store sanitized Alertmanager evidence for the classroom deployment."""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


EVIDENCE = Path("/var/lib/bbms-alerts/alerts.jsonl")


class AlertHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/alerts":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
            with EVIDENCE.open("a", encoding="utf-8") as stream:
                for alert in payload.get("alerts", []):
                    stream.write(json.dumps({
                        "status": alert.get("status"),
                        "alertname": alert.get("labels", {}).get("alertname"),
                        "starts_at": alert.get("startsAt"),
                        "ends_at": alert.get("endsAt"),
                    }, sort_keys=True) + "\n")
        except (ValueError, TypeError, json.JSONDecodeError):
            self.send_error(400)
            return
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", 9095), AlertHandler).serve_forever()
