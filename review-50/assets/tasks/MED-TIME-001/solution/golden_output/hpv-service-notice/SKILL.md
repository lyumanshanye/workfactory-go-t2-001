---
name: hpv-service-notice
description: Prepare historical HPV immunization-program service notices and route intake questions using the frozen November 2025 China policy packet. Use for administrative communication drafts, not diagnosis or clinical clearance.
---

# HPV service notice preparation

This is a historical, nonclinical service-desk workflow, frozen at 2025-11-12
Asia/Shanghai. It is not a current vaccine guideline or an autonomous eligibility
engine. For a different time or jurisdiction, obtain the applicable policy first.

Read [references/policy.json](references/policy.json) for the dated source map,
and [references/service-boundary.md](references/service-boundary.md) for local
workflow boundaries. Local routing conventions are not national vaccine rules.

For structured intake rehearsal, run:

```bash
python3 scripts/route_intake.py --cases /path/to/cases.json --out /path/to/results.json
python3 -m unittest discover -s tests -v
```

The helper validates all records before writing. Its results are draft service
routes, never permission to vaccinate. Do not reinterpret `SERVICE_REVIEW` as an
appointment confirmation, stock guarantee or clinical approval. Missing history
is not zero prior doses. Prior completed courses, special health states and
mixed manufacturers require the source-specific review described in the packet.

When drafting a notice, distinguish the 2025-10-10 signature, 2025-10-30 public
notice, and 2025-11-10 implementation. Cite S01/S02 with section locators. Describe
the national-program target, not all possible licensed HPV uses. State the
two-dose bivalent program and six-month interval without inventing a detailed
individual schedule. Explain the healthcare assessment and 30-minute observation
requirement. Prior vaccination and special-health questions go to trained staff.
School staff assist communication; they do not clear contraindications.

Save drafts and test evidence only. This Skill does not contact patients, book
slots, change a medical record, administer a dose or authorize publication.
