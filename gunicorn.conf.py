"""Gunicorn worker lifecycle hook for Prometheus multiprocess metrics."""


def child_exit(server, worker):
    from prometheus_client import multiprocess

    multiprocess.mark_process_dead(worker.pid)
