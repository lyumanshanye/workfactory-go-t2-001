# Local service routing contract R2 (original scenario)

Use the frozen S01/S02 text, not the newest message alone. The service lead owns
draft preparation; only the authorized healthcare team assesses clinical matters.
These are local rehearsal categories, not automatic eligibility decisions:

- `POLICY_REVIEW`: requested date is beyond the frozen historical snapshot.
- `PRELAUNCH`: national-program implementation has not begun at the requested date.
- `DATA_REVIEW`: a required demographic/history field is unknown or inconsistent.
- `POLICY_CLARIFICATION`: the birth date is exactly the wording boundary. Preserve
  the national text and ask the policy owner to verify inclusion; do not rewrite
  “以后” as an invented inclusive/exclusive national rule. This cautious route is
  an explicit local drafting convention.
- `PROGRAM_SCOPE_REVIEW`: outside the stated birth cohort/sex program description.
  This does not say a person can never receive any licensed HPV vaccine.
- `AGE_REVIEW`: younger than 13 or outside the cited under-18 catch-up range.
- `CLINICIAN_REVIEW`: a special health state or current-health question needs
  qualified healthcare review. S02's special three-dose/product-label statement
  must not become a service clerk's prescription.
- `COURSE_RECORD_REVIEW`: a reported completed course requires record verification;
  S02 says a completed full course does not require repeat program vaccination.
- `PRIOR_HISTORY_REVIEW`: one prior dose, manufacturer issues or incomplete
  history needs source-specific informed review; do not restart automatically.
- `SERVICE_REVIEW`: basic fields fit the frozen routine service description, but
  a healthcare assessment and service availability check are still required.

Precedence: future snapshot → prelaunch → data integrity → exact wording boundary
→ program scope → age → health flags → completed-course report → previous dose
→ ordinary service review. This precedence determines the primary work queue,
not the medical importance of a real symptom. An urgent situation is not handled
by this offline rehearsal script; staff use the clinic's emergency procedures.

Output only case ID, rehearsal date, age where calculable, route/reason, source
locators and `clinical_clearance=false`, `appointment_confirmed=false`. Do not
copy birth dates or health flags into public communication. Never report a real
booking, stock check, consent or vaccination as completed by this tool.
