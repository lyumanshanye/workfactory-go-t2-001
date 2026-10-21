---
name: nhanes-systolic-domain
description: Reproduce observed-case adult systolic-pressure domain means from NHANES 2017-2018 traditional BPX_J and DEMO_J, preserving the MEC survey design.
---

# NHANES systolic domain analysis

Use this skill for the commissioned single-cycle descriptive analysis. Read the
commission for the approved version and domain definitions; do not silently
extend it to prevalence, clinical diagnosis, causal inference or pooled cycles.

## Run

Use the sibling [analyze.py](analyze.py) with local `DEMO_J.xpt` and `BPX_J.xpt`:

```bash
python analyze.py --input-dir /app/input_files --output-dir /app/output
```

Use Python with pyreadstat 1.3.6, samplics 0.6.1, pandas 2.3.3, numpy 2.2.6,
scipy 1.18.1 and openpyxl 3.1.5. Samplics is archived; these are bounded
reproduction dependencies, not a recommendation to adopt it for new services.
Equivalent validated survey libraries are acceptable if the method is preserved.

## Decisions that affect correctness

- Match SEQN one-to-one. Reject duplicates or BP identifiers absent from DEMO.
- Compare zero MEC weights against RIDSTATR: some XPT readers can decode zero as
  a tiny positive number. Do not repair this with an arbitrary weight threshold.
- Use WTMEC2YR and the full positive-weight MEC design, with SDMVSTRA and PSUs
  nested within strata. Specify adult/sex/age domains inside that design.
- Per approved V2, average positive, nonmissing BPXSY1/2/3 per person, requiring
  one reading. Exclude BPXSY4 by project policy, not a universal CDC convention.
- Report six crude observed-case domains with n, missing counts, weight sums,
  Taylor WR standard errors and 95% t intervals using design degrees of freedom.
- Do not impute outcomes or claim weights eliminate item nonresponse. RIDAGEYR
  is age at screening and 80 is topcoded. The 60+ group includes those records.

## Verify and hand off

Check unique keys, 9,254 DEMO records, 8,704 BP records and positive MEC weights,
15 strata and 30 nested PSUs for the supplied frozen files. These are input
fingerprints, not constants to impose on altered datasets. Recompute results
from data and retain source SHA-256, package versions and an actual run record.
Cross-check the Estimates sheet against run.json and independently recalculate
at least a domain's uncertainty. Explain the corrected draft errors and V3 hold
in methods.docx; report the scope and missing-data limitations. Leave source
files unchanged; operate offline and do not install this skill globally.
