---
name: godot-migration-release
description: Run the Quest Board team's offline Godot migration evidence and release gate, including headless probes and rollback boundaries. Use for this team's migration candidates, not unrelated Godot development.
---

# Quest Board migration evidence

This is an original team workflow supplied for the benchmark, not an official
Godot release policy. The versioned local contract determines the evidence
schema and what a headless result can authorize. Read
[release-contract.json](references/release-contract.json) before deciding the gate.
Public API facts still come from the frozen engine documentation.

Run the actual checks against a working copy of the project:

```bash
python3 /skills/godot-migration-release/scripts/audit_release.py \
  --project /app/output/migrated_game --godot godot \
  --out /app/output/release_gate.json
```

The tool copies the project to isolated temporary storage, imports it, executes
the UI signal, stdin, and editor-parser probes, and records real commands,
exit codes, observations and source hashes. It never approves production or
modifies the input snapshot. `--godot` may name another verified executable in
an author QA environment; the benchmark image provides `godot`.

On a failing command, retain the failure evidence, fix the project and rerun;
do not relabel the failure as success or replace the observed output. On a tool
or environment error, report that condition rather than inventing a score.
Keep the 4.3 rollback snapshot untouched: 4.4 import caches/UID sidecars are not
rollback evidence. A successful headless candidate is still pending the manual
editor/platform checks required by the contract.
