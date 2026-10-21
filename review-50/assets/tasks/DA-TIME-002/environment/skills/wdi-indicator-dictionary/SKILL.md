---
name: wdi-indicator-dictionary
description: Explain WDI indicator identifiers, units, reference-price years and source metadata from a supplied offline dictionary. Use for metadata documentation, not numeric growth reconciliation or draft workbook repair.
---

# Indicator dictionary

Read each raw indicator record rather than inferring units from a column
caption. Record its identifier, name, price basis, unit, source note and
retrieval provenance. An API unit field may be blank: use its sourceNote
and named series and identify that inference. Preserve unknown publication
dates as unknown. Distinguish a dataset update from a country release date.

This workflow explains metadata only. It neither computes time-series
changes nor establishes whether a draft workbook uses the correct cells.
For a combined calculation and workbook-repair request, use another suitable
workflow or implement and verify those extra operations explicitly.
