---
name: ipo-document-control
description: Reconcile audited-financial cutoff and prospectus-signature windows for the frozen 2023 mainland Shanghai/Shenzhen IPO control packet, including evidence-dependent extensions. Use for the combined document-control worklist, not filing approval.
---

# IPO document control

Read [references/packet-contract.json](references/packet-contract.json) before
running the helper. National rule facts and local rehearsal conventions are
separately identified. This Skill is frozen at 2023-09-05 and is not a current
legal opinion, eligibility assessment or authority to submit documents.

```bash
python3 scripts/check_windows.py --cases /app/input_files/S04_项目清单.json --out /app/output/skill_evidence.json
```

Read S01 (2023 CSRC order 205, articles 26/30/31/46), S02 (2020 amendment
history), S03 (original work authorization), and S05 (original extension evidence
register). A current operational result uses the 2023 source, not an obsolete
article number or a history-only helper. Neither sales advice nor an unsigned
extension application proves the extension applies to a particular report.

The helper calculates separate financial and signature review dates, preserves
missing/invalid evidence, and hashes its actual inputs and local contract. It
does not determine legal expiry-day inclusivity or holiday adjustments. Under
the packet's explicit convention, equality at a review date requires review.
The nine-month calculation is a theoretical ceiling, never an automatic grant.

Use the resulting dates/statuses to construct the review workbook and memo.
Retain source/date/version, next action and owner. A clean date worklist is not
permission to issue securities. Do not modify inputs, send filings or invent
regulatory confirmation. The separate signature-only and historical Skills are
not substitutes for this combined control workflow.
