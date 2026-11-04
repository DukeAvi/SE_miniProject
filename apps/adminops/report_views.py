"""Date-filtered operational reports for Staff and Admin."""

import csv
from datetime import date, datetime, time, timedelta
import re
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import AccountRole
from apps.core.permissions import RolePermission
from apps.donors.models import Donation
from apps.inventory.models import BloodUnit, InventoryTransaction
from apps.requests.models import BloodAllocation, BloodRequest


def _error(code, message, details=None, status_code=400):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
                "correlation_id": str(uuid4()),
            }
        },
        status=status_code,
    )


class ReportPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class _Echo:
    """CSV writer target that returns each row as a streamed string."""

    def write(self, value):
        return value


REPORTS = {
    "donations": {
        "date_field": "donation_date",
        "filters": {
            "blood_group": "blood_group",
            "component": "component",
            "status": "status",
        },
        "filter_choices": {
            "blood_group": ("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"),
            "component": BloodUnit.Component.values,
            "status": Donation.Status.values,
        },
        "queryset": lambda start, end: Donation.objects.filter(
            donation_date__gte=start, donation_date__lte=end
        ).order_by("donation_date", "pk"),
        "quantity_sum": "quantity_units",
        "headers": ("date", "blood_group", "component", "quantity_units", "status"),
        "admin_groups": ("donation_date", "blood_group", "component", "status"),
        "admin_group_date": "donation_date",
        "admin_quantity": "quantity_units",
        "row": lambda item: (
            item.donation_date.isoformat(), item.blood_group, item.component,
            item.quantity_units, item.status,
        ),
    },
    "inventory": {
        "date_field": "occurred_at",
        "filters": {
            "blood_group": "blood_unit__blood_group",
            "component": "blood_unit__component",
            "action": "action",
        },
        "filter_choices": {
            "blood_group": ("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"),
            "component": BloodUnit.Component.values,
            "action": InventoryTransaction.Action.values,
        },
        "queryset": lambda start, end: InventoryTransaction.objects.filter(
            occurred_at__gte=start, occurred_at__lt=end
        ).select_related("blood_unit").order_by("occurred_at", "pk"),
        "quantity_sum": "blood_unit__quantity_units",
        "headers": (
            "date", "action", "from_status", "to_status", "blood_group",
            "component", "quantity_units",
        ),
        "admin_groups": ("report_date", "action", "from_status", "to_status", "blood_unit__blood_group", "blood_unit__component"),
        "admin_group_date": "report_date",
        "admin_quantity": "blood_unit__quantity_units",
        "row": lambda item: (
            timezone.localtime(item.occurred_at, ZoneInfo(settings.BLOOD_BANK_TIME_ZONE)).isoformat(),
            item.action, item.from_status, item.to_status, item.blood_unit.blood_group,
            item.blood_unit.component, item.blood_unit.quantity_units,
        ),
    },
    "requests": {
        "date_field": "created_at",
        "filters": {
            "blood_group": "patient_blood_group",
            "component": "component",
            "status": "status",
            "urgency": "urgency",
        },
        "filter_choices": {
            "blood_group": BloodRequest.BLOOD_GROUPS,
            "component": BloodRequest.COMPONENTS,
            "status": BloodRequest.Status.values,
            "urgency": BloodRequest.Urgency.values,
        },
        "queryset": lambda start, end: BloodRequest.objects.filter(
            created_at__gte=start, created_at__lt=end
        ).order_by("created_at", "pk"),
        "quantity_sum": "units_needed",
        "headers": (
            "date", "request_id", "blood_group", "component", "units_needed",
            "urgency", "status",
        ),
        "admin_groups": ("report_date", "patient_blood_group", "component", "urgency", "status"),
        "admin_group_date": "report_date",
        "admin_quantity": "units_needed",
        # Patient name, contact details, and hospital are deliberately excluded.
        "row": lambda item: (
            timezone.localtime(item.created_at, ZoneInfo(settings.BLOOD_BANK_TIME_ZONE)).isoformat(),
            item.request_id, item.patient_blood_group, item.component, item.units_needed,
            item.urgency, item.status,
        ),
    },
    "issued-units": {
        "date_field": "issued_at",
        "filters": {
            "blood_group": "blood_unit__blood_group",
            "component": "blood_unit__component",
        },
        "filter_choices": {
            "blood_group": ("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"),
            "component": BloodUnit.Component.values,
        },
        "queryset": lambda start, end: BloodAllocation.objects.filter(
            status=BloodAllocation.Status.ISSUED,
            issued_at__gte=start,
            issued_at__lt=end,
        ).select_related("blood_unit", "blood_request").order_by("issued_at", "pk"),
        "quantity_sum": "blood_unit__quantity_units",
        "headers": (
            "date", "request_id", "blood_group", "component", "quantity_units",
        ),
        "admin_groups": ("report_date", "blood_unit__blood_group", "blood_unit__component"),
        "admin_group_date": "report_date",
        "admin_quantity": "blood_unit__quantity_units",
        "row": lambda item: (
            timezone.localtime(item.issued_at, ZoneInfo(settings.BLOOD_BANK_TIME_ZONE)).isoformat(),
            item.blood_request.request_id, item.blood_unit.blood_group,
            item.blood_unit.component, item.blood_unit.quantity_units,
        ),
    },
}


def _parse_date(value, field, errors):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        errors[field] = ["Use YYYY-MM-DD."]
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors[field] = ["Enter a valid date."]
        return None


def _report_queryset(resource, start_date, end_date, params):
    definition = REPORTS[resource]
    zone = ZoneInfo(settings.BLOOD_BANK_TIME_ZONE)
    if definition["date_field"] == "donation_date":
        start, end = start_date, end_date
    else:
        start = datetime.combine(start_date, time.min, tzinfo=zone)
        end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=zone)
    rows = definition["queryset"](start, end)
    for key, field in definition["filters"].items():
        if key in params:
            rows = rows.filter(**{field: params[key]})
    return rows


def _csv_response(resource, start_date, end_date, rows, headers, render_row):
    writer = csv.writer(_Echo())

    def stream():
        yield writer.writerow(headers)
        for item in rows.iterator(chunk_size=500):
            yield writer.writerow(render_row(item).values())

    response = StreamingHttpResponse(stream(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = (
        f'attachment; filename="{resource}-{start_date.isoformat()}-{end_date.isoformat()}.csv"'
    )
    return response


def _admin_grouped_report(resource, rows):
    """Return the approved Admin summary view without exposing record-level data."""
    definition = REPORTS[resource]
    group_date = definition["admin_group_date"]
    date_field = definition["date_field"]
    if date_field != "donation_date":
        rows = rows.annotate(
            report_date=TruncDate(
                date_field,
                tzinfo=ZoneInfo(settings.BLOOD_BANK_TIME_ZONE),
            )
        )
    group_fields = definition["admin_groups"]
    grouped = (
        rows.values(*group_fields)
        .annotate(records=Count("pk"), quantity_units=Sum(definition["admin_quantity"]))
        .order_by(*group_fields)
    )
    headers = tuple(
        "date" if field == group_date else field.removeprefix("blood_unit__").removeprefix("patient_")
        for field in group_fields
    ) + ("records", "quantity_units")

    def render(row):
        values = {
            header: row[field].isoformat() if isinstance(row[field], date) else row[field]
            for header, field in zip(headers, group_fields)
        }
        values["records"] = row["records"]
        values["quantity_units"] = row["quantity_units"] or 0
        return values

    return grouped, headers, render


class OperationalReportView(APIView):
    permission_classes = (IsAuthenticated, RolePermission)
    permission_code = "reports"

    def get_authenticate_header(self, request):
        return "Session"

    def get(self, request, resource):
        definition = REPORTS.get(resource)
        if definition is None:
            return _error("report_not_found", "Report type was not found.", status_code=404)

        allowed = {"from", "to", "page", "page_size", "export", *definition["filters"]}
        errors = {}
        unexpected = set(request.query_params) - allowed
        if unexpected:
            errors["query"] = [f"Unsupported parameter: {key}." for key in sorted(unexpected)]

        start_date = _parse_date(request.query_params.get("from"), "from", errors)
        end_date = _parse_date(request.query_params.get("to"), "to", errors)
        if start_date and end_date and start_date > end_date:
            errors["to"] = ["Must be on or after from."]

        for field in set(request.query_params) & set(definition["filters"]):
            if request.query_params[field] not in definition["filter_choices"][field]:
                errors[field] = ["Invalid choice."]

        output_format = request.query_params.get("export", "json")
        if output_format not in {"json", "csv"}:
            errors["export"] = ["Use json or csv."]

        for field in ("page", "page_size"):
            value = request.query_params.get(field)
            if value is not None and (not value.isascii() or not value.isdecimal() or int(value) < 1):
                errors[field] = ["Must be a positive integer."]

        if errors:
            return _error("validation_error", "The request could not be processed.", errors)

        rows = _report_queryset(resource, start_date, end_date, request.query_params)
        record_count = rows.count()
        total_quantity = rows.aggregate(total=Sum(definition["quantity_sum"]))["total"] or 0
        if request.user.role == AccountRole.ADMIN:
            rows, csv_headers, render_row = _admin_grouped_report(resource, rows)
        else:
            csv_headers = definition["headers"]

            def render_row(item):
                return dict(zip(csv_headers, definition["row"](item)))
        result_count = rows.count()

        if output_format == "csv":
            return _csv_response(resource, start_date, end_date, rows, csv_headers, render_row)

        paginator = ReportPagination()
        try:
            page = paginator.paginate_queryset(rows, request, view=self)
        except NotFound:
            return _error("invalid_pagination", "Page is outside the available result range.")
        return Response(
            {
                "from": start_date.isoformat(),
                "to": end_date.isoformat(),
                "count": result_count,
                "page": paginator.page.number,
                "page_size": paginator.get_page_size(request),
                "totals": {"records": record_count, "quantity_units": total_quantity},
                "results": [render_row(item) for item in page],
            }
        )
