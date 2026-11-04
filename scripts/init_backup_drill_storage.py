"""Initialize the isolated MinIO bucket used by the CI recovery drill."""

import os
import time

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


client = boto3.client(
    "s3",
    endpoint_url=os.environ["BACKUP_S3_ENDPOINT_URL"],
    region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
    config=Config(connect_timeout=2, read_timeout=2, retries={"max_attempts": 0}, s3={"addressing_style": "path"}),
)
for _attempt in range(60):
    try:
        client.create_bucket(Bucket=os.environ["BACKUP_S3_BUCKET"])
        break
    except (BotoCoreError, ClientError):
        time.sleep(2)
else:
    raise SystemExit("temporary S3-compatible storage did not become ready")
