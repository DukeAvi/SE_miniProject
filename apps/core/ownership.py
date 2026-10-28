"""Object-ownership helpers that keep foreign records indistinguishable from missing ones."""

from django.http import Http404
from django.shortcuts import get_object_or_404

from apps.audit.services import record_event


def get_owned_object_or_404(queryset, *, request, lookup: dict, owner_field: str = "user"):
    """Return an owned object or raise the same 404 used for a missing object."""
    user = request.user
    if not user.is_authenticated:
        raise Http404

    try:
        return get_object_or_404(
            queryset.filter(**{owner_field: user}),
            **lookup,
        )
    except Http404:
        record_event(
            action="ACCESS_DENIED",
            actor=user,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        raise
