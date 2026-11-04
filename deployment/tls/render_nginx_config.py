"""Validate the public host and render the fixed Nginx TLS configuration."""

import os
import re
import sys


hostname = os.environ.get("BBMS_PUBLIC_HOSTNAME", "")
label = r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
if hostname != "localhost" and not re.fullmatch(rf"{label}(?:\.{label})*", hostname):
    print("BBMS_PUBLIC_HOSTNAME must be a valid DNS hostname", file=sys.stderr)
    raise SystemExit(2)

with open("/etc/nginx/nginx.conf.template", encoding="utf-8") as template:
    config = template.read()
if "__BBMS_PUBLIC_HOSTNAME__" not in config:
    print("Nginx hostname template marker is missing", file=sys.stderr)
    raise SystemExit(2)

with open("/etc/nginx/nginx.conf", "w", encoding="utf-8") as rendered:
    rendered.write(config.replace("__BBMS_PUBLIC_HOSTNAME__", hostname))

os.execvp("nginx", ["nginx", "-g", "daemon off;"])
