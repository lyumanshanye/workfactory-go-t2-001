---
name: device-correction-review
description: Apply the fictional facility's evidence-bound review gate to the frozen FDA correction task; no clinical or external release authority.
---

# Device correction review

Read `references/team-sop.json` in full. It is an original facility workflow, not an FDA-created approval standard. Read the actual FDA input documents separately for professional content.

The source scope is the four explicit model/UDI-DI pairs in the frozen current communication. A nonmatch is outside this given review matrix, not proof of no other recall. Conflicting model/UDI or equally authoritative same-observation service records must remain on identity/evidence hold; a later sales memo cannot resolve the conflict. Missing software, current addendum, historical sensor action, training or transferred-recipient acknowledgement remains a concrete action pending.

Execute the installed script without changing the Skill or input data:

```bash
python3 /skills/device-correction-review/scripts/review.py --input-dir /app/input_files --out /app/output/skill_evidence.json
```

Review the returned per-device findings and use them to revise every corresponding workbook row, memo and recipient draft. `READY_FOR_AUTHORIZED_REVIEW` means that the **given internal evidence checklist** is complete for handoff; it does not authorize patient use, software installation, changing therapy, manufacturer repair, clinical release, regulator approval or external communication. Do not turn `HOLD_*` or `ACTION_PENDING` into approved just because the script ran or a version string looks new.

Retain the actual Skill/input hashes, UTC execution, adopted service evidence and gaps from the tool output. Hashes prove byte identity, not a manufacturer's signature or the truth of a hypothetical maintenance record. This is a deterministic evidence aid, not a replacement for clinical engineering, respiratory clinicians, current manufacturer literature or expert review. Provide targeted questions and an owner for unresolved issues; do not fabricate replies or fill unknowns with conventional settings.
