FROM postgres:16-alpine

RUN apk add --no-cache python3 py3-pip tzdata \
    && python3 -m venv /opt/backup-venv \
    && /opt/backup-venv/bin/pip install --no-cache-dir boto3==1.43.98 cryptography==50.0.2

ENV PATH="/opt/backup-venv/bin:$PATH" TZ=UTC PYTHONUNBUFFERED=1
WORKDIR /app
COPY scripts/db_backup.py /app/scripts/db_backup.py
COPY scripts/backup_scheduler.py /app/scripts/backup_scheduler.py
COPY scripts/init_backup_drill_storage.py /app/scripts/init_backup_drill_storage.py
RUN adduser -D -H -u 10002 bbms-backup \
    && chown -R bbms-backup:bbms-backup /app
USER bbms-backup
CMD ["python3", "scripts/backup_scheduler.py"]
