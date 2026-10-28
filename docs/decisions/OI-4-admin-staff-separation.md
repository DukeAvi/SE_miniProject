# Decision: Admin and Staff operational duties

## Status

Proposed; Product Owner confirmation is outstanding.

## Context

Issue #87 asks whether Admin is excluded from operational work such as request review and blood-unit reservation or issuance. The SAD Section 3.9.2 permission matrix and assumption A-3 define the current least-privilege baseline and explicitly say Product Owner confirmation is required.

## Options

1. Preserve the SAD matrix: Staff handle operational workflows; Admin handles account/role management, configuration, reports, and audit oversight.
2. Grant Admin additional operational permissions. This would require explicit justification and updates to the permission matrix and tests.

## Decision

For implementation planning, use option 1 as the provisional baseline. This record transcribes the SAD matrix; it does not add privileges or represent Product Owner approval.

| Operation | Donor | Recipient | Staff | Admin |
| --- | --- | --- | --- | --- |
| Self-register an account | Yes | Yes | - | - |
| Log in, log out, view/edit own profile | Own | Own | Own | Own |
| Book or cancel an appointment | Own | - | - | - |
| View own donation history | Own | - | - | - |
| View any donor and appointments | - | - | Yes | - |
| Record completed donation | - | - | Yes | - |
| Create, discard, or accept return of a blood unit | - | - | Yes | - |
| Search availability by group/component | - | Aggregate | Unit level | - |
| Submit a blood request | - | Yes | - | - |
| View own requests and history | - | Own | - | - |
| View all requests | - | - | Yes | - |
| Approve, reject, or hold a request | - | - | Yes | - |
| Reserve and issue units | - | - | Yes | - |
| View own notifications | Own | Own | Own | Own |
| Generate reports | - | - | Yes | Yes |
| Configure low-stock thresholds | - | - | - | Yes |
| Create, disable, and change roles of staff accounts | - | - | - | Yes |
| View audit log and notification delivery failures | - | - | - | Yes |

## Consequences

- Admin does not approve, reserve, or issue operational blood requests under this provisional baseline.
- Staff cannot manage accounts, roles, thresholds, audit logs, or notification failure administration unless a separate approved requirement grants that access.
- BBMS-F-003 and BBMS-SR-002 authorization tests must use this matrix as their oracle unless the Product Owner approves a documented change.
- The SAD PDF is not edited; this record provides an editable repository copy of its current matrix.

## Approval

- Decision owner: Product Owner (confirmation pending)
- Date: Pending
- Evidence or reference: SAD Section 3.9.2 and assumption A-3, plus SAD Section 4.6 OI-4 / GitHub issue #87
