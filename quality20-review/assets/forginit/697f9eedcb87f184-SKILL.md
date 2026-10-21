---
name: game-asset-release
description: Prepare LumenForge game-asset review candidates using its approved conflict policy and source-byte probe.
---

# LumenForge asset handoff

This is a fictional company SOP, not a license or legal opinion. Read
[approved-policy.json](approved-policy.json) after the commission approval events.
Use V2: a procurement/source license conflict is a HOLD even when the public
source appears permissive. Never silently correct the ledger and clear that row.
A source license and company release authority are separate checks.
Missing files or preview-only components are HOLD; do not crop previews or fetch
substitutes. For a multi-license work choose one offered license permitted by V2,
record that choice, and preserve original notices. Do not apply all alternatives
simultaneously. V2 permits a partial candidate with eligible rows only; retain
every held row and its follow-up owner. V3 is a later unapproved proposal.

Inspect actual author/title/attribution/download fields and supplied raw files.
CC0 provenance is an internal requirement, not a CC0 attribution obligation.
Check original-author versus submitter. Preserve the original credit notice;
record no changes for byte-identical assets. Do not infer trademark clearance,
store compatibility, author endorsement or legal approval from a public license.

Run `python /skills/game-asset-release/release_probe.py --inputs /app/input_files
--candidate /app/output/candidate.json --report /app/output/release-report.json`
as one shell line. The helper reads raw source fields and hashes real files.
Its policy/byte validation does not approve rights or publication. Inspect the
underlying evidence as well; helper output does not replace the handoff.
Final state is prepared_for_human_review; no publication or global installation.
