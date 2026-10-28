# OI-1 Component Compatibility Rules

## Status

Approved for the classroom demonstration by the assigned contributor under delegated decision authority. These are software demonstration rules only, not a medically approved transfusion policy, and must not be used to guide real transfusions.

## Scope and decision

For the version 1.0 classroom demonstration, the compatibility engine uses the following deliberately narrow ABO/Rh screening rules. It does not replace antibody screening, crossmatching, product-specific requirements, or a transfusion service's decision.

| Component | Donor rule for recipient | Rh rule |
| --- | --- | --- |
| Whole blood | Same ABO group only | Same RhD status only |
| Red blood cells (RBC) | Standard ABO red-cell compatibility | Rh-negative recipients accept Rh-negative only; Rh-positive recipients accept either |
| Plasma | Donor plasma must be ABO-compatible with recipient red cells: O accepts any ABO; A accepts A/AB; B accepts B/AB; AB accepts AB only | RhD is ignored for plasma |
| Platelets | Same ABO group only | Same RhD status only |

The exact donor groups accepted for each recipient group are:

| Recipient | Whole blood donors | RBC donors | Plasma donors | Platelet donors |
| --- | --- | --- | --- | --- |
| O- | O- | O- | O-, O+, A-, A+, B-, B+, AB-, AB+ | O- |
| O+ | O+ | O-, O+ | O-, O+, A-, A+, B-, B+, AB-, AB+ | O+ |
| A- | A- | O-, A- | A-, A+, AB-, AB+ | A- |
| A+ | A+ | O-, O+, A-, A+ | A-, A+, AB-, AB+ | A+ |
| B- | B- | O-, B- | B-, B+, AB-, AB+ | B- |
| B+ | B+ | O-, O+, B-, B+ | B-, B+, AB-, AB+ | B+ |
| AB- | AB- | O-, A-, B-, AB- | AB-, AB+ | AB- |
| AB+ | AB+ | O-, O+, A-, A+, B-, B+, AB-, AB+ | AB-, AB+ | AB+ |

For this matrix, compatibility is directional: the recipient row lists acceptable donor groups. Invalid group or component values fail closed. The same pure domain function must be used during candidate selection and rechecked inside the locked reservation or issue transaction; a failed recheck returns `422 incompatible_blood_type` and rolls back the operation.

## Basis and limits

The RBC and plasma ABO rules follow the Australian Red Cross Lifeblood component compatibility guidance. Platelets are restricted to ABO-identical and RhD-identical matches for this demo, although real platelet selection is more nuanced. Whole blood is restricted to identical ABO/RhD groups. These constraints reduce the combinations the demo will accept; they do not establish clinical safety.

This application is a classroom demonstration using mock data. It is not validated for clinical use. Any real deployment requires a transfusion-medicine reviewer to approve the component matrix and the complete product-selection workflow, including antibody testing and crossmatching.

## Traceability

- Requirements: BBMS-F-034
- Design: DS-034; SAD Section 4.6, OI-1
- Verification: TC-Req-05, full 8 by 8 group matrix for each component
- GitHub: issue #84; implementation: issue #67

## Decision record

- Approved by: Ayushman Dey, assigned issue contributor acting under delegated decision authority
- Effective for the classroom demo: 2026-10-29
- Clinical approval: Not applicable to the mock-data demonstration; required before any real-world use
- Reference: [Australian Red Cross Lifeblood component compatibility](https://www.lifeblood.com.au/health-professionals/products/component-compatibility) and [matching blood groups](https://www.lifeblood.com.au/patients-recipients/blood-plasma-platelets/blood-for-transfusion/matching-blood-groups)
