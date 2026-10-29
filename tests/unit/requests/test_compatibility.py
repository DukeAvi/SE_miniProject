from itertools import product

import pytest
from rest_framework.test import APIRequestFactory

from apps.core.exceptions import api_exception_handler
from apps.requests.compatibility import (
    BLOOD_GROUPS,
    COMPONENTS,
    IncompatibleBloodTypeError,
    acceptable_donor_groups,
    assert_compatible,
    is_compatible,
    select_compatible_units,
)


EXPECTED = {
    "WHOLE_BLOOD": {
        group: {group} for group in BLOOD_GROUPS
    },
    "PLATELETS": {
        group: {group} for group in BLOOD_GROUPS
    },
    "RBC": {
        "O-": {"O-"},
        "O+": {"O-", "O+"},
        "A-": {"O-", "A-"},
        "A+": {"O-", "O+", "A-", "A+"},
        "B-": {"O-", "B-"},
        "B+": {"O-", "O+", "B-", "B+"},
        "AB-": {"O-", "A-", "B-", "AB-"},
        "AB+": set(BLOOD_GROUPS),
    },
    "PLASMA": {
        "O-": set(BLOOD_GROUPS),
        "O+": set(BLOOD_GROUPS),
        "A-": {"A-", "A+", "AB-", "AB+"},
        "A+": {"A-", "A+", "AB-", "AB+"},
        "B-": {"B-", "B+", "AB-", "AB+"},
        "B+": {"B-", "B+", "AB-", "AB+"},
        "AB-": {"AB-", "AB+"},
        "AB+": {"AB-", "AB+"},
    },
}


@pytest.mark.parametrize("component", sorted(COMPONENTS))
@pytest.mark.parametrize("recipient_group", BLOOD_GROUPS)
def test_complete_compatibility_matrix(component, recipient_group):
    expected = EXPECTED[component][recipient_group]

    assert set(acceptable_donor_groups(recipient_group, component)) == expected
    for donor_group in BLOOD_GROUPS:
        assert is_compatible(donor_group, recipient_group, component) is (
            donor_group in expected
        )


def test_every_component_has_all_64_pairings():
    assert sum(1 for _ in product(BLOOD_GROUPS, repeat=2)) == 64
    for component in COMPONENTS:
        assert len(
            [
                (donor, recipient)
                for donor, recipient in product(BLOOD_GROUPS, repeat=2)
                if is_compatible(donor, recipient, component)
            ]
        ) == sum(len(groups) for groups in EXPECTED[component].values())


def test_invalid_values_fail_closed():
    assert acceptable_donor_groups("INVALID", "RBC") == frozenset()
    assert acceptable_donor_groups("O-", "INVALID") == frozenset()
    assert is_compatible("INVALID", "O-", "RBC") is False


def test_candidate_selection_filters_incompatible_units():
    units = [
        {"blood_group": "O-", "unit": 1},
        {"blood_group": "A+", "unit": 2},
        {"blood_group": "AB+", "unit": 3},
    ]

    selected = select_compatible_units(
        units,
        recipient_group="A+",
        component="RBC",
        donor_group_for=lambda unit: unit["blood_group"],
    )

    assert [unit["unit"] for unit in selected] == [1, 2]


def test_locked_fulfillment_guard_raises_422_error():
    assert_compatible("O-", "A+", "RBC")

    with pytest.raises(IncompatibleBloodTypeError) as exc_info:
        assert_compatible("AB+", "O-", "RBC")

    assert exc_info.value.status_code == 422
    assert exc_info.value.default_code == "incompatible_blood_type"


def test_incompatible_type_uses_documented_422_error_envelope():
    request = APIRequestFactory().post("/api/v1/requests/1/fulfillment")
    try:
        assert_compatible("AB+", "O-", "RBC")
    except IncompatibleBloodTypeError as exc:
        response = api_exception_handler(exc, {"request": request})

    assert response.status_code == 422
    assert response.data["error"]["code"] == "incompatible_blood_type"
