"""Celery application and Django task discovery."""

import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bbms.settings")

app = Celery("bbms")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
