"""Maintenance-aware availability calculations from one-minute probes."""

from datetime import UTC, datetime


def calculate_availability(samples, maintenance_windows, *, target_percent=99.5):
    included = []
    excluded = 0
    for timestamp, value in samples:
        planned = any(start <= timestamp < end for start, end in maintenance_windows)
        if planned:
            excluded += 1
        else:
            included.append(float(value))
    up = sum(1 for value in included if value >= 1.0)
    total = len(included)
    raw_percent = up / total * 100.0 if total else None
    percent = round(raw_percent, 4) if raw_percent is not None else None
    return {
        "probe_samples": len(samples),
        "planned_maintenance_samples": excluded,
        "included_samples": total,
        "successful_samples": up,
        "failed_samples": total - up,
        "availability_percent": percent,
        "target_percent": float(target_percent),
        "target_met": raw_percent is not None and raw_percent >= target_percent,
        "data_available": total > 0,
    }


def parse_prometheus_samples(values):
    return [(datetime.fromtimestamp(float(ts), tz=UTC), float(value)) for ts, value in values]
