---
name: service-form-accessibility
description: Repair CivicLab service forms using the approved policy, keyboard flow and error-recovery checklist.
---

# CivicLab service form SOP

Use this for interactive service forms, not print exports or monthly reports.
Read the commission approval events first, then [approved-policy.json](approved-policy.json).
The JSON is an original fictional internal policy, not a W3C or government rule.
V2 is approved; a later V3 email is not authority. Compute rate * integer hours,
then apply the registered nonprofit multiplier. Exactly 80 is routine; more
than 80 needs additional safety review, up to capacity 120. All final receipts
remain pending manual review, never automatically approved.

Keep contact -> activity -> review -> pending receipt. Use native labeled inputs
and buttons with logical keyboard order and visible focus. On invalid continue,
focus a summary with textual field links; preserve valid values; associate each
error with its input. Only require organisation name when the checkbox is on.
Back and edit preserve entries. Reuse contact data on review without reentry.
Keep user strings as text. Run boundary checks, at least 320/390/1280 CSS-pixel
widths, keyboard-only navigation, and the project's V2 fee/routing checks.
Read the supplied unmodified WCAG 2.2 recommendation sections cited in the
commission. Do not claim full WCAG compliance from a bounded browser check.
Do not submit externally, persist personal information or install skills globally.

