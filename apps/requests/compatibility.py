"""Component-specific ABO/Rh screening rules for the classroom demo.

This initial screen is not a substitute for antibody testing, crossmatching, or
transfusion-service authorization.
"""

from collections.abc import Callable, Iterable
from typing import TypeVar

from rest_framework.exceptions import APIException


BLOOD_GROUPS = ("O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+")
COMPONENTS = frozenset({"WHOLE_BLOOD", "RBC", "PLASMA", "PLATELETS"})
ABO_GROUPS = ("O", "A", "B", "AB")
RH_VALUES = ("-", "+")

_RBC_ABO_DONORS = {
    "O": frozenset({"O"}),
    "A": frozenset({"O", "A"}),
    "B": frozenset({"O", "B"}),
    "AB": frozenset(ABO_GROUPS),
}
_PLASMA_ABO_DONORS = {
    "O": frozenset(ABO_GROUPS),
    "A": frozenset({"A", "AB"}),
    "B": frozenset({"B", "AB"}),
    "AB": frozenset({"AB"}),
}


def _abo_and_rh(group: str) -> tuple[str, str] | None:
    if group not in BLOOD_GROUPS:
        return None
    return group[:-1], group[-1]


def acceptable_donor_groups(recipient_group: str, component: str) -> frozenset[str]:
    """Return the exact donor groups accepted for a recipient, failing closed."""
    recipient = _abo_and_rh(recipient_group)
    if recipient is None or component not in COMPONENTS:
        return frozenset()

    recipient_abo, recipient_rh = recipient
    if component in {"WHOLE_BLOOD", "PLATELETS"}:
        return frozenset({recipient_group})

    if component == "RBC":
        compatible_abo = _RBC_ABO_DONORS[recipient_abo]
        return frozenset(
            donor_abo + donor_rh
            for donor_abo in compatible_abo
            for donor_rh in RH_VALUES
            if recipient_rh == "+" or donor_rh == "-"
        )

    compatible_abo = _PLASMA_ABO_DONORS[recipient_abo]
    return frozenset(
        donor_abo + donor_rh
        for donor_abo in compatible_abo
        for donor_rh in RH_VALUES
    )


def is_compatible(donor_group: str, recipient_group: str, component: str) -> bool:
    """Check one donor-recipient pairing for the specified component."""
    return donor_group in acceptable_donor_groups(recipient_group, component)


class IncompatibleBloodTypeError(APIException):
    status_code = 422
    default_detail = "The blood groups are incompatible for this component."
    default_code = "incompatible_blood_type"
    api_error_code = "incompatible_blood_type"


UnitT = TypeVar("UnitT")


def select_compatible_units(
    units: Iterable[UnitT],
    *,
    recipient_group: str,
    component: str,
    donor_group_for: Callable[[UnitT], str],
) -> list[UnitT]:
    """Filter candidate units before presenting them for fulfillment."""
    return [
        unit
        for unit in units
        if is_compatible(donor_group_for(unit), recipient_group, component)
    ]


def assert_compatible(
    donor_group: str, recipient_group: str, component: str
) -> None:
    """Recheck a selected unit immediately before a locked fulfillment write."""
    if not is_compatible(donor_group, recipient_group, component):
        raise IncompatibleBloodTypeError()
