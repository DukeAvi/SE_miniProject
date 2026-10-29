# Decision: one role per account for v1.0

## Status

Approved for v1.0 classroom demonstration. Product Owner Avrit Sharma recorded approval of option 1 on issue #88 on 2026-10-29.

## Context

Issue #88 asks whether a person who acts as both Donor and Recipient must use two accounts in v1.0 or whether the system should support multiple roles on one account. Registration, the account model, authorization, and test data depend on this choice.

The SAD's Section 4.6 lists "One role per account. A person who is both donor and recipient needs two accounts" and proposes that this is acceptable for v1.0, with multiple roles considered later.

## Options

1. Use one role per account in v1.0; a person acting in both capacities uses two accounts. This matches the SAD's proposed resolution and keeps the role model and permission checks singular.
2. Allow multiple roles on one account. This changes registration, account representation, permission evaluation, and related test cases.

## Decision

Use one role per account in v1.0. A person acting as both Donor and Recipient uses two accounts. Multiple roles on one account remain future scope.

## Consequences

- Registration accepts exactly one of Donor or Recipient for public account creation.
- Authorization reads one role value per account; any account with no recognized role must be denied protected access.
- Supporting multiple roles later requires a separately approved change to the account schema, registration contract, permission logic, and tests.
- No SRS or SAD source PDF was edited; the repository only contains the SAD PDF and no editable source document.

## Approval

- Decision owner: Avrit Sharma, Product Owner
- Approval: Recorded by Avrit Sharma on issue #88
- Date: 2026-10-29
- Evidence or reference: SAD Section 4.1.1 and Section 4.6, plus GitHub issue #88

## Published SAD source note

The SAD PDF states that one role per account is acceptable for v1.0 and that multiple roles may be considered later. The Product Owner approval recorded on issue #88 confirms that choice. This decision record adds the approval evidence; it does not modify the published PDF. The repository contains no editable SAD source or reproducible PDF-generation workflow, so the PDF was not regenerated.
